from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from organizations.models import Organization
from departments.models import Department
from designations.models import Designation
from locations.models import Location
from rbac.models import Role
from employees.models import Employee
from forms_engine.models import FormDefinition, FormSubmission
from workflow.models.workflow import WorkflowDefinition, WorkflowVersion, WorkflowStepDefinition
from workflow.models.instances import WorkflowInstance, WorkflowStepInstance

class MultiTenantTestCase(TestCase):
    def setUp(self):
        # Org A Setup
        self.org_a = Organization.objects.create(name="Org A", code="ORGA", email="admin@orga.test")
        self.dept_a = Department.objects.create(organization=self.org_a, name="IT A", code="IT_A")
        self.loc_a = Location.objects.create(organization=self.org_a, name="HQ A", code="HQA", location_type="HQ")
        self.des_a = Designation.objects.create(organization=self.org_a, name="Eng A", code="ENGA")
        
        self.user_a = User.objects.create_user(username="usera", email="usera@orga.test", password="password")
        self.role_emp, _ = Role.objects.get_or_create(code="EMPLOYEE", defaults={"name": "Employee"})
        self.role_mgr, _ = Role.objects.get_or_create(code="MANAGER", defaults={"name": "Manager"})
        
        self.emp_a = Employee.objects.create(
            user=self.user_a, organization=self.org_a, department=self.dept_a,
            location=self.loc_a, designation=self.des_a, role=self.role_mgr,
            employee_code="EMPA01", joining_date="2024-01-01"
        )
        
        # Org B Setup
        self.org_b = Organization.objects.create(name="Org B", code="ORGB", email="admin@orgb.test")
        self.dept_b = Department.objects.create(organization=self.org_b, name="IT B", code="IT_B")
        self.loc_b = Location.objects.create(organization=self.org_b, name="HQ B", code="HQB", location_type="HQ")
        self.des_b = Designation.objects.create(organization=self.org_b, name="Eng B", code="ENGB")
        
        self.user_b = User.objects.create_user(username="userb", email="userb@orgb.test", password="password")
        
        self.emp_b = Employee.objects.create(
            user=self.user_b, organization=self.org_b, department=self.dept_b,
            location=self.loc_b, designation=self.des_b, role=self.role_emp,
            employee_code="EMPB01", joining_date="2024-01-01"
        )

        # Create some data for Org B
        self.wf_def_b = WorkflowDefinition.objects.create(organization=self.org_b, name="WF B", code="WFB")
        self.wf_ver_b = WorkflowVersion.objects.create(workflow=self.wf_def_b, version=1, is_published=True)
        self.form_def_b = FormDefinition.objects.create(
            organization=self.org_b, name="Form B", code="FORMB", workflow=self.wf_ver_b, is_published=True
        )
        
        self.wf_inst_b = WorkflowInstance.objects.create(
            organization=self.org_b, workflow_version=self.wf_ver_b,
            initiated_by=self.user_b, status="IN_PROGRESS"
        )
        self.form_sub_b = FormSubmission.objects.create(
            organization=self.org_b, form=self.form_def_b,
            workflow_instance=self.wf_inst_b, submitted_by=self.user_b,
            status="SUBMITTED"
        )
        
        self.step_def_b = WorkflowStepDefinition.objects.create(
            workflow_version=self.wf_ver_b, name="Step B", step_order=1,
            step_type="APPROVAL", approver_type="ROLE", role_code="EMPLOYEE"
        )
        self.step_inst_b = WorkflowStepInstance.objects.create(
            workflow_instance=self.wf_inst_b, step_definition=self.step_def_b,
            assigned_to=self.user_b, status="PENDING"
        )

        self.client_a = Client()
        login_success = self.client_a.login(email="usera@orga.test", password="password")
        self.assertTrue(login_success, "Login failed for User A")

    def test_cross_tenant_get_returns_404(self):
        """Test that User A cannot GET a resource belonging to Org B."""
        url = reverse('request-detail', kwargs={'pk': self.form_sub_b.pk})
        response = self.client_a.get(url)
        self.assertEqual(response.status_code, 404)
        
    def test_cross_tenant_post_returns_404(self):
        """Test that User A cannot POST to an action for Org B's resource."""
        url = reverse('approve-request', kwargs={'pk': self.step_inst_b.pk})
        response = self.client_a.post(url, {'remarks': 'approved'})
        self.assertEqual(response.status_code, 404)

    def test_cross_tenant_patch_returns_404(self):
        """Test that User A cannot PATCH a resource belonging to Org B."""
        url = reverse('request-detail', kwargs={'pk': self.form_sub_b.pk})
        response = self.client_a.patch(url, {'some': 'data'})
        self.assertEqual(response.status_code, 404)

    def test_cross_tenant_delete_returns_404(self):
        """Test that User A cannot DELETE a resource belonging to Org B."""
        url = reverse('request-detail', kwargs={'pk': self.form_sub_b.pk})
        response = self.client_a.delete(url)
        self.assertEqual(response.status_code, 404)
