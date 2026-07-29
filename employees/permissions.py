from functools import wraps

from django.http import HttpResponseForbidden
from django.shortcuts import redirect

from employees.models import Employee


APPROVER_ROLES = {"MANAGER", "HR_HEAD", "IT_HEAD", "UNIT_HEAD", "ADMIN", "ORG_ADMIN", "SUPER_ADMIN"}
HR_ROLES = {"HR_HEAD", "ADMIN", "ORG_ADMIN", "SUPER_ADMIN"}


def get_employee_role(user):
    employee = Employee.objects.filter(user=user).first()
    if not employee:
        return None
    return employee.role.code if employee.role else None


def can_approve(user):
    return get_employee_role(user) in APPROVER_ROLES


def can_view_employees(user):
    return get_employee_role(user) in HR_ROLES


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            role = get_employee_role(request.user)
            if role not in allowed_roles:
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
