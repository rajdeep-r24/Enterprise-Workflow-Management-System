"""
Permission checks backed by the rbac.Permission / rbac.RolePermission models.

These models existed in the codebase but were never queried anywhere -
authorization was done purely by matching hardcoded role-code strings
(see employees/permissions.py). That's fine for coarse "which roles can
see this page" checks, but it means the Permission/RolePermission tables
can't actually gate anything yet.

This module adds the missing piece: a real lookup against RolePermission,
so you can start assigning fine-grained permissions to roles (via the
Django admin, since there's no rbac UI yet) and enforce them here instead
of only checking role names.

Nothing currently calls has_permission() by default - employees/permissions.py
still uses role_required() for existing views so nothing breaks. Use
has_permission()/permission_required() for new views where you want
per-permission (not just per-role) control.
"""
from functools import wraps

from django.shortcuts import redirect

from .models import RolePermission


def has_permission(user, permission_code):
    """
    Return True if the user's employee role has been granted the given
    permission code via RolePermission.

    Note: if you haven't created any RolePermission records yet (e.g. via
    the admin), this will always return False. It doesn't fall back to
    role-name checks - use employees.permissions.role_required for that.
    """
    from employees.models import Employee

    employee = Employee.objects.filter(user=user).select_related("role").first()
    if not employee or not employee.role:
        return False

    return RolePermission.objects.filter(
        role=employee.role,
        permission__code=permission_code,
        permission__is_active=True,
    ).exists()


def permission_required(permission_code):
    """
    View decorator that checks a specific permission code rather than a
    hardcoded list of role names. Redirects to 'dashboard' if not granted.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not has_permission(request.user, permission_code):
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
