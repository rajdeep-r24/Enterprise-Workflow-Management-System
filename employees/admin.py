from django.contrib import admin
from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):

    list_display = (
        "employee_code",
        "user",
        "organization",
        "department",
        "designation",
        "role",
        "is_active",
    )

    search_fields = (
        "employee_code",
        "user__email",
        "user__first_name",
        "user__last_name",
    )

    list_filter = (
        "organization",
        "department",
        "designation",
        "role",
        "is_active",
    )
