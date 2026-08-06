import dataclasses
from django.db import transaction
from django.utils.crypto import get_random_string
from accounts.models import User
from employees.models import Employee

@dataclasses.dataclass
class ProvisioningResult:
    employee: Employee
    temp_password: str

class EmployeeProvisioningService:
    @staticmethod
    @transaction.atomic
    def provision_employee(data, tenant):
        """
        Creates a User and Employee account based on validated form data.
        Returns a ProvisioningResult containing the Employee instance and a temporary password.
        """
        temp_password = get_random_string(length=12)

        user = User.objects.create_user(
            username=data["email"],
            email=data["email"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            phone=data.get("phone", ""),
            date_of_birth=data.get("date_of_birth"),
            is_active=True,
            requires_password_change=True,
        )
        user.set_password(temp_password)
        user.save()

        # Generate employee code
        latest_employee = Employee.objects.filter(
            organization=tenant,
            employee_code__regex=r'^EMP\d{4}$'
        ).order_by('-employee_code').first()

        if latest_employee:
            last_num = int(latest_employee.employee_code[3:])
            new_code = f"EMP{last_num + 1:04d}"
        else:
            new_code = "EMP0001"

        employee = Employee.objects.create(
            user=user,
            employee_code=new_code,
            organization=tenant,
            department=data["department"],
            location=data["location"],
            designation=data["designation"],
            role=data["role"],
            manager=data.get("manager"),
            joining_date=data["joining_date"],
            is_active=data.get("is_active", True),
        )

        return ProvisioningResult(
            employee=employee,
            temp_password=temp_password,
        )
