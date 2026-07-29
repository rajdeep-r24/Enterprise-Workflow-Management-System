from django.contrib import admin
from .models import Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "organization",
        "location_type",
        "city",
        "is_active",
    )

    search_fields = (
        "name",
        "code",
        "city",
    )

    list_filter = (
        "organization",
        "location_type",
        "city",
    )
