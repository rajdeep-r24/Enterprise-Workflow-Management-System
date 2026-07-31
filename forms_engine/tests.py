from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from accounts.models import User
from departments.models import Department
from designations.models import Designation
from employees.models import Employee
from forms_engine.models import FormDefinition, FormField, FormSubmission, RequestAttachment
from forms_engine.services import FormEngineService
from locations.models import Location
from organizations.models import Organization
from rbac.models import Role
from workflow.models.events import WorkflowEvent
from workflow.models.instances import WorkflowInstance, WorkflowStepInstance
from workflow.models.workflow import (
    WorkflowDefinition,
    WorkflowStepDefinition,
    WorkflowVersion,
)
from workflow.services.approver_resolver import AmbiguousApproverError, ApproverResolver
from workflow.services.workflow_service import WorkflowService


class ForgeFlowWorkflowIntegrationTests(TestCase):

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
        self.role_unit_head = Role.objects.create(name="Unit Head", code="UNIT_HEAD")
        self.role_manager = Role.objects.create(name="Manager", code="MANAGER")

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

        self.unit_head_user = User.objects.create_user(
            username="unit_head",
            email="unit_head@acme.test",
            password="testpass123",
        )
        self.unit_head_employee = Employee.objects.create(
            user=self.unit_head_user,
            organization=self.organization,
            department=self.department,
            location=self.location,
            designation=self.designation,
            role=self.role_unit_head,
            employee_code="EMP004",
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

    def test_employee_submission_creates_workflow_and_pending_first_step(self):
        _, _, form_definition, steps = self._create_workflow(["IT_HEAD"])

        submission = self._submit_request(form_definition)

        workflow_instance = submission.workflow_instance

        self.assertIsNotNone(workflow_instance)
        self.assertEqual(WorkflowInstance.objects.count(), 1)
        self.assertEqual(FormSubmission.objects.count(), 1)
        self.assertEqual(workflow_instance.status, "IN_PROGRESS")
        self.assertEqual(submission.status, "SUBMITTED")

        step_instances = workflow_instance.steps.all()
        self.assertEqual(step_instances.count(), 1)
        first_step_instance = step_instances.get(step_definition=steps[0])
        self.assertEqual(first_step_instance.status, "PENDING")
        self.assertEqual(first_step_instance.assigned_to, self.it_head_user)

    def test_multi_step_approval_flow_moves_between_approvers_and_completes(self):
        _, _, form_definition, steps = self._create_workflow(
            ["IT_HEAD", "HR_HEAD", "UNIT_HEAD"]
        )

        submission = self._submit_request(form_definition)
        workflow_instance = submission.workflow_instance

        first_step_instance = workflow_instance.steps.get(step_definition=steps[0])
        self.assertEqual(workflow_instance.steps.count(), 1)
        self.assertEqual(first_step_instance.status, "PENDING")

        WorkflowService.approve(first_step_instance, self.it_head_user)
        workflow_instance.refresh_from_db()
        hr_step_instance = workflow_instance.steps.get(step_definition=steps[1])

        self.assertEqual(workflow_instance.status, "IN_PROGRESS")
        self.assertEqual(workflow_instance.current_step, steps[1])
        self.assertEqual(hr_step_instance.status, "PENDING")
        self.assertEqual(hr_step_instance.assigned_to, self.hr_head_user)

        WorkflowService.approve(hr_step_instance, self.hr_head_user)
        workflow_instance.refresh_from_db()
        unit_step_instance = workflow_instance.steps.get(step_definition=steps[2])

        self.assertEqual(workflow_instance.current_step, steps[2])
        self.assertEqual(unit_step_instance.status, "PENDING")
        self.assertEqual(unit_step_instance.assigned_to, self.unit_head_user)

        WorkflowService.approve(unit_step_instance, self.unit_head_user)
        workflow_instance.refresh_from_db()
        submission.refresh_from_db()

        self.assertEqual(workflow_instance.status, "APPROVED")
        self.assertIsNone(workflow_instance.current_step)
        self.assertEqual(submission.status, "APPROVED")
        self.assertEqual(workflow_instance.steps.count(), 3)

    def test_rejection_stops_workflow_and_skips_later_steps(self):
        _, _, form_definition, steps = self._create_workflow(["IT_HEAD", "HR_HEAD"])

        submission = self._submit_request(form_definition)
        workflow_instance = submission.workflow_instance
        first_step_instance = workflow_instance.steps.get(step_definition=steps[0])

        WorkflowService.reject(first_step_instance, self.it_head_user, remarks="Needs revision")
        workflow_instance.refresh_from_db()
        submission.refresh_from_db()

        self.assertEqual(workflow_instance.status, "REJECTED")
        self.assertEqual(submission.status, "REJECTED")
        self.assertIsNone(workflow_instance.current_step)
        self.assertEqual(workflow_instance.steps.count(), 1)
        self.assertFalse(workflow_instance.steps.filter(step_definition=steps[1]).exists())

    def test_manager_role_is_resolved_from_requesters_manager(self):
        manager_user = User.objects.create_user(
            username="manager",
            email="manager@acme.test",
            password="testpass123",
        )
        manager_employee = Employee.objects.create(
            user=manager_user,
            organization=self.organization,
            department=self.department,
            location=self.location,
            designation=self.designation,
            role=self.role_manager,
            employee_code="EMP005",
            joining_date="2024-01-01",
        )
        self.requester_employee.manager = manager_employee
        self.requester_employee.save(update_fields=["manager"])

        _, _, form_definition, steps = self._create_workflow(["MANAGER"])
        submission = self._submit_request(form_definition)
        workflow_instance = submission.workflow_instance
        first_step_instance = workflow_instance.steps.get(step_definition=steps[0])

        self.assertEqual(first_step_instance.assigned_to, manager_user)

    def test_missing_approver_rolls_back_submission_and_workflow(self):
        _, _, form_definition, _ = self._create_workflow(["NO_APPROVER"])

        before_workflow_count = WorkflowInstance.objects.count()
        before_submission_count = FormSubmission.objects.count()
        before_event_count = WorkflowEvent.objects.count()

        with self.assertRaises(ValueError):
            self._submit_request(form_definition)

        self.assertEqual(WorkflowInstance.objects.count(), before_workflow_count)
        self.assertEqual(FormSubmission.objects.count(), before_submission_count)
        self.assertEqual(WorkflowEvent.objects.count(), before_event_count)

    def test_workflow_events_record_submission_assignment_and_completion(self):
        _, _, form_definition, steps = self._create_workflow(["IT_HEAD", "HR_HEAD"])

        submission = self._submit_request(form_definition)
        workflow_instance = submission.workflow_instance
        first_step_instance = workflow_instance.steps.get(step_definition=steps[0])

        WorkflowService.approve(first_step_instance, self.it_head_user)
        second_step_instance = workflow_instance.steps.get(step_definition=steps[1])
        WorkflowService.approve(second_step_instance, self.hr_head_user)

        event_types = list(
            workflow_instance.events.values_list("event_type", flat=True)
        )

        self.assertEqual(
            event_types,
            ["SUBMITTED", "ASSIGNED", "APPROVED", "ASSIGNED", "APPROVED", "COMPLETED"],
        )

    def test_role_resolution_is_scoped_to_the_requesters_organization(self):
        other_org = Organization.objects.create(
            name="Beta Corp",
            code="BETA",
            email="hr@beta.test",
        )
        other_department = Department.objects.create(
            organization=other_org,
            name="Operations",
            code="OPS",
        )
        other_location = Location.objects.create(
            organization=other_org,
            name="Branch",
            code="BR",
            location_type="HQ",
            address="456 Main St",
            city="Delhi",
            state="DL",
        )
        other_designation = Designation.objects.create(
            organization=other_org,
            name="Manager",
            code="MGR",
        )

        other_it_head_user = User.objects.create_user(
            username="other_it_head",
            email="other_it_head@beta.test",
            password="testpass123",
        )
        Employee.objects.create(
            user=other_it_head_user,
            organization=other_org,
            department=other_department,
            location=other_location,
            designation=other_designation,
            role=self.role_it_head,
            employee_code="EMP006",
            joining_date="2024-01-01",
        )

        other_requester_user = User.objects.create_user(
            username="requester_beta",
            email="requester_beta@beta.test",
            password="testpass123",
        )
        other_requester_employee = Employee.objects.create(
            user=other_requester_user,
            organization=other_org,
            department=other_department,
            location=other_location,
            designation=other_designation,
            role=self.role_employee,
            employee_code="EMP007",
            joining_date="2024-01-01",
        )

        workflow_definition = WorkflowDefinition.objects.create(
            organization=self.organization,
            name="Resolver Test Workflow",
            code="RESOLVER_TEST",
        )

        workflow_version = WorkflowVersion.objects.create(
            workflow=workflow_definition,
            version=1,
            is_published=True,
        )

        role_step = WorkflowStepDefinition.objects.create(
            workflow_version=workflow_version,
            name="IT Head Approval",
            step_order=1,
            step_type="APPROVAL",
            approver_type="ROLE",
            role_code="IT_HEAD",
        )

        self.assertEqual(
            ApproverResolver.resolve(
                self.requester_employee,
                role_step,
            ),
            self.it_head_user,
        )

        self.assertEqual(
            ApproverResolver.resolve(
                other_requester_employee,
                role_step,
            ),
            other_it_head_user,
        )

    def test_manager_resolution_still_uses_employee_manager(self):
        manager_user = User.objects.create_user(
            username="manager_user",
            email="manager_user@acme.test",
            password="testpass123",
        )

        manager_employee = Employee.objects.create(
            user=manager_user,
            organization=self.organization,
            department=self.department,
            location=self.location,
            designation=self.designation,
            role=self.role_manager,
            employee_code="EMP008",
            joining_date="2024-01-01",
        )

        self.requester_employee.manager = manager_employee
        self.requester_employee.save(
            update_fields=["manager"]
        )

        workflow_definition = WorkflowDefinition.objects.create(
            organization=self.organization,
            name="Manager Resolver Test Workflow",
            code="MANAGER_RESOLVER_TEST",
        )

        workflow_version = WorkflowVersion.objects.create(
            workflow=workflow_definition,
            version=1,
            is_published=True,
        )

        manager_step = WorkflowStepDefinition.objects.create(
            workflow_version=workflow_version,
            name="Manager Approval",
            step_order=1,
            step_type="APPROVAL",
            approver_type="MANAGER",
        )

        self.assertEqual(
            ApproverResolver.resolve(
                self.requester_employee,
                manager_step,
            ),
            manager_user,
        )

    def test_missing_matching_approver_returns_none(self):
        step = WorkflowStepDefinition.objects.create(
            workflow_version=WorkflowVersion.objects.create(
                workflow=WorkflowDefinition.objects.create(
                    organization=self.organization,
                    name="Missing Approver Workflow",
                    code="MISSING_APPROVER",
                ),
                version=1,
                is_published=True,
            ),
            name="Missing Step",
            step_order=1,
            step_type="APPROVAL",
            approver_type="ROLE",
            role_code="SENIOR_DIRECTOR",
        )
        self.assertIsNone(ApproverResolver.resolve(self.requester_employee, step))

    def test_submission_rolls_back_when_first_step_resolution_is_ambiguous(self):
        other_it_user = User.objects.create_user(
            username="other_it_ambiguous",
            email="other_it_ambiguous@acme.test",
            password="testpass123",
        )
        Employee.objects.create(
            user=other_it_user,
            organization=self.organization,
            department=self.department,
            location=self.location,
            designation=self.designation,
            role=self.role_it_head,
            employee_code="EMP009",
            joining_date="2024-01-01",
        )

        _, _, form_definition, _ = self._create_workflow(["IT_HEAD"])

        with self.assertRaises(AmbiguousApproverError):
            self._submit_request(form_definition)

        self.assertEqual(WorkflowInstance.objects.count(), 0)
        self.assertEqual(FormSubmission.objects.count(), 0)
        self.assertEqual(WorkflowEvent.objects.count(), 0)

    def test_approval_progression_rolls_back_when_next_step_resolution_is_ambiguous(self):
        _, _, form_definition, steps = self._create_workflow(["IT_HEAD", "HR_HEAD"])
        submission = self._submit_request(form_definition)
        workflow_instance = submission.workflow_instance
        first_step_instance = workflow_instance.steps.get(step_definition=steps[0])

        other_hr_user = User.objects.create_user(
            username="other_hr_ambiguous",
            email="other_hr_ambiguous@acme.test",
            password="testpass123",
        )
        Employee.objects.create(
            user=other_hr_user,
            organization=self.organization,
            department=self.department,
            location=self.location,
            designation=self.designation,
            role=self.role_hr_head,
            employee_code="EMP010",
            joining_date="2024-01-01",
        )

        with self.assertRaises(AmbiguousApproverError):
            WorkflowService.approve(first_step_instance, self.it_head_user)

        workflow_instance.refresh_from_db()
        first_step_instance.refresh_from_db()
        submission.refresh_from_db()

        self.assertEqual(workflow_instance.status, "IN_PROGRESS")
        self.assertEqual(first_step_instance.status, "PENDING")
        self.assertEqual(submission.status, "SUBMITTED")
        self.assertEqual(workflow_instance.steps.count(), 1)

    def test_submission_with_attachment_saves_attachment(self):
        _, _, form_definition, steps = self._create_workflow(["IT_HEAD"])
        
        self.client.force_login(self.requester_user)
        
        test_file = SimpleUploadedFile(
            "test_doc.pdf", b"file_content", content_type="application/pdf"
        )
        
        url = reverse("submit-request", args=[form_definition.code])
        response = self.client.post(url, {
            "request_type": "Need PDF",
            "attachments": [test_file]
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FormSubmission.objects.count(), 1)
        self.assertEqual(RequestAttachment.objects.count(), 1)
        attachment = RequestAttachment.objects.first()
        self.assertEqual(attachment.original_filename, "test_doc.pdf")
        self.assertEqual(attachment.uploaded_by, self.requester_user)

    def test_invalid_extension_rejected(self):
        _, _, form_definition, steps = self._create_workflow(["IT_HEAD"])
        self.client.force_login(self.requester_user)
        
        test_file = SimpleUploadedFile(
            "test_script.exe", b"bad_content", content_type="application/x-msdownload"
        )
        url = reverse("submit-request", args=[form_definition.code])
        response = self.client.post(url, {
            "request_type": "Need PDF",
            "attachments": [test_file]
        })
        
        self.assertEqual(response.status_code, 200) # Form rendered with errors
        self.assertContains(response, "invalid extension")
        self.assertEqual(FormSubmission.objects.count(), 0)

    def test_oversized_file_rejected(self):
        _, _, form_definition, steps = self._create_workflow(["IT_HEAD"])
        self.client.force_login(self.requester_user)
        
        large_content = b"0" * (11 * 1024 * 1024)
        test_file = SimpleUploadedFile(
            "large_doc.pdf", large_content, content_type="application/pdf"
        )
        url = reverse("submit-request", args=[form_definition.code])
        response = self.client.post(url, {
            "request_type": "Need large",
            "attachments": [test_file]
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "exceeds the 10MB size limit")
        self.assertEqual(FormSubmission.objects.count(), 0)

    def test_authorized_users_can_download_attachment(self):
        _, _, form_definition, steps = self._create_workflow(["IT_HEAD"])
        
        submission = self._submit_request(form_definition)
        test_file = SimpleUploadedFile(
            "test_doc.pdf", b"file_content", content_type="application/pdf"
        )
        attachment = RequestAttachment.objects.create(
            submission=submission,
            file=test_file,
            original_filename="test_doc.pdf",
            uploaded_by=self.requester_user
        )
        
        download_url = reverse("download-attachment", args=[attachment.pk])
        
        # Requester can download
        self.client.force_login(self.requester_user)
        response = self.client.get(download_url)
        self.assertEqual(response.status_code, 200)
        
        # IT Head (assigned approver) can download
        self.client.force_login(self.it_head_user)
        response = self.client.get(download_url)
        self.assertEqual(response.status_code, 200)
        
        # HR Head (administrative role) can download
        self.client.force_login(self.hr_head_user)
        response = self.client.get(download_url)
        self.assertEqual(response.status_code, 200)
        
        # Unrelated normal employee cannot download
        unrelated_user = User.objects.create_user(
            username="unrelated", email="unrelated@acme.test", password="pass"
        )
        Employee.objects.create(
            user=unrelated_user,
            organization=self.organization,
            department=self.department,
            location=self.location,
            designation=self.designation,
            role=self.role_employee,
            employee_code="EMP999",
            joining_date="2024-01-01",
        )
        self.client.force_login(unrelated_user)
        response = self.client.get(download_url)
        self.assertEqual(response.status_code, 403)


class RequestTypeFieldManagementTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.organization = Organization.objects.create(name="Acme Corp", code="ACME", email="acme@test.com")
        self.other_organization = Organization.objects.create(name="Globex", code="GLBX", email="globex@test.com")
        
        # We need a department, designation and location to satisfy constraints
        from employees.models import Department, Designation, Location
        self.department = Department.objects.create(name="Engineering", code="ENG", organization=self.organization)
        self.designation = Designation.objects.create(name="Engineer", code="ENGR", organization=self.organization)
        self.location = Location.objects.create(name="Headquarters", code="HQ", organization=self.organization)
        
        self.role_org_admin = Role.objects.create(name="Org Admin", code="ORG_ADMIN")
        
        self.admin_user = User.objects.create_user(username="admin", email="admin@acme.test", password="testpass123")
        self.admin_employee = Employee.objects.create(
            user=self.admin_user,
            organization=self.organization,
            department=self.department,
            designation=self.designation,
            location=self.location,
            role=self.role_org_admin,
            employee_code="EMP001",
            joining_date="2024-01-01",
        )
        
        self.workflow_definition = WorkflowDefinition.objects.create(
            organization=self.organization,
            name="Test workflow",
            code="test",
        )
        self.workflow_version = WorkflowVersion.objects.create(
            workflow=self.workflow_definition,
            version=1,
            is_latest=True,
        )
        
        self.draft_form = FormDefinition.objects.create(
            organization=self.organization,
            name="Draft Form",
            code="draft",
            workflow=self.workflow_version,
            is_published=False,
        )
        
        self.published_form = FormDefinition.objects.create(
            organization=self.organization,
            name="Published Form",
            code="published",
            workflow=self.workflow_version,
            is_published=True,
        )
        
        self.draft_field = FormField.objects.create(
            form=self.draft_form,
            label="Old Field",
            field_name="old_field",
            field_type="text",
        )
        
        self.published_field = FormField.objects.create(
            form=self.published_form,
            label="Pub Field",
            field_name="pub_field",
            field_type="text",
        )
        
        # Cross tenant setup
        self.other_workflow_definition = WorkflowDefinition.objects.create(
            organization=self.other_organization,
            name="Other workflow",
            code="other",
        )
        self.other_workflow_version = WorkflowVersion.objects.create(
            workflow=self.other_workflow_definition,
            version=1,
            is_latest=True,
        )
        self.other_form = FormDefinition.objects.create(
            organization=self.other_organization,
            name="Other Form",
            code="other",
            workflow=self.other_workflow_version,
            is_published=False,
        )

    def test_tenant_scoping(self):
        self.client.login(username="admin@acme.test", password="testpass123")
        response = self.client.get(reverse("request-type-fields", args=[self.other_form.pk]))
        self.assertEqual(response.status_code, 404)

    def test_add_field_draft_success(self):
        self.client.login(username="admin@acme.test", password="testpass123")
        response = self.client.post(reverse("request-type-field-add", args=[self.draft_form.pk]), {
            "label": "New Field",
            "field_name": "new_field",
            "field_type": "text",
            "is_required": True,
            "order": 1,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(FormField.objects.filter(form=self.draft_form, field_name="new_field").exists())

    def test_edit_field_draft_success(self):
        self.client.login(username="admin@acme.test", password="testpass123")
        response = self.client.post(reverse("request-type-field-edit", args=[self.draft_form.pk, self.draft_field.pk]), {
            "label": "Updated Field",
            "field_name": "old_field",
            "field_type": "textarea",
            "order": 1,
        })
        self.assertEqual(response.status_code, 302)
        self.draft_field.refresh_from_db()
        self.assertEqual(self.draft_field.label, "Updated Field")
        self.assertEqual(self.draft_field.field_type, "textarea")

    def test_delete_field_draft_success(self):
        self.client.login(username="admin@acme.test", password="testpass123")
        response = self.client.post(reverse("request-type-field-delete", args=[self.draft_form.pk, self.draft_field.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(FormField.objects.filter(pk=self.draft_field.pk).exists())

    def test_published_form_protection(self):
        self.client.login(username="admin@acme.test", password="testpass123")
        
        # Try add
        response = self.client.post(reverse("request-type-field-add", args=[self.published_form.pk]), {
            "label": "New Field",
            "field_name": "new_field",
            "field_type": "text",
            "order": 1,
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(FormField.objects.filter(form=self.published_form, field_name="new_field").exists())
        
        # Try edit
        response = self.client.post(reverse("request-type-field-edit", args=[self.published_form.pk, self.published_field.pk]), {
            "label": "Updated Field",
            "field_name": "pub_field",
            "field_type": "textarea",
            "order": 1,
        })
        self.assertEqual(response.status_code, 302)
        self.published_field.refresh_from_db()
        self.assertEqual(self.published_field.label, "Pub Field")
        
        # Try delete
        response = self.client.post(reverse("request-type-field-delete", args=[self.published_form.pk, self.published_field.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(FormField.objects.filter(pk=self.published_field.pk).exists())
