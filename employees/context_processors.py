from .permissions import get_employee_role, can_approve, can_view_employees


def role_context(request):
    if not request.user.is_authenticated:
        return {}

    role = get_employee_role(request.user)

    return {
        "employee_role": role,
        "user_can_approve": can_approve(request.user),
        "user_can_view_employees": can_view_employees(request.user),
    }
