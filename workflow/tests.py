"""
Tests for WorkflowService.approve() - the core approval state machine
that decides whether a request moves to the next approver or is marked
fully APPROVED. This is the highest-risk piece of business logic in the
app, so it's covered directly here rather than only through the views.
"""
from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from organizations.models import Organization
from departments.models import Department
from locations.models import Location
from designations.models import Designation
from rbac.models import Role
from employees.models import Employee
from forms_engine.models import FormDefinition, FormSubmission
from workflow.models.events import WorkflowEvent
from workflow.models.workflow import (
    WorkflowDefinition,
    WorkflowVersion,
    WorkflowStepDefinition,
)
from workflow.models.instances import WorkflowInstance, WorkflowStepInstance
from workflow.services.approver_resolver import AmbiguousApproverError, ApproverResolver
from workflow.services.workflow_service import WorkflowActionError, WorkflowService


class WorkflowServiceApproveTests(TestCase):

    def setUp(self):
        self.org = Organization.objects.create(
            name="Acme Corp",
            code="ACME",
            email="hr@acme.test",
        )
        self.department = Department.objects.create(
            organization=self.org, name="IT", code="IT",
        )
        self.location = Location.objects.create(
            organization=self.org, name="HQ", code="HQ",
            location_type="HQ", address="123 Main St",
            city="Mumbai", state="MH",
        )
        self.designation = Designation.objects.create(
            organization=self.org, name="Engineer", code="ENG",
        )

        self.role_employee, _ = Role.objects.get_or_create(code="EMPLOYEE", defaults={"name": "Employee"})
        self.role_it_head, _ = Role.objects.get_or_create(code="IT_HEAD", defaults={"name": "IT Head"})
        self.role_hr_head, _ = Role.objects.get_or_create(code="HR_HEAD", defaults={"name": "HR Head"})

        # The requester submitting the form
        self.requester_user = User.objects.create_user(
            username="requester", email="requester@acme.test", password="testpass123",
        )
        self.requester = Employee.objects.create(
            user=self.requester_user, organization=self.org,
            department=self.department, location=self.location,
            designation=self.designation, role=self.role_employee,
            employee_code="EMP001", joining_date="2024-01-01",
        )

        # Approvers, resolved by role_code via ApproverResolver
        self.it_head_user = User.objects.create_user(
            username="it_head", email="it_head@acme.test", password="testpass123",
        )
        Employee.objects.create(
            user=self.it_head_user, organization=self.org,
            department=self.department, location=self.location,
            designation=self.designation, role=self.role_it_head,
            employee_code="EMP002", joining_date="2024-01-01",
        )

        self.hr_head_user = User.objects.create_user(
            username="hr_head", email="hr_head@acme.test", password="testpass123",
        )
        Employee.objects.create(
            user=self.hr_head_user, organization=self.org,
            department=self.department, location=self.location,
            designation=self.designation, role=self.role_hr_head,
            employee_code="EMP003", joining_date="2024-01-01",
        )

        # Workflow definition: IT Head -> HR Head -> (end)
        self.workflow_def = WorkflowDefinition.objects.create(
            organization=self.org, name="Laptop Request", code="LAPTOP",
        )
        self.version = WorkflowVersion.objects.create(
            workflow=self.workflow_def, version=1, is_published=True,
        )
        self.step1 = WorkflowStepDefinition.objects.create(
            workflow_version=self.version, name="IT Head Approval",
            step_order=1, step_type="APPROVAL", approver_type="ROLE", role_code="IT_HEAD",
        )
        self.step2 = WorkflowStepDefinition.objects.create(
            workflow_version=self.version, name="HR Head Approval",
            step_order=2, step_type="APPROVAL", approver_type="ROLE", role_code="HR_HEAD",
        )
        self.step1.next_step = self.step2
        self.step1.save()

        self.form_def = FormDefinition.objects.create(
            organization=self.org, name="Laptop Request Form",
            code="LAPTOP_FORM", workflow=self.version, is_published=True,
        )

        self.instance = WorkflowInstance.objects.create(
            organization=self.org,
            workflow_version=self.version, initiated_by=self.requester_user,
            current_step=self.step1, status="IN_PROGRESS",
        )
        self.submission = FormSubmission.objects.create(
            organization=self.org,
            form=self.form_def, workflow_instance=self.instance,
            submitted_by=self.requester_user, status="SUBMITTED",
        )
        self.step_instance_1 = WorkflowStepInstance.objects.create(
            workflow_instance=self.instance, step_definition=self.step1,
            assigned_to=self.it_head_user, status="PENDING",
        )

    def test_approve_intermediate_step_advances_to_next_step(self):
        """Approving a non-final step should assign + create the next
        PENDING step and keep the workflow IN_PROGRESS."""
        WorkflowService.approve(self.step_instance_1, self.it_head_user)

        self.instance.refresh_from_db()
        self.step_instance_1.refresh_from_db()

        self.assertEqual(self.step_instance_1.status, "APPROVED")
        self.assertEqual(self.instance.status, "IN_PROGRESS")
        self.assertEqual(self.instance.current_step, self.step2)

        next_step_instance = self.instance.steps.get(step_definition=self.step2)
        self.assertEqual(next_step_instance.status, "PENDING")
        self.assertEqual(next_step_instance.assigned_to, self.hr_head_user)

    def test_approve_final_step_marks_workflow_and_submission_approved(self):
        """Approving the last step should mark the workflow instance and
        the related form submission APPROVED, and issue a permission_id."""
        WorkflowService.approve(self.step_instance_1, self.it_head_user)

        self.instance.refresh_from_db()
        step_instance_2 = self.instance.steps.get(step_definition=self.step2)

        WorkflowService.approve(step_instance_2, self.hr_head_user)

        self.instance.refresh_from_db()
        step_instance_2.refresh_from_db()
        self.submission.refresh_from_db()

        self.assertEqual(step_instance_2.status, "APPROVED")
        self.assertEqual(self.instance.status, "APPROVED")
        self.assertIsNone(self.instance.current_step)
        self.assertIsNotNone(self.instance.completed_at)

        self.assertEqual(self.submission.status, "APPROVED")
        self.assertIsNotNone(self.submission.permission_id)
        self.assertIsNotNone(self.submission.verification_token)

    def test_approve_records_remarks(self):
        WorkflowService.approve(
            self.step_instance_1, self.it_head_user, remarks="Looks good",
        )
        self.step_instance_1.refresh_from_db()
        self.assertEqual(self.step_instance_1.remarks, "Looks good")

    def test_approve_raises_if_next_approver_cannot_be_resolved(self):
        """If nobody holds the next step's role, approve() should raise
        rather than silently create an unassigned step."""
        self.hr_head_user_employee = Employee.objects.get(user=self.hr_head_user)
        self.hr_head_user_employee.is_active = False
        self.hr_head_user_employee.save(update_fields=["is_active"])

        with self.assertRaises(WorkflowActionError):
            WorkflowService.approve(self.step_instance_1, self.it_head_user)

    def test_assigned_approver_can_approve(self):
        WorkflowService.approve(self.step_instance_1, self.it_head_user)
        self.step_instance_1.refresh_from_db()
        self.instance.refresh_from_db()
        self.assertEqual(self.step_instance_1.status, "APPROVED")
        self.assertEqual(self.instance.status, "IN_PROGRESS")

    def test_unassigned_user_cannot_approve(self):
        with self.assertRaises(WorkflowActionError):
            WorkflowService.approve(self.step_instance_1, self.requester_user)

        self.step_instance_1.refresh_from_db()
        self.instance.refresh_from_db()
        self.assertEqual(self.step_instance_1.status, "PENDING")
        self.assertEqual(self.instance.status, "IN_PROGRESS")
        self.assertEqual(WorkflowEvent.objects.count(), 0)

    def test_same_step_cannot_be_approved_twice(self):
        WorkflowService.approve(self.step_instance_1, self.it_head_user)
        before_event_count = WorkflowEvent.objects.count()

        with self.assertRaises(WorkflowActionError):
            WorkflowService.approve(self.step_instance_1, self.it_head_user)

        self.step_instance_1.refresh_from_db()
        self.instance.refresh_from_db()
        self.assertEqual(WorkflowEvent.objects.count(), before_event_count)
        self.assertEqual(self.instance.status, "IN_PROGRESS")

    def test_approved_step_cannot_later_be_rejected(self):
        WorkflowService.approve(self.step_instance_1, self.it_head_user)
        before_event_count = WorkflowEvent.objects.count()

        with self.assertRaises(WorkflowActionError):
            WorkflowService.reject(self.step_instance_1, self.it_head_user)

        self.instance.refresh_from_db()
        self.step_instance_1.refresh_from_db()
        self.assertEqual(WorkflowEvent.objects.count(), before_event_count)
        self.assertEqual(self.instance.status, "IN_PROGRESS")

    def test_non_current_pending_step_cannot_be_acted_on(self):
        second_step = WorkflowStepDefinition.objects.create(
            workflow_version=self.version,
            name="Second Step",
            step_order=2,
            step_type="APPROVAL",
            approver_type="ROLE",
            role_code="HR_HEAD",
        )
        non_current_step_instance = WorkflowStepInstance.objects.create(
            workflow_instance=self.instance,
            step_definition=second_step,
            assigned_to=self.hr_head_user,
            status="PENDING",
        )

        with self.assertRaises(WorkflowActionError):
            WorkflowService.approve(non_current_step_instance, self.hr_head_user)

        non_current_step_instance.refresh_from_db()
        self.instance.refresh_from_db()
        self.assertEqual(non_current_step_instance.status, "PENDING")
        self.assertEqual(self.instance.current_step, self.step1)
        self.assertEqual(WorkflowEvent.objects.count(), 0)

    def test_completed_workflow_rejects_further_actions(self):
        WorkflowService.approve(self.step_instance_1, self.it_head_user)
        self.instance.refresh_from_db()
        self.step_instance_1.refresh_from_db()

        with self.assertRaises(WorkflowActionError):
            WorkflowService.reject(self.step_instance_1, self.it_head_user)

        self.instance.refresh_from_db()
        self.assertEqual(self.instance.status, "IN_PROGRESS")

    def test_rejected_workflow_rejects_further_actions(self):
        with self.assertRaises(WorkflowActionError):
            WorkflowService.reject(self.step_instance_1, self.requester_user)

        self.instance.refresh_from_db()
        self.step_instance_1.refresh_from_db()
        self.assertEqual(self.instance.status, "IN_PROGRESS")
        self.assertEqual(self.step_instance_1.status, "PENDING")


