from django.contrib import admin

from workflow.models import (
    WorkflowDefinition,
    WorkflowVersion,
    WorkflowStepDefinition,
)
from workflow.models.instances import (
    WorkflowInstance,
    WorkflowStepInstance,
)


class WorkflowStepInline(admin.TabularInline):
    model = WorkflowStepDefinition
    extra = 1


@admin.register(WorkflowDefinition)
class WorkflowDefinitionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "organization",
        "is_active",
    )

    search_fields = (
        "name",
        "code",
    )


@admin.register(WorkflowVersion)
class WorkflowVersionAdmin(admin.ModelAdmin):
    list_display = (
        "workflow",
        "version",
        "is_published",
        "is_latest",
    )

    list_filter = (
        "is_published",
        "is_latest",
    )

    inlines = [WorkflowStepInline]


@admin.register(WorkflowStepDefinition)
class WorkflowStepDefinitionAdmin(admin.ModelAdmin):
    list_display = (
        "workflow_version",
        "name",
        "step_order",
        "step_type",
        "approver_type",
        "role_code",
        "specific_approver",
    )

    list_filter = (
        "step_type",
        "approver_type",
    )


@admin.register(WorkflowInstance)
class WorkflowInstanceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "workflow_version",
        "initiated_by",
        "status",
        "created_at",
    )


@admin.register(WorkflowStepInstance)
class WorkflowStepInstanceAdmin(admin.ModelAdmin):
    list_display = (
        "workflow_instance",
        "step_definition",
        "assigned_to",
        "status",
    )
