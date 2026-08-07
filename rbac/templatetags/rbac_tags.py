from django import template
from rbac.models import Role

register = template.Library()


@register.filter
def role_display(value):
    """
    Template filter to display friendly role names.
    Accepts a Role object, a role code string, or None.
    """
    if not value:
        return ""

    if hasattr(value, "display_name"):
        return value.display_name

    return Role.get_display_name(str(value))
