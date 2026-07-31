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

class EmployeeCodeGenerationTests(TestCase):
    def setUp(self):
        from organizations.models import Organization
        from departments.models import Department
        from locations.models import Location
        from designations.models import Designation
        from rbac.models import Role
        
        self.org1 = Organization.objects.create(name="Org 1", code="O1", email="o1@example.com", country="India")
        self.org2 = Organization.objects.create(name="Org 2", code="O2", email="o2@example.com", country="India")
        
        self.dept1 = Department.objects.create(organization=self.org1, name="Dept 1", code="D1")
        self.loc1 = Location.objects.create(organization=self.org1, name="Loc 1", code="L1", location_type="HQ", address="123", city="BLR", state="KA", country="India")
        self.desg1 = Designation.objects.create(organization=self.org1, name="Desg 1", code="DS1")
        
        self.dept2 = Department.objects.create(organization=self.org2, name="Dept 2", code="D2")
        self.loc2 = Location.objects.create(organization=self.org2, name="Loc 2", code="L2", location_type="HQ", address="123", city="BLR", state="KA", country="India")
        self.desg2 = Designation.objects.create(organization=self.org2, name="Desg 2", code="DS2")
        
        self.role = Role.objects.create(name="Employee", code="EMPLOYEE")
        
    def _create_employee_via_form(self, org, email, first_name="John", last_name="Doe"):
        from employees.forms import EmployeeRegistrationForm
        
        dept = self.dept1 if org == self.org1 else self.dept2
        loc = self.loc1 if org == self.org1 else self.loc2
        desg = self.desg1 if org == self.org1 else self.desg2
        
        data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": "1234567890",
            "date_of_birth": "1990-01-01",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "organization": org.pk,
            "department": dept.pk,
            "location": loc.pk,
            "designation": desg.pk,
            "role": self.role.pk,
            "joining_date": "2024-01-01",
            "is_active": True,
        }
        form = EmployeeRegistrationForm(data, tenant=org)
        self.assertTrue(form.is_valid(), form.errors)
        return form.save()

    def test_auto_generation(self):
        # 1. First generated code = EMP0001
        emp1 = self._create_employee_via_form(self.org1, "john1@example.com")
        self.assertEqual(emp1.employee_code, "EMP0001")
        
        # 2. Next employee = EMP0002
        emp2 = self._create_employee_via_form(self.org1, "john2@example.com")
        self.assertEqual(emp2.employee_code, "EMP0002")
        
        # 3. Codes are independent between two organizations
        emp3 = self._create_employee_via_form(self.org2, "jane1@example.com")
        self.assertEqual(emp3.employee_code, "EMP0001")
