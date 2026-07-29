from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    USER_TYPES = [
        ("EMPLOYEE", "Employee"),
    ]

    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPES,
        default="EMPLOYEE",
    )

    email = models.EmailField(
        unique=True
    )

    phone = models.CharField(
        max_length=15,
        blank=True
    )

    profile_picture = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True
    )

    date_of_birth = models.DateField(
        blank=True,
        null=True
    )

    is_email_verified = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email
