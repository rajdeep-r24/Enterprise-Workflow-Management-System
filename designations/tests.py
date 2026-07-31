from django.test import TestCase
from django.urls import reverse
from organizations.models import Organization
from accounts.models import User
from employees.models import Employee
from rbac.models import Role
from designations.models import Designation

class DesignationTests(TestCase):
    def setUp(self):
        self.org1 = Organization.objects.create(name="Org 1", code="O1", email="o1@example.com")
        self.org2 = Organization.objects.create(name="Org 2", code="O2", email="o2@example.com")
        
        self.user1 = User.objects.create_user(username="u1@example.com", email="u1@example.com", password="pwd")
        self.user2 = User.objects.create_user(username="u2@example.com", email="u2@example.com", password="pwd")
        
        role = Role.objects.create(name="Admin", code="ADMIN")
        
        self.desg1 = Designation.objects.create(organization=self.org1, name="Eng", code="ENG")
        self.desg2 = Designation.objects.create(organization=self.org2, name="Mgr", code="MGR")
        
        from departments.models import Department
        from locations.models import Location
        
        self.dept1 = Department.objects.create(organization=self.org1, name="HR", code="HR")
        self.dept2 = Department.objects.create(organization=self.org2, name="IT", code="IT")
        
        self.loc1 = Location.objects.create(organization=self.org1, name="L1", code="L1", location_type="HQ")
        self.loc2 = Location.objects.create(organization=self.org2, name="L2", code="L2", location_type="HQ")

        self.emp1 = Employee.objects.create(user=self.user1, organization=self.org1, department=self.dept1, location=self.loc1, designation=self.desg1, employee_code="E1", role=role, joining_date="2024-01-01")
        self.emp2 = Employee.objects.create(user=self.user2, organization=self.org2, department=self.dept2, location=self.loc2, designation=self.desg2, employee_code="E2", role=role, joining_date="2024-01-01")

    def test_designation_list_tenant_isolation(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse("designation-list"))
        self.assertContains(response, "Eng")
        self.assertNotContains(response, "Mgr")

    def test_designation_create(self):
        self.client.force_login(self.user1)
        response = self.client.post(reverse("designation-create"), {
            "name": "VP",
            "code": "VP",
            "level": 5,
            "is_active": True
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Designation.objects.filter(organization=self.org1, code="VP").exists())
        self.assertFalse(Designation.objects.filter(organization=self.org2, code="VP").exists())

    def test_designation_update_tenant_isolation(self):
        self.client.force_login(self.user1)
        # Try to edit desg2 which belongs to org2
        response = self.client.get(reverse("designation-update", args=[self.desg2.pk]))
        self.assertEqual(response.status_code, 404)
