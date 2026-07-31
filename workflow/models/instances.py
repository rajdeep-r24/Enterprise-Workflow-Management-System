from django.db import models
from accounts.models import User
from organizations.models import Organization
from .workflow import WorkflowVersion, WorkflowStepDefinition


from organizations.managers import TenantManager

class WorkflowInstance(models.Model):
    objects = TenantManager()
    
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
    )

    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("IN_PROGRESS", "In Progress"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    ]

    workflow_version = models.ForeignKey(
        WorkflowVersion,
        on_delete=models.PROTECT
    )

    initiated_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT
    )

    current_step = models.ForeignKey(
        WorkflowStepDefinition,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="DRAFT"
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Workflow #{self.pk}"
    
class WorkflowStepInstance(models.Model):

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("SKIPPED", "Skipped"),
    ]

    workflow_instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name="steps"
    )

    step_definition = models.ForeignKey(
        WorkflowStepDefinition,
        on_delete=models.PROTECT
    )

    assigned_to = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    remarks = models.TextField(blank=True)

    action_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.workflow_instance} - {self.step_definition.name}"
