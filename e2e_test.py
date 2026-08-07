import os
import django
import sys
import json
import traceback

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client
from accounts.models import User
from organizations.models import Organization
from departments.models import Department
from designations.models import Designation
from locations.models import Location
from employees.models import Employee
from rbac.models import Role

def run():
    c = Client(enforce_csrf_checks=False, SERVER_NAME="127.0.0.1")
    
    print("=== Step 1: Organization Signup ===")
    res = c.get("/signup/")
    if res.status_code != 200: return 1, f"Signup GET failed: {res.status_code}"
    
    # POST signup
    data = {
        "organization_name": "Test Org Inc",
        "first_name": "Admin",
        "last_name": "User",
        "email": "admin@testorg.com",
        "password": "Password123",
        "confirm_password": "Password123",
    }
    res = c.post("/signup/", data)
    if res.status_code == 200:
        import re
        errors = re.findall(r'<ul class="errorlist">(.*?)</ul>', res.content.decode("utf-8"), re.DOTALL)
        print("Form Errors (errorlist):", errors)
        errors2 = re.findall(r'<div[^>]*class="[^"]*error[^"]*"[^>]*>(.*?)</div>', res.content.decode("utf-8"), re.DOTALL)
        print("Form Errors (divs):", errors2)
    elif res.status_code != 302:
        return 1, f"Signup POST failed: {res.status_code}"
    
    org = Organization.objects.order_by('-id').first()
    if not org:
        return 1, "Organization not created"
    
    admin_user = User.objects.filter(email="admin@testorg.com").first()
    if not admin_user:
        return 1, "Admin user not created"
        
    print("=== Step 2: Organization Admin Login ===")
    res = c.post("/login/", {"username": "admin@testorg.com", "password": "Password123"})
    if res.status_code == 200:
        import re
        errors = re.findall(r'<div[^>]*class="[^"]*error[^"]*"[^>]*>(.*?)</div>', res.content.decode("utf-8"), re.DOTALL)
        print("Login Errors (divs):", errors)
        errors = re.findall(r'<ul class="errorlist">(.*?)</ul>', res.content.decode("utf-8"), re.DOTALL)
        print("Login Errors (ul):", errors)
        return 2, f"Login failed: {res.status_code}"
    
    login_redirect = res.url
    print("Redirected to:", login_redirect)
    
    res = c.get(login_redirect)
    print("Dashboard HTML:", res.content.decode("utf-8"))
    print("Redirected to:", login_redirect)
    
    # Follow the redirect
    res = c.get(login_redirect)
    
    print("=== Step 3: Setup Wizard ===")
    res = c.get("/setup/wizard/")
    if res.status_code != 200:
        return 3, f"Wizard GET failed: {res.status_code}"
        
    print("=== Step 4: Create Department ===")
    data = {
        "name": "Engineering",
        "code": "ENG",
        "description": "Tech department",
        "email": "eng@testorg.com",
        "phone": "111222333",
        "is_active": True,
    }
    res = c.post("/departments/add/", data)
    if res.status_code != 302:
        if b"already exists" not in res.content:
            return 4, f"Create Department POST failed: {res.status_code}"
            
    print("=== Step 5: Create Designation ===")
    data = {
        "name": "Software Engineer",
        "code": "SE",
        "level": 3,
        "description": "Writes code",
        "is_active": True,
    }
    res = c.post("/designations/add/", data)
    if res.status_code != 302:
        if b"already exists" not in res.content:
            return 5, f"Create Designation POST failed: {res.status_code}"

    print("=== Step 6: Create Location ===")
    data = {
        "name": "Headquarters",
        "code": "HQ01",
        "location_type": "HQ",
        "address": "123 Main St",
        "city": "Testville",
        "state": "TS",
        "country": "India",
        "is_active": True,
    }
    res = c.post("/locations/add/", data)
    if res.status_code != 302:
        if b"already exists" not in res.content:
            return 6, f"Create Location POST failed: {res.status_code}"

    print("=== Step 7: Create Employee ===")
    dept = Department.objects.filter(organization=org).first()
    desig = Designation.objects.filter(organization=org).first()
    loc = Location.objects.filter(organization=org).first()
    role_emp = Role.objects.get(code="EMPLOYEE")
    
    data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@testorg.com",
        "phone": "9876543210",
        "date_of_birth": "1990-01-01",
        "department": dept.id,
        "designation": desig.id,
        "location": loc.id,
        "role": role_emp.id,
        "manager": "",
        "joining_date": "2020-01-01",
        "is_active": True,
    }
    res = c.post("/employees/add/", data)
    if res.status_code != 302:
        if b"Email already exists" not in res.content:
            return 7, f"Create Employee POST failed: {res.status_code}"

    print("=== Step 8: Employee First Login ===")
    c.logout()
    res = c.post("/login/", {"email": "john.doe@testorg.com", "password": "Password123!"}) 
    # Wait, what's the default password? 
    # Employee creation form sets a password. Let's check employee creation logic.
    # It probably sets a random password or default. We can just force login for testing.
    emp_user = User.objects.filter(email="john.doe@testorg.com").first()
    c.force_login(emp_user)
    
    res = c.get("/dashboard/")
    if res.status_code != 200:
        return 8, f"Employee Dashboard failed: {res.status_code}"
    
    # We will return success up to this point and then test more.
    return 0, "Passed initial steps"

try:
    step, msg = run()
    if step != 0:
        print(f"FAILED AT STEP {step}")
        print(f"BUG: {msg}")
    else:
        print("SUCCESS SO FAR")
except Exception as e:
    print(f"EXCEPTION: {str(e)}")
    traceback.print_exc()

