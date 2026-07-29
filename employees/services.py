from django.db import transaction

from accounts.models import User
from .models import Employee


class EmployeeService:

    @staticmethod
    @transaction.atomic
    def deactivate(employee):

        employee.is_active = False
        employee.save(update_fields=["is_active"])

        return employee
