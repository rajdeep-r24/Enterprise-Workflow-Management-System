from django.db import transaction

from employees.models import Employee

from workflow.models.instances import (
    WorkflowInstance,
    WorkflowStepInstance,
)
from workflow.models.events import WorkflowEvent
from notifications.services import NotificationService
from workflow.services import ApproverResolver

from .models import (
    FormSubmission,
    FormSubmissionValue,
)


class FormEngineService:

    @staticmethod
    @transaction.atomic
    def submit(
        form_definition,
        submitted_by,
        cleaned_data,
    ):

        workflow_version = form_definition.workflow

        # Create workflow instance
        workflow_instance = WorkflowInstance.objects.create(
            workflow_version=workflow_version,
            initiated_by=submitted_by,
            status="SUBMITTED",
        )

        # Record submission event
        WorkflowEvent.objects.create(
            workflow_instance=workflow_instance,
            event_type="SUBMITTED",
            performed_by=submitted_by,
            remarks="Request submitted",
        )

        # Create form submission
        submission = FormSubmission.objects.create(
            form=form_definition,
            workflow_instance=workflow_instance,
            submitted_by=submitted_by,
            status="SUBMITTED",
        )

        # Save submitted form values
        for field in form_definition.fields.all():

            value = cleaned_data.get(
                field.field_name
            )

            if hasattr(value, "isoformat"):
                value = value.isoformat()

            FormSubmissionValue.objects.create(
                submission=submission,
                field=field,
                value=value,
            )

        # Get first workflow step
        first_step = (
            workflow_version.steps
            .order_by("step_order")
            .first()
        )

        if not first_step:
            raise ValueError(
                "This workflow does not have any approval steps."
            )

        # Set current workflow step
        workflow_instance.current_step = first_step
        workflow_instance.status = "IN_PROGRESS"

        workflow_instance.save(
            update_fields=[
                "current_step",
                "status",
            ]
        )

        # ==========================================
        # RESOLVE FIRST APPROVER
        # ==========================================

        employee = Employee.objects.get(
            user=submitted_by
        )

        approver = ApproverResolver.resolve(
            employee,
            first_step,
        )

        # Do not create an unassigned approval
        if approver is None:
            raise ValueError(
                f"No approver found for role: "
                f"{first_step.role_code}"
            )

        # Create first pending approval
        WorkflowStepInstance.objects.create(
            workflow_instance=workflow_instance,
            step_definition=first_step,
            assigned_to=approver,
            status="PENDING",
        )

        NotificationService.notify(
            recipient=submitted_by,
            notification_type="SUBMITTED",
            title="Request submitted",
            message="Your request has been submitted and is waiting for review.",
            workflow_instance=workflow_instance,
        )

        NotificationService.notify(
            recipient=approver,
            notification_type="ASSIGNED",
            title="New workflow assignment",
            message=f"You have a new workflow assignment for {first_step.name}.",
            workflow_instance=workflow_instance,
        )

        # Record assignment event
        WorkflowEvent.objects.create(
            workflow_instance=workflow_instance,
            event_type="ASSIGNED",
            performed_by=approver,
            remarks=f"Assigned to {first_step.name}",
        )

        return submission
