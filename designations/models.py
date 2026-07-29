from django.db import models
from organizations.models import Organization


class Designation(models.Model):

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="designations"
    )

    name = models.CharField(max_length=100)

    code = models.CharField(max_length=20)

    description = models.TextField(blank=True)

    level = models.PositiveIntegerField(default=1)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["level", "name"]

    def __str__(self):
        return self.name
