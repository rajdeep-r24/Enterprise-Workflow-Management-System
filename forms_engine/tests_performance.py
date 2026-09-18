from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from organizations.models import Organization
from employees.models import Employee
from rbac.models import Role
from departments.models import Department
from locations.models import Location
from designations.models import Designation
from forms_engine.models import FormDefinition, FormSubmission
from workflow.models.workflow import WorkflowDefinition, WorkflowVersion, WorkflowStepDefinition
from workflow.models.instances import WorkflowInstance, WorkflowStepInstance
from django.core.files.uploadedfile import SimpleUploadedFile

class PerformanceTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Performance Org", code="PERF", email="perf@org.com")
        self.dept = Department.objects.create(organization=self.org, name="IT", code="IT")
        self.loc = Location.objects.create(organization=self.org, name="HQ", code="HQ", location_type="HQ")
        self.desig = Designation.objects.create(organization=self.org, name="Engineer", code="ENG")
        
        self.role_emp, _ = Role.objects.get_or_create(code="EMPLOYEE", defaults={"name": "Employee"})
        self.role_mgr, _ = Role.objects.get_or_create(code="MANAGER", defaults={"name": "Manager"})
        
        self.user_emp = User.objects.create_user(username="perf_emp", email="emp@perf.com", password="password")
        Employee.objects.create(user=self.user_emp, organization=self.org, role=self.role_emp, department=self.dept, location=self.loc, designation=self.desig, joining_date="2024-01-01", employee_code="P1")
        
        self.user_mgr = User.objects.create_user(username="perf_mgr", email="mgr@perf.com", password="password")
        Employee.objects.create(user=self.user_mgr, organization=self.org, role=self.role_mgr, department=self.dept, location=self.loc, designation=self.desig, joining_date="2024-01-01", employee_code="P2")
        
        self.wf_def = WorkflowDefinition.objects.create(organization=self.org, name="WF Perf", code="WFP")
        self.wf_ver = WorkflowVersion.objects.create(workflow=self.wf_def, version=1, is_published=True)
        self.step_def = WorkflowStepDefinition.objects.create(workflow_version=self.wf_ver, name="Step 1", step_order=1, step_type="APPROVAL", approver_type="ROLE", role_code="MANAGER")
        self.form = FormDefinition.objects.create(organization=self.org, workflow=self.wf_ver, name="Form Perf", code="FRMP", is_published=True)
        
        # Create 10 instances to test N+1
        for i in range(10):
            wf_inst = WorkflowInstance.objects.create(organization=self.org, workflow_version=self.wf_ver, initiated_by=self.user_emp, status="PENDING")
            FormSubmission.objects.create(organization=self.org, form=self.form, workflow_instance=wf_inst, submitted_by=self.user_emp, status="PENDING")
            WorkflowStepInstance.objects.create(workflow_instance=wf_inst, step_definition=self.step_def, assigned_to=self.user_mgr, status="PENDING")

    def test_approval_inbox_query_count(self):
        client = Client()
        client.force_login(self.user_mgr)
        url = reverse("approval-inbox")
        
        # First request to warm up caches (e.g. session, permissions)
        client.get(url)
        
        # We expect a constant number of queries regardless of how many steps are in the inbox
        # Without select_related, 10 items might cause 10+ queries.
        # With optimization, it should be well under 20 total.
        with self.assertNumQueriesLessThan(25):
            response = client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Step 1")
            
    def assertNumQueriesLessThan(self, limit):
        return _AssertNumQueriesLessThanContext(self, limit)

class _AssertNumQueriesLessThanContext:
    def __init__(self, test_case, limit):
        self.test_case = test_case
        self.limit = limit
    
    def __enter__(self):
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        self.context = CaptureQueriesContext(connection)
        self.context.__enter__()
        return self
        
    def __exit__(self, exc_type, exc_value, traceback):
        self.context.__exit__(exc_type, exc_value, traceback)
        if exc_type is not None:
            return
        executed = len(self.context.captured_queries)
        self.test_case.assertTrue(
            executed < self.limit,
            f"Expected less than {self.limit} queries, but {executed} were executed."
        )
