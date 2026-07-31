import uuid
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from organizations.models import Organization
from employees.models import Employee
from departments.models import Department
from locations.models import Location
from designations.models import Designation
from rbac.models import Role

User = get_user_model()

def create_organization_and_admin(validated_data: dict) -> Organization:
    """
    Creates a new Organization, User, and Employee (as ORG_ADMIN) atomically.
    Expected keys in validated_data:
      - organization_name
      - first_name
      - last_name
      - email
      - password
    """
    with transaction.atomic():
        org_name = validated_data["organization_name"]
        org_email = validated_data["email"]
        
        # Generate a unique code for the organization
        base_code = org_name.upper().replace(" ", "")[:10]
        unique_suffix = str(uuid.uuid4().hex)[:6].upper()
        org_code = f"{base_code}_{unique_suffix}"

        org = Organization.objects.create(
            name=org_name,
            code=org_code,
            email=org_email
        )

        # Using create_user to properly hash the password
        user = User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"]
        )

        # Get existing global role
        role = Role.objects.get(code="ORG_ADMIN")

        # Create necessary default dependencies for Employee
        default_department = Department.objects.create(
            organization=org,
            name="Administration",
            code="ADMIN"
        )

        default_location = Location.objects.create(
            organization=org,
            name="Headquarters",
            code="HQ",
            location_type="HQ",
            address="Not specified",
            city="Not specified",
            state="Not specified"
        )

        default_designation = Designation.objects.create(
            organization=org,
            name="System Administrator",
            code="SYSADMIN"
        )

        # Create Employee Profile
        Employee.objects.create(
            user=user,
            organization=org,
            department=default_department,
            location=default_location,
            designation=default_designation,
            role=role,
            employee_code="ADMIN001",
            joining_date=timezone.now().date()
        )

        return org
