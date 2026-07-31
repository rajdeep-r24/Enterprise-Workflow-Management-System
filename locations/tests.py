from django.test import TestCase
from django.urls import reverse
from organizations.models import Organization
from accounts.models import User
from employees.models import Employee
from rbac.models import Role
from locations.models import Location

class LocationTests(TestCase):
    def setUp(self):
        self.org1 = Organization.objects.create(name="Org 1", code="O1", email="o1@example.com")
        self.org2 = Organization.objects.create(name="Org 2", code="O2", email="o2@example.com")
        
        self.user1 = User.objects.create_user(username="u1@example.com", email="u1@example.com", password="pwd")
        self.user2 = User.objects.create_user(username="u2@example.com", email="u2@example.com", password="pwd")
        
        role = Role.objects.create(name="Admin", code="ADMIN")
        
        from departments.models import Department
        from designations.models import Designation
        
        self.dept1 = Department.objects.create(organization=self.org1, name="HR", code="HR")
        self.dept2 = Department.objects.create(organization=self.org2, name="IT", code="IT")
        
        self.desg1 = Designation.objects.create(organization=self.org1, name="D1", code="D1")
        self.desg2 = Designation.objects.create(organization=self.org2, name="D2", code="D2")
        
        self.loc1 = Location.objects.create(organization=self.org1, name="HQ1", code="HQ1", location_type="HQ", address="123", city="C1", state="S1")
        self.loc2 = Location.objects.create(organization=self.org2, name="HQ2", code="HQ2", location_type="HQ", address="123", city="C2", state="S2")

        self.emp1 = Employee.objects.create(user=self.user1, organization=self.org1, department=self.dept1, location=self.loc1, designation=self.desg1, employee_code="E1", role=role, joining_date="2024-01-01")
        self.emp2 = Employee.objects.create(user=self.user2, organization=self.org2, department=self.dept2, location=self.loc2, designation=self.desg2, employee_code="E2", role=role, joining_date="2024-01-01")

    def test_location_list_tenant_isolation(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse("location-list"))
        self.assertContains(response, "HQ1")
        self.assertNotContains(response, "HQ2")

    def test_location_create(self):
        self.client.force_login(self.user1)
        response = self.client.post(reverse("location-create"), {
            "name": "Branch 1",
            "code": "BR1",
            "location_type": "BRANCH",
            "address": "456",
            "city": "C1",
            "state": "S1",
            "country": "India",
            "is_active": True
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Location.objects.filter(organization=self.org1, code="BR1").exists())
        self.assertFalse(Location.objects.filter(organization=self.org2, code="BR1").exists())

    def test_location_update_tenant_isolation(self):
        self.client.force_login(self.user1)
        # Try to edit loc2 which belongs to org2
        response = self.client.get(reverse("location-update", args=[self.loc2.pk]))
        self.assertEqual(response.status_code, 404)
