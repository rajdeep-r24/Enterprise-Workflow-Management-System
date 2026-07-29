from django.contrib import admin
from .models import Designation


@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "organization",
        "level",
        "is_active",
    )

    list_filter = (
        "organization",
        "is_active",
    )

    search_fields = (
        "name",
        "code",
    )
