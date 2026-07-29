from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from organizations.models import Organization


class WorkflowDefinition(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="workflow_definitions"
    )

    name = models.CharField(max_length=200)

    code = models.CharField(max_length=50)

    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["name"]

    def __str__(self):
        return self.name


class WorkflowVersion(models.Model):

    workflow = models.ForeignKey(
        WorkflowDefinition,
        on_delete=models.CASCADE,
        related_name="versions"
    )

    version = models.PositiveIntegerField()

    is_published = models.BooleanField(default=False)

    is_latest = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            "workflow",
            "version",
        )

        ordering = [
            "-version",
        ]

    def __str__(self):
        return f"{self.workflow.name} v{self.version}"
    
class WorkflowStepDefinition(models.Model):

    STEP_TYPES = [
        ("APPROVAL", "Approval"),
        ("CONDITION", "Condition"),
        ("EMAIL", "Email"),
        ("WEBHOOK", "Webhook"),
        ("AI", "AI"),
        ("END", "End"),
    ]

    APPROVER_TYPES = [
        ("MANAGER", "Manager"),
        ("ROLE", "Role"),
        ("SPECIFIC_USER", "Specific User"),
    ]

    workflow_version = models.ForeignKey(
        WorkflowVersion,
        on_delete=models.CASCADE,
        related_name="steps"
    )

    name = models.CharField(max_length=150)

    step_order = models.PositiveIntegerField()

    step_type = models.CharField(
        max_length=20,
        choices=STEP_TYPES
    )

    approver_type = models.CharField(
        max_length=20,
        choices=APPROVER_TYPES,
        default="ROLE",
    )

    role_code = models.CharField(
        max_length=50,
        blank=True
    )

    specific_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    is_required = models.BooleanField(default=True)

    next_step = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["step_order"]

    def clean(self):
        super().clean()
        if self.approver_type == "ROLE":
            if not self.role_code.strip():
                raise ValidationError({"role_code": "Role-based steps must define a role_code."})
            if self.specific_approver_id:
                raise ValidationError({"specific_approver": "Role-based steps must not use a specific approver."})
        elif self.approver_type == "SPECIFIC_USER":
            if not self.specific_approver_id:
                raise ValidationError({"specific_approver": "Specific-user steps must define a specific approver."})
            if self.role_code.strip():
                raise ValidationError({"role_code": "Specific-user steps must not use a role_code."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.workflow_version} - Step {self.step_order}"
