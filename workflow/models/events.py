from django.db import models
from accounts.models import User
from .instances import WorkflowInstance


class WorkflowEvent(models.Model):

    EVENT_TYPES = [
        ("SUBMITTED", "Submitted"),
        ("ASSIGNED", "Assigned"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("COMPLETED", "Completed"),
        ("COMMENT", "Comment"),
    ]

    workflow_instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name="events",
    )

    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPES,
    )

    performed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.workflow_instance} - {self.event_type}"
