import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


class WorkflowEmailService:
    @staticmethod
    def send_workflow_email(
        recipient,
        notification_type,
        title,
        message="",
        workflow_instance=None,
    ):
        """
        Renders and dispatches a responsive HTML & plain-text workflow notification email.
        Executes safely with try/except so email delivery errors never block DB transactions.
        """
        if not recipient or not getattr(recipient, "email", None):
            return False

        try:
            site_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000").rstrip("/")
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@anukram.local")

            # Extract related submission & workflow metadata if available
            submission = None
            workflow_name = "Enterprise Workflow"
            organization_name = "Anukram"
            permission_id = None
            current_step_name = None
            requester_name = getattr(recipient, "get_full_name", lambda: "")() or recipient.username or recipient.email
            requester_dept = "General"

            if workflow_instance:
                try:
                    if hasattr(workflow_instance, "formsubmission"):
                        submission = workflow_instance.formsubmission
                    else:
                        from forms_engine.models import FormSubmission
                        submission = FormSubmission.objects.filter(workflow_instance=workflow_instance).first()
                except Exception:
                    submission = None

                # Extract workflow name
                if hasattr(workflow_instance, "workflow_version") and workflow_instance.workflow_version:
                    workflow_name = workflow_instance.workflow_version.workflow.name
                    if hasattr(workflow_instance.workflow_version.workflow, "organization") and workflow_instance.workflow_version.workflow.organization:
                        organization_name = workflow_instance.workflow_version.workflow.organization.name
                elif submission and hasattr(submission, "request_type") and submission.request_type:
                    workflow_name = submission.request_type.name

                # Extract requester info
                if workflow_instance.initiated_by:
                    init_user = workflow_instance.initiated_by
                    requester_name = init_user.get_full_name() or init_user.username or init_user.email
                    try:
                        from employees.models import Employee
                        emp = Employee.objects.filter(user=init_user).first()
                        if emp:
                            if emp.department:
                                requester_dept = emp.department.name
                            if emp.organization:
                                organization_name = emp.organization.name
                    except Exception:
                        pass

                # Extract current step & permission ID
                if workflow_instance.current_step:
                    current_step_name = workflow_instance.current_step.name

                if submission and submission.permission_id:
                    permission_id = submission.permission_id

            # Determine action URL
            if submission:
                request_url = f"{site_url}/requests/{submission.id}/"
            else:
                request_url = f"{site_url}/dashboard/"

            # Dynamic copy configuration based on notification type
            nt = (notification_type or "").upper()

            if nt == "ASSIGNED":
                badge_type = "warning"
                badge_text = "Action Required"
                email_subject = f"Action Required: Approval needed for {workflow_name} | Anukram"
                headline = f"New Approval Request: {workflow_name}"
                main_message = (
                    f"You have been assigned to review and approve {requester_name}'s request for {workflow_name}. "
                    "Please review the submitted information and record your decision."
                )
                cta_text = "Review & Take Action"
                cta_url = request_url

            elif nt == "APPROVED":
                badge_type = "success"
                badge_text = "Step Approved"
                email_subject = f"Step Approved: Your {workflow_name} request has progressed | Anukram"
                headline = f"Workflow Step Approved"
                main_message = (
                    f"Great news! A step in your {workflow_name} request has been approved and moved forward in the pipeline."
                )
                cta_text = "View Request Status"
                cta_url = request_url

            elif nt == "COMPLETED":
                badge_type = "success"
                badge_text = "Approved & Issued"
                email_subject = f"Approved & Completed: {workflow_name} | Anukram"
                headline = f"Request Completed & Permission Issued"
                main_message = (
                    f"Your request for {workflow_name} has been fully approved by all designated authorities. "
                    "Your official QR Permission Slip is now generated and ready for presentation."
                )
                if submission and submission.verification_token:
                    cta_url = f"{site_url}/verify/{submission.verification_token}/"
                    cta_text = "View QR Permission Slip"
                else:
                    cta_url = request_url
                    cta_text = "View Permission Slip"

            elif nt == "REJECTED":
                badge_type = "danger"
                badge_text = "Request Rejected"
                email_subject = f"Notice: Your {workflow_name} request was rejected | Anukram"
                headline = f"Request Not Approved"
                main_message = (
                    f"Your request for {workflow_name} was not approved. "
                    "Please review the approver remarks below for specific guidance or required corrections."
                )
                cta_text = "View Rejection Details"
                cta_url = request_url

            elif nt == "SUBMITTED":
                badge_type = "info"
                badge_text = "Request Submitted"
                email_subject = f"Submitted: {workflow_name} | Anukram"
                headline = f"Request Received & Processing"
                main_message = (
                    f"Your {workflow_name} request has been submitted successfully and routed to the first approver in the workflow pipeline."
                )
                cta_text = "Track Live Status"
                cta_url = request_url

            else:
                badge_type = "info"
                badge_text = "Workflow Update"
                email_subject = f"Workflow Notification: {title} | Anukram"
                headline = title
                main_message = message or "There is a new update on your workflow request."
                cta_text = "View in Anukram"
                cta_url = request_url

            context = {
                "email_subject": email_subject,
                "badge_type": badge_type,
                "badge_text": badge_text,
                "headline": headline,
                "main_message": main_message,
                "workflow_name": workflow_name,
                "requester_name": requester_name,
                "requester_dept": requester_dept,
                "organization_name": organization_name,
                "current_step_name": current_step_name,
                "permission_id": permission_id,
                "remarks": message if message != main_message else None,
                "timestamp": timezone.now(),
                "cta_text": cta_text,
                "cta_url": cta_url,
            }

            # Render HTML and Plain text templates
            html_body = render_to_string("emails/workflow_notification.html", context)
            text_body = render_to_string("emails/workflow_notification.txt", context)

            msg = EmailMultiAlternatives(
                subject=email_subject,
                body=text_body,
                from_email=from_email,
                to=[recipient.email],
            )
            msg.attach_alternative(html_body, "text/html")
            msg.send(fail_silently=False)

            logger.info("Workflow notification email sent to %s for type %s", recipient.email, notification_type)
            return True

        except Exception as exc:
            logger.warning("Failed to dispatch workflow email notification to %s: %s", getattr(recipient, "email", "unknown"), exc)
            return False
