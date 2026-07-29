from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from departments.models import Department
from designations.models import Designation
from employees.models import Employee
from forms_engine.models import FormDefinition, FormField
from forms_engine.services import FormEngineService
from locations.models import Location
from notifications.models import Notification
from notifications.services import NotificationService
from organizations.models import Organization
from rbac.models import Role
from workflow.models.instances import WorkflowInstance, WorkflowStepInstance
from workflow.models.workflow import WorkflowDefinition, WorkflowStepDefinition, WorkflowVersion
from workflow.services.workflow_service import WorkflowService


class NotificationLifecycleTests(TestCase):

    def setUp(self):
        self.organization = Organization.objects.create(
            name="Acme Corp",
            code="ACME",
            email="hr@acme.test",
        )
        self.department = Department.objects.create(
            organization=self.organization,
            name="Engineering",
            code="ENG",
        )
        self.location = Location.objects.create(
            organization=self.organization,
            name="HQ",
            code="HQ",
            location_type="HQ",
            address="123 Main St",
            city="Mumbai",
            state="MH",
        )
        self.designation = Designation.objects.create(
            organization=self.organization,
            name="Engineer",
            code="ENG",
        )

        self.role_employee = Role.objects.create(name="Employee", code="EMPLOYEE")
        self.role_it_head = Role.objects.create(name="IT Head", code="IT_HEAD")
        self.role_hr_head = Role.objects.create(name="HR Head", code="HR_HEAD")

        self.requester_user = User.objects.create_user(
            username="requester",
            email="requester@acme.test",
            password="testpass123",
        )
        self.requester_employee = Employee.objects.create(
            user=self.requester_user,
            organization=self.organization,
            department=self.department,
            location=self.location,
            designation=self.designation,
            role=self.role_employee,
            employee_code="EMP001",
            joining_date="2024-01-01",
        )

        self.it_head_user = User.objects.create_user(
            username="it_head",
            email="it_head@acme.test",
            password="testpass123",
        )
        self.it_head_employee = Employee.objects.create(
            user=self.it_head_user,
            organization=self.organization,
            department=self.department,
            location=self.location,
            designation=self.designation,
            role=self.role_it_head,
            employee_code="EMP002",
            joining_date="2024-01-01",
        )

        self.hr_head_user = User.objects.create_user(
            username="hr_head",
            email="hr_head@acme.test",
            password="testpass123",
        )
        self.hr_head_employee = Employee.objects.create(
            user=self.hr_head_user,
            organization=self.organization,
            department=self.department,
            location=self.location,
            designation=self.designation,
            role=self.role_hr_head,
            employee_code="EMP003",
            joining_date="2024-01-01",
        )

    def _create_workflow(self, role_codes, workflow_code="REQUEST"):
        workflow_definition = WorkflowDefinition.objects.create(
            organization=self.organization,
            name=f"{workflow_code} workflow",
            code=workflow_code,
        )
        workflow_version = WorkflowVersion.objects.create(
            workflow=workflow_definition,
            version=1,
            is_published=True,
        )

        previous_step = None
        steps = []
        for index, role_code in enumerate(role_codes, start=1):
            step = WorkflowStepDefinition.objects.create(
                workflow_version=workflow_version,
                name=f"{role_code} Approval",
                step_order=index,
                step_type="APPROVAL",
                approver_type="ROLE",
                role_code=role_code,
            )
            if previous_step is not None:
                previous_step.next_step = step
                previous_step.save(update_fields=["next_step"])
            previous_step = step
            steps.append(step)

        form_definition = FormDefinition.objects.create(
            organization=self.organization,
            name=f"{workflow_code} form",
            code=f"{workflow_code.lower()}_form",
            workflow=workflow_version,
            is_published=True,
        )
        FormField.objects.create(
            form=form_definition,
            label="Request Type",
            field_name="request_type",
            field_type="text",
            order=1,
        )

        return workflow_definition, workflow_version, form_definition, steps

    def _submit_request(self, form_definition, submitted_by=None, cleaned_data=None):
        return FormEngineService.submit(
            form_definition,
            submitted_by or self.requester_user,
            cleaned_data or {"request_type": "Laptop request"},
        )

    def test_submission_notification_is_created_for_requester(self):
        _, _, form_definition, _ = self._create_workflow(["IT_HEAD"])

        self._submit_request(form_definition)

        notification = Notification.objects.get(
            recipient=self.requester_user,
            notification_type="SUBMITTED",
        )
        self.assertEqual(notification.title, "Request submitted")
        self.assertFalse(notification.is_read)

    def test_assignment_notification_is_created_for_approver(self):
        _, _, form_definition, _ = self._create_workflow(["IT_HEAD"])

        self._submit_request(form_definition)

        notification = Notification.objects.get(
            recipient=self.it_head_user,
            notification_type="ASSIGNED",
        )
        self.assertEqual(notification.title, "New workflow assignment")

    def test_approval_notification_is_created_for_requester(self):
        _, _, form_definition, steps = self._create_workflow(["IT_HEAD", "HR_HEAD"])

        submission = self._submit_request(form_definition)
        workflow_instance = submission.workflow_instance
        step_instance = workflow_instance.steps.get(step_definition=steps[0])

        WorkflowService.approve(step_instance, self.it_head_user)

        notification = Notification.objects.get(
            recipient=self.requester_user,
            notification_type="APPROVED",
        )
        self.assertEqual(notification.workflow_instance, workflow_instance)

    def test_rejection_notification_is_created_for_requester(self):
        _, _, form_definition, steps = self._create_workflow(["IT_HEAD"])

        submission = self._submit_request(form_definition)
        workflow_instance = submission.workflow_instance
        step_instance = workflow_instance.steps.get(step_definition=steps[0])

        WorkflowService.reject(step_instance, self.it_head_user, remarks="Needs revision")

        notification = Notification.objects.get(
            recipient=self.requester_user,
            notification_type="REJECTED",
        )
        self.assertEqual(notification.workflow_instance, workflow_instance)

    def test_completion_notification_is_created_for_requester(self):
        _, _, form_definition, steps = self._create_workflow(["IT_HEAD"])

        submission = self._submit_request(form_definition)
        workflow_instance = submission.workflow_instance
        step_instance = workflow_instance.steps.get(step_definition=steps[0])

        WorkflowService.approve(step_instance, self.it_head_user)

        notification = Notification.objects.get(
            recipient=self.requester_user,
            notification_type="COMPLETED",
        )
        self.assertEqual(notification.workflow_instance, workflow_instance)

    def test_unread_count_mark_read_and_mark_all_read(self):
        NotificationService.notify(self.requester_user, "SUBMITTED", "Request submitted", "Hello")
        NotificationService.notify(self.requester_user, "ASSIGNED", "New workflow assignment", "Hello")

        self.assertEqual(Notification.objects.filter(recipient=self.requester_user, is_read=False).count(), 2)

        notification = Notification.objects.filter(recipient=self.requester_user).latest("created_at")
        self.client.force_login(self.requester_user)
        self.client.post(reverse("notifications:mark-read", args=[notification.pk]))
        self.assertTrue(Notification.objects.get(pk=notification.pk).is_read)

        self.client.post(reverse("notifications:mark-all-read"))
        self.assertEqual(Notification.objects.filter(recipient=self.requester_user, is_read=False).count(), 0)

    def test_user_cannot_access_or_update_another_users_notification(self):
        other_user = User.objects.create_user(username="other", email="other@acme.test", password="testpass123")
        notification = NotificationService.notify(other_user, "SUBMITTED", "Request submitted", "Hello")

        self.client.force_login(self.requester_user)

        response = self.client.get(reverse("notifications:list"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, notification.title)

        response = self.client.post(reverse("notifications:mark-read", args=[notification.pk]))
        self.assertEqual(response.status_code, 404)

        self.assertFalse(Notification.objects.get(pk=notification.pk).is_read)
