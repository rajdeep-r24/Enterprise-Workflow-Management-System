from django.db import transaction

from .models import Notification
from .email_service import WorkflowEmailService


class NotificationService:
    @staticmethod
    @transaction.atomic
    def notify(
        recipient,
        notification_type,
        title,
        message="",
        workflow_instance=None,
        send_email=True,
    ):
        if not recipient:
            return None

        existing = Notification.objects.filter(
            recipient=recipient,
            notification_type=notification_type,
            workflow_instance=workflow_instance,
            title=title,
            message=message,
        ).first()

        if existing:
            notification = existing
        else:
            notification = Notification.objects.create(
                recipient=recipient,
                notification_type=notification_type,
                title=title,
                message=message,
                workflow_instance=workflow_instance,
            )

        if send_email:
            WorkflowEmailService.send_workflow_email(
                recipient=recipient,
                notification_type=notification_type,
                title=title,
                message=message,
                workflow_instance=workflow_instance,
            )

        return notification

    @staticmethod
    def unread_count(user):
        return Notification.objects.filter(recipient=user, is_read=False).count()
