from django.db import models
from accounts.models import User
from organizations.models import Organization
from departments.models import Department
from locations.models import Location
from designations.models import Designation
from rbac.models import Role


from organizations.managers import TenantManager

class Employee(models.Model):

    objects = TenantManager()

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="employee_profile"
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT
    )

    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT
    )

    designation = models.ForeignKey(
        Designation,
        on_delete=models.PROTECT
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT
    )

    employee_code = models.CharField(
        max_length=20,
    )

    manager = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    joining_date = models.DateField()

    is_active = models.BooleanField(default=True)

    digital_signature = models.ImageField(
        upload_to="signatures/",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "employee_code"],
                name="unique_employee_code_per_org"
            )
        ]

    def __str__(self):
        return f"{self.employee_code} - {self.user.get_full_name()}"


class EmployeeHistory(models.Model):

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="history",
    )

    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="employee_changes",
    )

    old_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    new_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    old_designation = models.ForeignKey(
        Designation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    new_designation = models.ForeignKey(
        Designation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    old_manager = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    new_manager = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    reason = models.TextField(blank=True)

    effective_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.employee.employee_code} - {self.created_at.date()}"

class EmployeeInvitation(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("REVOKED", "Revoked"),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="invitations",
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="employee_invitations",
    )

    email = models.EmailField()

    token_hash = models.CharField(max_length=128)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    expires_at = models.DateTimeField()

    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_invitations",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["token_hash"]),
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return f"Invitation for {self.email} ({self.status})"

