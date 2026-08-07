from django.db import models
from organizations.models import Organization

from organizations.managers import TenantManager

class Department(models.Model):
    objects = TenantManager()
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="departments"
    )

    name = models.CharField(max_length=100)

    code = models.CharField(max_length=20)

    description = models.TextField(blank=True)

    email = models.EmailField(null=True, blank=True)

    phone = models.CharField(max_length=20, blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["name"]

    def __str__(self):
        return f"{self.organization.code} - {self.name}"
