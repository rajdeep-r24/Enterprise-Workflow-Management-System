from django.db import transaction

from .models import Notification


class NotificationService:
    @staticmethod
    @transaction.atomic
    def notify(
        recipient,
        notification_type,
        title,
        message="",
        workflow_instance=None,
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
            return existing

        notification = Notification.objects.create(
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
