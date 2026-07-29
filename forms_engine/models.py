import uuid
from django.db import models

from accounts.models import User
from organizations.models import Organization
from workflow.models import WorkflowInstance, WorkflowVersion


class FormDefinition(models.Model):

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
    )

    name = models.CharField(max_length=200)

    code = models.CharField(
        max_length=100,
        unique=True,
    )

    description = models.TextField(blank=True)

    workflow = models.ForeignKey(
        WorkflowVersion,
        on_delete=models.PROTECT,
    )

    version = models.PositiveIntegerField(default=1)

    is_published = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class FormField(models.Model):

    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    DATE = "date"
    TIME = "time"
    EMAIL = "email"
    SELECT = "select"
    CHECKBOX = "checkbox"
    FILE = "file"

    FIELD_TYPES = [
        (TEXT, "Text"),
        (TEXTAREA, "Textarea"),
        (NUMBER, "Number"),
        (DATE, "Date"),
        (TIME, "Time"),
        (EMAIL, "Email"),
        (SELECT, "Select"),
        (CHECKBOX, "Checkbox"),
        (FILE, "File"),
    ]

    form = models.ForeignKey(
        FormDefinition,
        on_delete=models.CASCADE,
        related_name="fields",
    )

    label = models.CharField(max_length=200)

    field_name = models.SlugField()

    field_type = models.CharField(
        max_length=20,
        choices=FIELD_TYPES,
    )

    is_required = models.BooleanField(default=False)

    order = models.PositiveIntegerField(default=1)

    placeholder = models.CharField(
        max_length=255,
        blank=True,
    )

    help_text = models.TextField(blank=True)

    options = models.JSONField(
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.form.name} - {self.label}"

    class Meta:
        ordering = ["order"]


class FormSubmission(models.Model):

    STATUS = [
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    form = models.ForeignKey(
        FormDefinition,
        on_delete=models.PROTECT,
    )

    workflow_instance = models.OneToOneField(
        WorkflowInstance,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    submitted_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="DRAFT",
    )

    permission_id = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
    )

    verification_token = models.UUIDField(
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )

    issued_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_revoked = models.BooleanField(
        default=False,
    )

    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    revoked_by = models.ForeignKey(
    User,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="revoked_permissions",
    )
    
    revocation_reason = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.form.name} - {self.submitted_by.email}"


class FormSubmissionValue(models.Model):

    submission = models.ForeignKey(
        FormSubmission,
        on_delete=models.CASCADE,
        related_name="values",
    )

    field = models.ForeignKey(
        FormField,
        on_delete=models.CASCADE,
    )

    value = models.JSONField()

    class Meta:
        unique_together = (
            "submission",
            "field",
        )

    def __str__(self):
        return self.field.label


class RequestAttachment(models.Model):
    submission = models.ForeignKey(
        FormSubmission,
        on_delete=models.CASCADE,
        related_name="attachments"
    )
    file = models.FileField(upload_to="request_attachments/")
    original_filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.original_filename
