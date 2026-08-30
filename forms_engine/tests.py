from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from accounts.models import User
from departments.models import Department
from designations.models import Designation
from employees.models import Employee
from forms_engine.models import FormDefinition, FormField, FormSubmission, FormSubmissionValue, RequestAttachment, RequestComment
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

        self.role_employee, _ = Role.objects.get_or_create(code="EMPLOYEE", defaults={"name": "Employee"})
        self.role_it_head, _ = Role.objects.get_or_create(code="IT_HEAD", defaults={"name": "IT Head"})
        self.role_hr_head, _ = Role.objects.get_or_create(code="HR_HEAD", defaults={"name": "HR Head"})
        self.role_unit_head, _ = Role.objects.get_or_create(code="UNIT_HEAD", defaults={"name": "Unit Head"})
        self.role_manager, _ = Role.objects.get_or_create(code="MANAGER", defaults={"name": "Manager"})

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
        
        self.role_org_admin, _ = Role.objects.get_or_create(code="ORG_ADMIN", defaults={"name": "Org Admin"})
        
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


class RequestCommentAndDiscussionTests(TestCase):

    def setUp(self):
        from notifications.models import Notification
        self.Notification = Notification

        # Org A
        self.org_a = Organization.objects.create(name="Acme Corp", code="ACME", email="admin@acme.test")
        self.dept_a = Department.objects.create(organization=self.org_a, name="Engineering", code="ENG")
        self.loc_a = Location.objects.create(organization=self.org_a, name="HQ", code="HQ", address="123 St", city="Mumbai", state="MH")
        self.desig_a = Designation.objects.create(organization=self.org_a, name="Engineer", code="ENG")

        # Roles
        self.role_emp, _ = Role.objects.get_or_create(code="EMPLOYEE", defaults={"name": "Employee"})
        self.role_mgr, _ = Role.objects.get_or_create(code="MANAGER", defaults={"name": "Manager"})
        self.role_admin, _ = Role.objects.get_or_create(code="ADMIN", defaults={"name": "Admin"})
        self.role_it_head, _ = Role.objects.get_or_create(code="IT_HEAD", defaults={"name": "IT Head"})

        # Users in Org A
        self.requester = User.objects.create_user(username="req_user", email="req@acme.test", password="pass123", first_name="Rahul", last_name="Sharma")
        self.emp_requester = Employee.objects.create(user=self.requester, organization=self.org_a, department=self.dept_a, location=self.loc_a, designation=self.desig_a, role=self.role_emp, employee_code="EMP_R", joining_date="2024-01-01")

        self.approver = User.objects.create_user(username="app_user", email="app@acme.test", password="pass123", first_name="Vikram", last_name="Sahay")
        self.emp_approver = Employee.objects.create(user=self.approver, organization=self.org_a, department=self.dept_a, location=self.loc_a, designation=self.desig_a, role=self.role_mgr, employee_code="EMP_A", joining_date="2024-01-01")

        self.admin = User.objects.create_user(username="adm_user", email="adm@acme.test", password="pass123", first_name="Admin", last_name="User")
        self.emp_admin = Employee.objects.create(user=self.admin, organization=self.org_a, department=self.dept_a, location=self.loc_a, designation=self.desig_a, role=self.role_admin, employee_code="EMP_AD", joining_date="2024-01-01")

        self.other_emp = User.objects.create_user(username="oth_user", email="oth@acme.test", password="pass123", first_name="Other", last_name="User")
        self.emp_other = Employee.objects.create(user=self.other_emp, organization=self.org_a, department=self.dept_a, location=self.loc_a, designation=self.desig_a, role=self.role_emp, employee_code="EMP_O", joining_date="2024-01-01")

        # Org B User (for tenant isolation test)
        self.org_b = Organization.objects.create(name="Beta Corp", code="BETA", email="admin@beta.test")
        self.dept_b = Department.objects.create(organization=self.org_b, name="Sales", code="SAL")
        self.loc_b = Location.objects.create(organization=self.org_b, name="HQ B", code="HQB", address="456 St", city="Delhi", state="DL")
        self.desig_b = Designation.objects.create(organization=self.org_b, name="Executive", code="EXEC")
        self.user_org_b = User.objects.create_user(username="beta_user", email="user@beta.test", password="pass123")
        self.emp_org_b = Employee.objects.create(user=self.user_org_b, organization=self.org_b, department=self.dept_b, location=self.loc_b, designation=self.desig_b, role=self.role_admin, employee_code="EMP_B", joining_date="2024-01-01")

        # Workflow & Form
        self.wf_def = WorkflowDefinition.objects.create(organization=self.org_a, name="Hardware Approval", code="HW_APP")
        self.wf_ver = WorkflowVersion.objects.create(workflow=self.wf_def, version=1, is_published=True, is_latest=True)
        self.step_def = WorkflowStepDefinition.objects.create(
            workflow_version=self.wf_ver,
            step_order=1,
            name="Manager Review",
            step_type="APPROVAL",
            approver_type="ROLE",
            role_code="MANAGER",
        )

        self.form_def = FormDefinition.objects.create(organization=self.org_a, name="Laptop Request", code="laptop-req", workflow=self.wf_ver, is_published=True)
        self.field_1 = FormField.objects.create(form=self.form_def, label="Laptop Model", field_name="laptop_model", field_type="text", is_required=True, order=1)

        # Create active submission
        self.wf_inst = WorkflowInstance.objects.create(organization=self.org_a, workflow_version=self.wf_ver, initiated_by=self.requester, status="IN_PROGRESS")
        self.step_inst = WorkflowStepInstance.objects.create(workflow_instance=self.wf_inst, step_definition=self.step_def, assigned_to=self.approver, status="PENDING")
        self.wf_inst.current_step = self.step_def
        self.wf_inst.save()

        self.submission = FormSubmission.objects.create(form=self.form_def, organization=self.org_a, workflow_instance=self.wf_inst, submitted_by=self.requester, status="SUBMITTED")

    def test_requester_can_comment(self):
        self.client.force_login(self.requester)
        url = reverse("add-request-comment", args=[self.submission.pk])
        response = self.client.post(url, {"message": "Need this urgent for client project."})
        self.assertEqual(response.status_code, 302)
        
        # Verify comment created
        self.assertEqual(RequestComment.objects.filter(submission=self.submission).count(), 1)
        comment = RequestComment.objects.first()
        self.assertEqual(comment.author, self.requester)
        self.assertEqual(comment.message, "Need this urgent for client project.")
        
        # Verify notification sent to pending approver
        notif = self.Notification.objects.filter(recipient=self.approver).first()
        self.assertIsNotNone(notif)
        self.assertIn("Requester Replied", notif.title)
        self.assertEqual(notif.notification_type, "COMMENT")

    def test_assigned_approver_can_comment(self):
        self.client.force_login(self.approver)
        url = reverse("add-request-comment", args=[self.submission.pk])
        response = self.client.post(url, {"message": "Please specify whether 16GB or 32GB RAM is needed."})
        self.assertEqual(response.status_code, 302)
        
        # Verify comment created
        self.assertEqual(RequestComment.objects.filter(submission=self.submission).count(), 1)
        comment = RequestComment.objects.first()
        self.assertEqual(comment.author, self.approver)
        
        # Verify notification sent to requester
        notif = self.Notification.objects.filter(recipient=self.requester).first()
        self.assertIsNotNone(notif)
        self.assertIn("New Note", notif.title)
        self.assertEqual(notif.notification_type, "COMMENT")

    def test_authorized_admin_can_comment(self):
        self.client.force_login(self.admin)
        url = reverse("add-request-comment", args=[self.submission.pk])
        response = self.client.post(url, {"message": "IT inventory has MacBook in stock."})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(RequestComment.objects.filter(submission=self.submission, author=self.admin).count(), 1)

    def test_unauthorized_user_cannot_comment(self):
        self.client.force_login(self.other_emp)
        url = reverse("add-request-comment", args=[self.submission.pk])
        response = self.client.post(url, {"message": "Attempting unauthorized note."})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(RequestComment.objects.filter(submission=self.submission).count(), 0)

    def test_tenant_isolation_on_comment(self):
        self.client.force_login(self.user_org_b)
        url = reverse("add-request-comment", args=[self.submission.pk])
        response = self.client.post(url, {"message": "Cross-tenant intrusion attempt."})
        # Tenant isolation middleware / get_object_or_404 returns 404
        self.assertEqual(response.status_code, 404)
        self.assertEqual(RequestComment.objects.count(), 0)

    def test_empty_comment_rejected(self):
        self.client.force_login(self.requester)
        url = reverse("add-request-comment", args=[self.submission.pk])
        response = self.client.post(url, {"message": "   "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(RequestComment.objects.count(), 0)


class CrossTenantAndQRTokenSecurityTests(TestCase):
    """
    Automated security tests verifying:
    1. Strict tenant isolation across request viewing, approval, and audit export.
    2. QR verification token security (valid, invalid, tampered, revoked).
    """

    def setUp(self):
        import uuid
        from forms_engine.audit_service import AuditExportService

        self.AuditExportService = AuditExportService

        # Global Roles
        self.role_emp, _ = Role.objects.get_or_create(code="EMPLOYEE", defaults={"name": "Employee"})
        self.role_mgr, _ = Role.objects.get_or_create(code="MANAGER", defaults={"name": "Manager"})
        self.role_admin, _ = Role.objects.get_or_create(code="ORG_ADMIN", defaults={"name": "Organization Administrator"})

        # Org A
        self.org_a = Organization.objects.create(name="Alpha Corp", code="ALPHA", email="admin@alpha.test")
        self.dept_a = Department.objects.create(organization=self.org_a, name="Engineering", code="ENG")
        self.loc_a = Location.objects.create(organization=self.org_a, name="HQ Alpha", code="HQ_A", address="100 St", city="Bangalore", state="KA")
        self.desig_a = Designation.objects.create(organization=self.org_a, name="Software Engineer", code="SWE")

        self.user_a1 = User.objects.create_user(username="alpha_emp", email="emp@alpha.test", password="password123")
        self.emp_a1 = Employee.objects.create(user=self.user_a1, organization=self.org_a, department=self.dept_a, location=self.loc_a, designation=self.desig_a, role=self.role_emp, employee_code="A_EMP_01", joining_date="2024-01-01")

        self.user_a_mgr = User.objects.create_user(username="alpha_mgr", email="mgr@alpha.test", password="password123")
        self.emp_a_mgr = Employee.objects.create(user=self.user_a_mgr, organization=self.org_a, department=self.dept_a, location=self.loc_a, designation=self.desig_a, role=self.role_mgr, employee_code="A_MGR_01", joining_date="2024-01-01")

        self.user_a_admin = User.objects.create_user(username="alpha_admin", email="admin@alpha.test", password="password123")
        self.emp_a_admin = Employee.objects.create(user=self.user_a_admin, organization=self.org_a, department=self.dept_a, location=self.loc_a, designation=self.desig_a, role=self.role_admin, employee_code="A_ADM_01", joining_date="2024-01-01")

        # Org B
        self.org_b = Organization.objects.create(name="Beta Industries", code="BETA", email="admin@beta.test")
        self.dept_b = Department.objects.create(organization=self.org_b, name="Operations", code="OPS")
        self.loc_b = Location.objects.create(organization=self.org_b, name="HQ Beta", code="HQ_B", address="200 St", city="Mumbai", state="MH")
        self.desig_b = Designation.objects.create(organization=self.org_b, name="Analyst", code="ANL")

        self.user_b_emp = User.objects.create_user(username="beta_emp", email="emp@beta.test", password="password123")
        self.emp_b_emp = Employee.objects.create(user=self.user_b_emp, organization=self.org_b, department=self.dept_b, location=self.loc_b, designation=self.desig_b, role=self.role_emp, employee_code="B_EMP_01", joining_date="2024-01-01")

        self.user_b_admin = User.objects.create_user(username="beta_admin", email="admin@beta.test", password="password123")
        self.emp_b_admin = Employee.objects.create(user=self.user_b_admin, organization=self.org_b, department=self.dept_b, location=self.loc_b, designation=self.desig_b, role=self.role_admin, employee_code="B_ADM_01", joining_date="2024-01-01")

        # Workflow & Form in Org A
        self.wf_def_a = WorkflowDefinition.objects.create(organization=self.org_a, name="Hardware Approval", code="HW_ALPHA")
        self.wf_ver_a = WorkflowVersion.objects.create(workflow=self.wf_def_a, version=1, is_published=True, is_latest=True)
        self.step_def_a = WorkflowStepDefinition.objects.create(
            workflow_version=self.wf_ver_a,
            step_order=1,
            name="Manager Review",
            step_type="APPROVAL",
            approver_type="ROLE",
            role_code="MANAGER",
        )

        self.form_a = FormDefinition.objects.create(organization=self.org_a, name="Laptop Request", code="laptop-alpha", workflow=self.wf_ver_a, is_published=True)
        self.field_a = FormField.objects.create(form=self.form_a, label="Item", field_name="item_name", field_type="text", is_required=True, order=1)

        # Submission in Org A
        self.wf_inst_a = WorkflowInstance.objects.create(
            workflow_version=self.wf_ver_a,
            organization=self.org_a,
            initiated_by=self.user_a1,
            status="APPROVED",
        )
        self.token_a = uuid.uuid4()
        self.sub_a = FormSubmission.objects.create(
            form=self.form_a,
            organization=self.org_a,
            submitted_by=self.user_a1,
            workflow_instance=self.wf_inst_a,
            status="APPROVED",
            permission_id="PRM-ALPHA-001",
            verification_token=self.token_a,
            is_revoked=False,
        )
        FormSubmissionValue.objects.create(submission=self.sub_a, field=self.field_a, value="MacBook Pro M3")

    def test_cross_tenant_request_detail_blocked(self):
        """Users from Org B cannot view request details of Org A (returns 404)."""
        self.client.force_login(self.user_b_emp)
        url = reverse("request-detail", args=[self.sub_a.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_cross_tenant_audit_export_isolation(self):
        """Org Admin from Org B exporting audit CSV cannot see any submissions from Org A."""
        csv_content_b = self.AuditExportService.generate_organization_audit_csv(self.org_b)
        self.assertNotIn("PRM-ALPHA-001", csv_content_b)
        self.assertNotIn("emp@alpha.test", csv_content_b)
        self.assertNotIn("MacBook Pro M3", csv_content_b)

        # Org A export should contain its own submission
        csv_content_a = self.AuditExportService.generate_organization_audit_csv(self.org_a)
        self.assertIn("PRM-ALPHA-001", csv_content_a)
        self.assertIn("emp@alpha.test", csv_content_a)

    def test_valid_qr_token_public_verification(self):
        """A valid QR verification token returns 200 with public approval status."""
        url = reverse("verify-permission", args=[str(self.token_a)])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["verification_status"], "VALID")
        self.assertEqual(response.context["submission"].permission_id, "PRM-ALPHA-001")

    def test_tampered_or_invalid_qr_token(self):
        """An invalid or non-existent token returns INVALID status without crashing."""
        import uuid
        tampered_token = uuid.uuid4()
        url = reverse("verify-permission", args=[str(tampered_token)])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["verification_status"], "INVALID")
        self.assertIsNone(response.context["submission"])

    def test_revoked_qr_token_shows_revoked_status(self):
        """When a permission is revoked, the public verification page shows REVOKED."""
        self.sub_a.is_revoked = True
        self.sub_a.save()

        url = reverse("verify-permission", args=[str(self.token_a)])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["verification_status"], "REVOKED")


