from django.db import models
from organizations.models import Organization

from organizations.managers import TenantManager

class Location(models.Model):
    objects = TenantManager()

    LOCATION_TYPES = [
        ("HQ", "Headquarters"),
        ("BRANCH", "Branch"),
        ("FACTORY", "Factory"),
        ("WAREHOUSE", "Warehouse"),
        ("REMOTE", "Remote Office"),
        ("DATACENTER", "Data Center"),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="locations"
    )

    name = models.CharField(max_length=150)

    code = models.CharField(max_length=20)

    location_type = models.CharField(
        max_length=100
    )

    address = models.TextField()

    city = models.CharField(max_length=100)

    state = models.CharField(max_length=100)

    country = models.CharField(max_length=100, default="India")

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["name"]

    def __str__(self):
        return self.name
        
    def get_location_type_display(self):
        types_dict = dict(self.LOCATION_TYPES)
        return types_dict.get(self.location_type, self.location_type)
