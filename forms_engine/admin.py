from django.contrib import admin

from .models import (
    FormDefinition,
    FormField,
    FormSubmission,
    FormSubmissionValue,
)


class FormFieldInline(admin.TabularInline):
    model = FormField
    extra = 1


@admin.register(FormDefinition)
class FormDefinitionAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "organization",
        "version",
        "is_published",
    )

    list_filter = (
        "organization",
        "is_published",
    )

    search_fields = (
        "name",
        "code",
    )

    inlines = [
        FormFieldInline,
    ]


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "permission_id",
        "form",
        "submitted_by",
        "status",
        "issued_at",
        "is_revoked",
        "created_at",
    )

    list_filter = (
        "status",
        "is_revoked",
        "form",
    )

    search_fields = (
        "permission_id",
        "submitted_by__email",
        "submitted_by__first_name",
        "submitted_by__last_name",
    )

    fields = (
        "form",
        "submitted_by",
        "status",
        "workflow_instance",

        "permission_id",
        "verification_token",
        "issued_at",

        "is_revoked",
        "revoked_at",
        "revoked_by",
        "revocation_reason",

        "created_at",
        "updated_at",
    )

    readonly_fields = (
        "permission_id",
        "verification_token",
        "issued_at",
        "revoked_at",
        "revoked_by",
        "created_at",
        "updated_at",
    )


@admin.register(FormSubmissionValue)
class FormSubmissionValueAdmin(admin.ModelAdmin):

    list_display = (
        "submission",
        "field",
        "value",
    )

    search_fields = (
        "submission__permission_id",
        "field__label",
    )
