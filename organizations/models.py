from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=20, unique=True)

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)

    website = models.URLField(blank=True)

    address = models.TextField(blank=True)

    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default="India")

    logo = models.ImageField(
        upload_to="organization_logos/",
        blank=True,
        null=True
    )

    official_stamp = models.ImageField(
        upload_to="organization_stamps/",
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"

    def __str__(self):
        return self.name