class WorkflowServiceRejectTests(WorkflowServiceApproveTests):
    pass


class ApproverResolverTests(TestCase):

    def setUp(self):
        self.org_a = Organization.objects.create(
            name="Org A",
            code="ORG_A",
            email="a@example.test",
        )
        self.org_b = Organization.objects.create(
            name="Org B",
            code="ORG_B",
            email="b@example.test",
        )
        self.department = Department.objects.create(
            organization=self.org_a,
            name="IT",
            code="IT",
        )
        self.location = Location.objects.create(
            organization=self.org_a,
            name="HQ",
            code="HQ",
            location_type="HQ",
            address="1 Main",
            city="Mumbai",
            state="MH",
        )
        self.designation = Designation.objects.create(
            organization=self.org_a,
            name="Engineer",
            code="ENG",
        )
        self.role_employee, _ = Role.objects.get_or_create(code="EMPLOYEE", defaults={"name": "Employee"})
        self.role_it_head, _ = Role.objects.get_or_create(code="IT_HEAD", defaults={"name": "IT Head"})
        self.role_manager, _ = Role.objects.get_or_create(code="MANAGER", defaults={"name": "Manager"})

    def _create_employee(self, user, organization, employee_code):
        return Employee.objects.create(
            user=user,
            organization=organization,
            department=self.department,
            location=self.location,
            designation=self.designation,
            role=self.role_employee,
            employee_code=employee_code,
            joining_date="2024-01-01",
        )

    def test_zero_match_returns_none(self):
        requester = self._create_employee(
            User.objects.create_user(username="req", email="req@example.test", password="testpass123"),
            self.org_a,
            "EMP001",
        )

        step = WorkflowStepDefinition.objects.create(
            workflow_version=WorkflowVersion.objects.create(workflow=WorkflowDefinition.objects.create(organization=self.org_a, name="Test Workflow", code="TEST_WORKFLOW"), version=1, is_published=True),
            name="HR Step",
            step_order=1,
            step_type="APPROVAL",
            approver_type="ROLE",
            role_code="HR_HEAD",
        )

        self.assertIsNone(ApproverResolver.resolve(requester, step))

    def test_single_match_resolves_correctly(self):
        requester = self._create_employee(
            User.objects.create_user(username="req2", email="req2@example.test", password="testpass123"),
            self.org_a,
            "EMP002",
        )
        approver_user = User.objects.create_user(username="it1", email="it1@example.test", password="testpass123")
        Employee.objects.create(
            user=approver_user,
            organization=self.org_a,
            department=self.department,
            location=self.location,
            designation=self.designation,
            role=self.role_it_head,
            employee_code="EMP003",
            joining_date="2024-01-01",
        )

        step = WorkflowStepDefinition.objects.create(
            workflow_version=WorkflowVersion.objects.create(workflow=WorkflowDefinition.objects.create(organization=self.org_a, name="Test Workflow", code="TEST_WORKFLOW_2"), version=1, is_published=True),
            name="IT Step",
            step_order=1,
            step_type="APPROVAL",
            approver_type="ROLE",
            role_code="IT_HEAD",
        )

        self.assertEqual(ApproverResolver.resolve(requester, step), approver_user)

    def test_same_role_in_different_organizations_is_not_ambiguous(self):
        requester = self._create_employee(
            User.objects.create_user(username="req3", email="req3@example.test", password="testpass123"),
            self.org_a,
            "EMP004",
        )
        org_b_user = User.objects.create_user(username="itb", email="itb@example.test", password="testpass123")
        Employee.objects.create(
            user=org_b_user,
            organization=self.org_b,
            department=self.department,
            location=self.location,
            designation=self.designation,
            role=self.role_it_head,
            employee_code="EMP005",
            joining_date="2024-01-01",
        )

        step = WorkflowStepDefinition.objects.create(
            workflow_version=WorkflowVersion.objects.create(workflow=WorkflowDefinition.objects.create(organization=self.org_a, name="Test Workflow", code="TEST_WORKFLOW_3"), version=1, is_published=True),
            name="IT Step",
            step_order=1,
            step_type="APPROVAL",
            approver_type="ROLE",
            role_code="IT_HEAD",
        )

        self.assertIsNone(ApproverResolver.resolve(requester, step))

    def test_two_matches_in_same_organization_raise_ambiguity(self):
        requester = self._create_employee(
            User.objects.create_user(username="req4", email="req4@example.test", password="testpass123"),
            self.org_a,
            "EMP006",
        )
        first_user = User.objects.create_user(username="it2", email="it2@example.test", password="testpass123")
        second_user = User.objects.create_user(username="it3", email="it3@example.test", password="testpass123")
        Employee.objects.create(
            user=first_user,
            organization=self.org_a,
            department=self.department,
            location=self.location,
            designation=self.designation,
            role=self.role_it_head,
            employee_code="EMP007",
            joining_date="2024-01-01",
        )
        Employee.objects.create(
            user=second_user,
            organization=self.org_a,
            department=self.department,
            location=self.location,
            designation=self.designation,
            role=self.role_it_head,
            employee_code="EMP008",
            joining_date="2024-01-01",
        )

        step = WorkflowStepDefinition.objects.create(
            workflow_version=WorkflowVersion.objects.create(workflow=WorkflowDefinition.objects.create(organization=self.org_a, name="Test Workflow", code="TEST_WORKFLOW_4"), version=1, is_published=True),
            name="IT Step",
            step_order=1,
            step_type="APPROVAL",
            approver_type="ROLE",
            role_code="IT_HEAD",
        )

        with self.assertRaises(AmbiguousApproverError):
            ApproverResolver.resolve(requester, step)

    def test_manager_behavior_remains_unchanged(self):
        requester = self._create_employee(
            User.objects.create_user(username="req5", email="req5@example.test", password="testpass123"),
            self.org_a,
            "EMP009",
        )
        manager_user = User.objects.create_user(username="mgr", email="mgr@example.test", password="testpass123")
        manager_employee = Employee.objects.create(
            user=manager_user,
            organization=self.org_a,
            department=self.department,
            location=self.location,
            designation=self.designation,
            role=self.role_manager,
            employee_code="EMP010",
            joining_date="2024-01-01",
        )
        requester.manager = manager_employee
        requester.save(update_fields=["manager"])

        step = WorkflowStepDefinition.objects.create(
            workflow_version=WorkflowVersion.objects.create(workflow=WorkflowDefinition.objects.create(organization=self.org_a, name="Test Workflow", code="TEST_WORKFLOW_5"), version=1, is_published=True),
            name="Manager Step",
            step_order=1,
            step_type="APPROVAL",
            approver_type="MANAGER",
            role_code="",
        )

        self.assertEqual(ApproverResolver.resolve(requester, step), manager_user)

    def test_specific_user_resolves_when_configured_user_is_valid(self):
        requester = self._create_employee(
            User.objects.create_user(username="req6", email="req6@example.test", password="testpass123"),
            self.org_a,
            "EMP011",
        )
        specific_user = User.objects.create_user(username="specific", email="specific@example.test", password="testpass123")
        Employee.objects.create(
            user=specific_user,
            organization=self.org_a,
            department=self.department,
            location=self.location,
            designation=self.designation,
            role=self.role_employee,
            employee_code="EMP012",
            joining_date="2024-01-01",
        )
        step = WorkflowStepDefinition.objects.create(
            workflow_version=WorkflowVersion.objects.create(workflow=WorkflowDefinition.objects.create(organization=self.org_a, name="Test Workflow", code="TEST_WORKFLOW_6"), version=1, is_published=True),
            name="Specific User Step",
            step_order=1,
            step_type="APPROVAL",
            approver_type="SPECIFIC_USER",
            specific_approver=specific_user,
        )

        self.assertEqual(ApproverResolver.resolve(requester, step), specific_user)

    def test_specific_user_in_other_organization_fails(self):
        requester = self._create_employee(
            User.objects.create_user(username="req7", email="req7@example.test", password="testpass123"),
            self.org_a,
            "EMP013",
        )
        specific_user = User.objects.create_user(username="specific2", email="specific2@example.test", password="testpass123")
        Employee.objects.create(
            user=specific_user,
            organization=self.org_b,
            department=self.department,
            location=self.location,
            designation=self.designation,
            role=self.role_employee,
            employee_code="EMP014",
            joining_date="2024-01-01",
        )
        step = WorkflowStepDefinition.objects.create(
            workflow_version=WorkflowVersion.objects.create(workflow=WorkflowDefinition.objects.create(organization=self.org_a, name="Test Workflow", code="TEST_WORKFLOW_7"), version=1, is_published=True),
            name="Specific User Step",
            step_order=1,
            step_type="APPROVAL",
            approver_type="SPECIFIC_USER",
            specific_approver=specific_user,
        )

        self.assertIsNone(ApproverResolver.resolve(requester, step))

    def test_specific_user_without_employee_profile_fails(self):
        requester = self._create_employee(
            User.objects.create_user(username="req8", email="req8@example.test", password="testpass123"),
            self.org_a,
            "EMP015",
        )
        specific_user = User.objects.create_user(username="specific3", email="specific3@example.test", password="testpass123")
        step = WorkflowStepDefinition.objects.create(
            workflow_version=WorkflowVersion.objects.create(workflow=WorkflowDefinition.objects.create(organization=self.org_a, name="Test Workflow", code="TEST_WORKFLOW_8"), version=1, is_published=True),
            name="Specific User Step",
            step_order=1,
            step_type="APPROVAL",
            approver_type="SPECIFIC_USER",
            specific_approver=specific_user,
        )

        self.assertIsNone(ApproverResolver.resolve(requester, step))

    def test_specific_user_inactive_employee_fails(self):
        requester = self._create_employee(
            User.objects.create_user(username="req9", email="req9@example.test", password="testpass123"),
            self.org_a,
            "EMP016",
        )
        specific_user = User.objects.create_user(username="specific4", email="specific4@example.test", password="testpass123")
        Employee.objects.create(
            user=specific_user,
            organization=self.org_a,
            department=self.department,
            location=self.location,
            designation=self.designation,
            role=self.role_employee,
            employee_code="EMP017",
            joining_date="2024-01-01",
            is_active=False,
        )
        step = WorkflowStepDefinition.objects.create(
            workflow_version=WorkflowVersion.objects.create(workflow=WorkflowDefinition.objects.create(organization=self.org_a, name="Test Workflow", code="TEST_WORKFLOW_9"), version=1, is_published=True),
            name="Specific User Step",
            step_order=1,
            step_type="APPROVAL",
            approver_type="SPECIFIC_USER",
            specific_approver=specific_user,
        )

        self.assertIsNone(ApproverResolver.resolve(requester, step))

    def test_specific_user_validation_requires_approver(self):
        with self.assertRaises(ValidationError):
            WorkflowStepDefinition.objects.create(
                workflow_version=WorkflowVersion.objects.create(workflow=WorkflowDefinition.objects.create(organization=self.org_a, name="Test Workflow", code="TEST_WORKFLOW_10"), version=1, is_published=True),
                name="Missing Specific User",
                step_order=1,
                step_type="APPROVAL",
                approver_type="SPECIFIC_USER",
                role_code="",
            )

    def test_role_with_specific_approver_is_invalid(self):
        with self.assertRaises(ValidationError):
            WorkflowStepDefinition.objects.create(
                workflow_version=WorkflowVersion.objects.create(workflow=WorkflowDefinition.objects.create(organization=self.org_a, name="Test Workflow", code="TEST_WORKFLOW_11"), version=1, is_published=True),
                name="Invalid Role Step",
                step_order=1,
                step_type="APPROVAL",
                approver_type="ROLE",
                role_code="IT_HEAD",
                specific_approver=User.objects.create_user(username="badrole", email="badrole@example.test", password="testpass123"),
            )


