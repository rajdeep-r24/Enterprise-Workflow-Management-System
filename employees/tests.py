from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from departments.models import Department
from designations.models import Designation
from employees.models import Employee
from locations.models import Location
from organizations.models import Organization
from rbac.models import Role


class EmployeeProfileViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="employee@example.com",
            email="employee@example.com",
            password="testpass123",
            first_name="Jane",
            last_name="Doe",
        )
        organization = Organization.objects.create(
            name="Demo Org",
            code="DO1",
            email="demo@example.com",
            country="India",
        )
        department = Department.objects.create(
            organization=organization,
            name="Engineering",
            code="ENG",
        )
        location = Location.objects.create(
            organization=organization,
            name="Main Office",
            code="LOC1",
            location_type="HQ",
            address="123 Street",
            city="Bengaluru",
            state="Karnataka",
            country="India",
        )
        designation = Designation.objects.create(
            organization=organization,
            name="Engineer",
            code="ENGR",
        )
        role = Role.objects.create(name="Employee", code="EMPLOYEE")
        Employee.objects.create(
            user=self.user,
            organization=organization,
            department=department,
            location=location,
            designation=designation,
            role=role,
            employee_code="EMP001",
            joining_date="2024-01-01",
        )

    def test_profile_requires_login(self):
        response = self.client.get(reverse("employee-profile"))
        self.assertEqual(response.status_code, 302)

    def test_profile_renders_for_authenticated_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("employee-profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Employee Profile")
