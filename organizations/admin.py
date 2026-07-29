from django.contrib import admin
from .models import Organization

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "code",
        "email",
        "country",
        "is_active",
    )

    search_fields = (
        "name",
        "code",
        "email",
    )

    list_filter = (
        "country",
        "is_active",
    )
