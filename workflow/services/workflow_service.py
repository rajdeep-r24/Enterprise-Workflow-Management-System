import uuid

from django.db import transaction
from django.utils import timezone

from employees.models import Employee
from forms_engine.models import FormSubmission
from notifications.services import NotificationService

from ..models.events import WorkflowEvent
from ..models.instances import WorkflowStepInstance
from .approver_resolver import ApproverResolver


class WorkflowActionError(Exception):
    """Raised when a workflow action is attempted on an invalid step or workflow state."""


class WorkflowService:

    @staticmethod
    @transaction.atomic
    def approve(step_instance, user, remarks=""):

        workflow = step_instance.workflow_instance

        if step_instance.status != "PENDING":
            raise WorkflowActionError("Only pending steps can be approved")

        if step_instance.assigned_to_id != user.pk:
            raise WorkflowActionError("Only the assigned approver can approve this step")

        if workflow.status != "IN_PROGRESS":
            raise WorkflowActionError("Workflow is not in progress")

        if workflow.current_step_id != step_instance.step_definition_id:
            raise WorkflowActionError("Only the current step can be acted on")

        # ------------------------------------------
        # APPROVE CURRENT STEP
        # ------------------------------------------

        step_instance.status = "APPROVED"
        step_instance.remarks = remarks
        step_instance.action_at = timezone.now()

        step_instance.save(
            update_fields=[
                "status",
                "remarks",
                "action_at",
            ]
        )

        WorkflowEvent.objects.create(
            workflow_instance=workflow,
            event_type="APPROVED",
            performed_by=user,
            remarks=remarks or "Request approved",
        )

        NotificationService.notify(
            recipient=workflow.initiated_by,
            notification_type="APPROVED",
            title="Step approved",
            message=remarks or "A workflow step has been approved.",
            workflow_instance=workflow,
        )

        # ------------------------------------------
        # FIND NEXT STEP
        # ------------------------------------------

        next_step = step_instance.step_definition.next_step

        # ==========================================
        # NEXT APPROVAL STEP EXISTS
        # ==========================================

        if next_step:

            submission = FormSubmission.objects.get(
                workflow_instance=workflow
            )

            employee = Employee.objects.get(
                user=submission.submitted_by
            )

            next_approver = ApproverResolver.resolve(
                employee,
                next_step,
            )

            # Do not continue if approver is missing
            if next_approver is None:

                raise WorkflowActionError(
                    f"No approver found for role: "
                    f"{next_step.role_code}"
                )

            # Create ONLY the next approval
            WorkflowStepInstance.objects.create(
                workflow_instance=workflow,
                step_definition=next_step,
                assigned_to=next_approver,
                status="PENDING",
            )

            WorkflowEvent.objects.create(
                workflow_instance=workflow,
                event_type="ASSIGNED",
                performed_by=next_approver,
                remarks=f"Assigned to {next_step.name}",
            )

            NotificationService.notify(
                recipient=next_approver,
                notification_type="ASSIGNED",
                title="New workflow assignment",
                message=f"You have a new workflow assignment for {next_step.name}.",
                workflow_instance=workflow,
            )

            # Move workflow forward
            workflow.current_step = next_step
            workflow.status = "IN_PROGRESS"

            workflow.save(
                update_fields=[
                    "current_step",
                    "status",
                ]
            )

        # ==========================================
        # FINAL APPROVAL - WORKFLOW COMPLETED
        # ==========================================

        else:

            workflow.current_step = None
            workflow.status = "APPROVED"
            workflow.completed_at = timezone.now()

            workflow.save(
                update_fields=[
                    "current_step",
                    "status",
                    "completed_at",
                ]
            )

            # Get related submission
            submission = FormSubmission.objects.get(
                workflow_instance=workflow
            )

            submission.status = "APPROVED"

            # --------------------------------------
            # GENERATE VERIFICATION CREDENTIALS
            # --------------------------------------

            # Human-readable permission ID
            if not submission.permission_id:

                submission.permission_id = (
                    f"LP-"
                    f"{timezone.now().year}-"
                    f"{submission.pk:06d}"
                )

            # Secure unpredictable verification token
            if not submission.verification_token:

                submission.verification_token = uuid.uuid4()

            # Record when permission was officially issued
            if not submission.issued_at:

                submission.issued_at = timezone.now()

            submission.save(
                update_fields=[
                    "status",
                    "permission_id",
                    "verification_token",
                    "issued_at",
                ]
            )

            # Record completion only after final approval
            WorkflowEvent.objects.create(
                workflow_instance=workflow,
                event_type="COMPLETED",
                performed_by=user,
                remarks="Workflow completed successfully",
            )

            NotificationService.notify(
                recipient=workflow.initiated_by,
                notification_type="COMPLETED",
                title="Request completed",
                message="Your request has been fully approved and completed.",
                workflow_instance=workflow,
            )

        return workflow


    @staticmethod
    @transaction.atomic
    def reject(step_instance, user, remarks=""):

        workflow = step_instance.workflow_instance

        if step_instance.status != "PENDING":
            raise WorkflowActionError("Only pending steps can be rejected")

        if step_instance.assigned_to_id != user.pk:
            raise WorkflowActionError("Only the assigned approver can reject this step")

        if workflow.status != "IN_PROGRESS":
            raise WorkflowActionError("Workflow is not in progress")

        if workflow.current_step_id != step_instance.step_definition_id:
            raise WorkflowActionError("Only the current step can be acted on")

        # ------------------------------------------
        # REJECT CURRENT STEP
        # ------------------------------------------

        step_instance.status = "REJECTED"
        step_instance.remarks = remarks
        step_instance.action_at = timezone.now()

        step_instance.save(
            update_fields=[
                "status",
                "remarks",
                "action_at",
            ]
        )

        WorkflowEvent.objects.create(
            workflow_instance=workflow,
            event_type="REJECTED",
            performed_by=user,
            remarks=remarks or "Request rejected",
        )

        NotificationService.notify(
            recipient=workflow.initiated_by,
            notification_type="REJECTED",
            title="Request rejected",
            message=remarks or "Your request was rejected.",
            workflow_instance=workflow,
        )

        # ------------------------------------------
        # STOP WORKFLOW
        # ------------------------------------------

        workflow.current_step = None
        workflow.status = "REJECTED"
        workflow.completed_at = timezone.now()

        workflow.save(
            update_fields=[
                "current_step",
                "status",
                "completed_at",
            ]
        )

        # ------------------------------------------
        # UPDATE FORM SUBMISSION
        # ------------------------------------------

        submission = FormSubmission.objects.get(
            workflow_instance=workflow
        )

        submission.status = "REJECTED"

        submission.save(
            update_fields=[
                "status",
            ]
        )

        return workflow
