from django.contrib import admin
from .models import Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "organization",
        "code",
        "is_active",
    )

    search_fields = (
        "name",
        "code",
    )

    list_filter = (
        "organization",
        "is_active",
    )