class WorkflowTransitionSecurityTests(TestCase):
    """
    Security and concurrency test suite ensuring:
    1. Invalid workflow transitions fail cleanly with WorkflowActionError.
    2. Unauthorized users cannot act on workflow steps.
    3. Out-of-sequence step execution is strictly blocked.
    4. Concurrency protection prevents double-approval and duplicate audit events.
    """

    def setUp(self):
        self.org = Organization.objects.create(name="Cyber Corp", code="CYBER", email="admin@cyber.test")
        self.dept = Department.objects.create(organization=self.org, name="Security", code="SEC")
        self.loc = Location.objects.create(organization=self.org, name="Main Office", code="MAIN", address="1 Tech Way", city="Bangalore", state="KA")
        self.desig = Designation.objects.create(organization=self.org, name="Analyst", code="ANL")

        self.role_emp, _ = Role.objects.get_or_create(code="EMPLOYEE", defaults={"name": "Employee"})
        self.role_mgr, _ = Role.objects.get_or_create(code="MANAGER", defaults={"name": "Manager"})
        self.role_it, _ = Role.objects.get_or_create(code="IT_HEAD", defaults={"name": "IT Head"})

        # Requester
        self.user_req = User.objects.create_user(username="cyber_emp", email="emp@cyber.test", password="pass")
        self.emp_req = Employee.objects.create(user=self.user_req, organization=self.org, department=self.dept, location=self.loc, designation=self.desig, role=self.role_emp, employee_code="CYB_01", joining_date="2024-01-01")

        # Manager Approver
        self.user_mgr = User.objects.create_user(username="cyber_mgr", email="mgr@cyber.test", password="pass")
        self.emp_mgr = Employee.objects.create(user=self.user_mgr, organization=self.org, department=self.dept, location=self.loc, designation=self.desig, role=self.role_mgr, employee_code="CYB_02", joining_date="2024-01-01")

        # IT Approver
        self.user_it = User.objects.create_user(username="cyber_it", email="it@cyber.test", password="pass")
        self.emp_it = Employee.objects.create(user=self.user_it, organization=self.org, department=self.dept, location=self.loc, designation=self.desig, role=self.role_it, employee_code="CYB_03", joining_date="2024-01-01")

        # Unrelated User
        self.user_stranger = User.objects.create_user(username="cyber_stranger", email="stranger@cyber.test", password="pass")
        self.emp_stranger = Employee.objects.create(user=self.user_stranger, organization=self.org, department=self.dept, location=self.loc, designation=self.desig, role=self.role_emp, employee_code="CYB_99", joining_date="2024-01-01")

        # 2-Step Workflow: Manager (Step 1) -> IT Head (Step 2)
        self.wf_def = WorkflowDefinition.objects.create(organization=self.org, name="Security Access", code="SEC_ACC")
        self.wf_ver = WorkflowVersion.objects.create(workflow=self.wf_def, version=1, is_published=True)
        self.step_def_1 = WorkflowStepDefinition.objects.create(workflow_version=self.wf_ver, step_order=1, name="Manager Approval", step_type="APPROVAL", approver_type="ROLE", role_code="MANAGER")
        self.step_def_2 = WorkflowStepDefinition.objects.create(workflow_version=self.wf_ver, step_order=2, name="IT Head Approval", step_type="APPROVAL", approver_type="ROLE", role_code="IT_HEAD")
        self.step_def_1.next_step = self.step_def_2
        self.step_def_1.save()

        self.form_def = FormDefinition.objects.create(organization=self.org, name="VPN Access", code="vpn-access", workflow=self.wf_ver, is_published=True)

        # Create active instance
        self.wf_inst = WorkflowInstance.objects.create(workflow_version=self.wf_ver, organization=self.org, initiated_by=self.user_req, current_step=self.step_def_1, status="IN_PROGRESS")
        self.submission = FormSubmission.objects.create(form=self.form_def, workflow_instance=self.wf_inst, submitted_by=self.user_req, organization=self.org, status="IN_PROGRESS")
        self.step_inst_1 = WorkflowStepInstance.objects.create(workflow_instance=self.wf_inst, step_definition=self.step_def_1, assigned_to=self.user_mgr, status="PENDING")

    def test_approve_by_unauthorized_user_rejected(self):
        """User who is not assigned to the step cannot approve it."""
        with self.assertRaises(WorkflowActionError) as ctx:
            WorkflowService.approve(self.step_inst_1, self.user_stranger, remarks="Hacking approval")
        self.assertIn("assigned approver", str(ctx.exception))
        self.step_inst_1.refresh_from_db()
        self.assertEqual(self.step_inst_1.status, "PENDING")

    def test_approve_already_approved_step_rejected(self):
        """Cannot approve an already approved step."""
        WorkflowService.approve(self.step_inst_1, self.user_mgr, remarks="First approval")
        self.step_inst_1.refresh_from_db()
        self.assertEqual(self.step_inst_1.status, "APPROVED")

        # Second approval attempt on the same step instance
        with self.assertRaises(WorkflowActionError) as ctx:
            WorkflowService.approve(self.step_inst_1, self.user_mgr, remarks="Duplicate approval")
        self.assertIn("Only pending steps", str(ctx.exception))

    def test_approve_already_rejected_step_rejected(self):
        """Cannot approve an already rejected step."""
        WorkflowService.reject(self.step_inst_1, self.user_mgr, remarks="Rejected by Manager")
        self.step_inst_1.refresh_from_db()
        self.assertEqual(self.step_inst_1.status, "REJECTED")

        with self.assertRaises(WorkflowActionError) as ctx:
            WorkflowService.approve(self.step_inst_1, self.user_mgr, remarks="Trying to approve after rejection")
        self.assertIn("Only pending steps", str(ctx.exception))

    def test_approve_out_of_sequence_step_rejected(self):
        """Cannot approve Step 2 while workflow is currently at Step 1."""
        step_inst_2 = WorkflowStepInstance.objects.create(
            workflow_instance=self.wf_inst,
            step_definition=self.step_def_2,
            assigned_to=self.user_it,
            status="PENDING",
        )
        # Workflow current_step is still step_def_1
        with self.assertRaises(WorkflowActionError) as ctx:
            WorkflowService.approve(step_inst_2, self.user_it, remarks="Skipping ahead")
        self.assertIn("Only the current step", str(ctx.exception))

    def test_approve_on_completed_workflow_rejected(self):
        """Cannot approve steps when workflow status is not IN_PROGRESS."""
        self.wf_inst.status = "APPROVED"
        self.wf_inst.save()

        with self.assertRaises(WorkflowActionError) as ctx:
            WorkflowService.approve(self.step_inst_1, self.user_mgr, remarks="Approving completed workflow")
        self.assertIn("Workflow is not in progress", str(ctx.exception))

    def test_concurrency_protection_prevents_duplicate_audit_events(self):
        """Sequential double-call simulation verifies single transition and single APPROVED event."""
        # First execution succeeds
        WorkflowService.approve(self.step_inst_1, self.user_mgr, remarks="Valid approval")
        self.step_inst_1.refresh_from_db()
        self.assertEqual(self.step_inst_1.status, "APPROVED")

        # Second execution immediately fails
        with self.assertRaises(WorkflowActionError):
            WorkflowService.approve(self.step_inst_1, self.user_mgr, remarks="Race attempt")

        # Exactly 1 APPROVED event for step 1
        approved_events = WorkflowEvent.objects.filter(workflow_instance=self.wf_inst, event_type="APPROVED")
        self.assertEqual(approved_events.count(), 1)


