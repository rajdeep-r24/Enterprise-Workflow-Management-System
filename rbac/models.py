from django.db import models


class Role(models.Model):
    ROLE_DISPLAY_MAP = {
        "SUPER_ADMIN": "Super Administrator",
        "ORG_ADMIN": "Organization Administrator",
        "ADMIN": "Administrator",
        "HR_HEAD": "HR Head",
        "IT_HEAD": "IT Head",
        "MANAGER": "Manager",
        "UNIT_HEAD": "Unit Head",
        "EMPLOYEE": "Employee",
    }

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    @property
    def display_name(self):
        return self.ROLE_DISPLAY_MAP.get(self.code, self.name or self.code)

    @classmethod
    def get_display_name(cls, code):
        if not code:
            return ""
        return cls.ROLE_DISPLAY_MAP.get(code, str(code).replace("_", " ").title())

    def __str__(self):
        return self.display_name


class Permission(models.Model):

    module = models.CharField(max_length=100)

    name = models.CharField(max_length=100)

    code = models.CharField(
        max_length=100,
        unique=True,
    )

    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["module", "name"]

    def __str__(self):
        return f"{self.module} | {self.name}"


class RolePermission(models.Model):
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE
    )

    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"],
                name="unique_role_permission",
            )
        ]

    def __str__(self):
        return f"{self.role.name} → {self.permission.code}"
