from django.db import models
from organizations.models import Organization


class FormDefinition(models.Model):

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="forms"
    )

    name = models.CharField(max_length=200)

    code = models.CharField(max_length=50)

    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (
            "organization",
            "code",
        )

    def __str__(self):
        return self.name
    
class FormVersion(models.Model):

    form = models.ForeignKey(
        FormDefinition,
        on_delete=models.CASCADE,
        related_name="versions"
    )

    version = models.PositiveIntegerField()

    is_published = models.BooleanField(default=False)

    is_latest = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            "form",
            "version",
        )

    def __str__(self):
        return f"{self.form.name} v{self.version}"
    
class FormFieldDefinition(models.Model):

    FIELD_TYPES = [
        ("TEXT", "Text"),
        ("TEXTAREA", "Textarea"),
        ("NUMBER", "Number"),
        ("EMAIL", "Email"),
        ("PHONE", "Phone"),
        ("DATE", "Date"),
        ("DATETIME", "DateTime"),
        ("BOOLEAN", "Boolean"),
        ("SELECT", "Select"),
        ("MULTISELECT", "Multi Select"),
        ("RADIO", "Radio"),
        ("CHECKBOX", "Checkbox"),
        ("FILE", "File"),
        ("IMAGE", "Image"),
    ]

    form_version = models.ForeignKey(
        FormVersion,
        on_delete=models.CASCADE,
        related_name="fields"
    )

    label = models.CharField(max_length=150)

    field_name = models.CharField(max_length=100)

    field_type = models.CharField(
        max_length=20,
        choices=FIELD_TYPES
    )

    placeholder = models.CharField(
        max_length=255,
        blank=True
    )

    help_text = models.TextField(
        blank=True
    )

    is_required = models.BooleanField(
        default=False
    )

    field_order = models.PositiveIntegerField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = [
            "field_order"
        ]

    def __str__(self):
        return self.label
