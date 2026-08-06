"""
rbac/migrations/0003_seed_default_roles.py

Data migration: seeds the canonical set of RBAC roles required for
ForgeFlow to function on any fresh installation.

Design decisions:
- Uses get_or_create() on (code=) so the migration is fully idempotent:
  safe to run against an existing database, a fresh database, or after a
  reverse/re-apply cycle without creating duplicates.
- The reverse operation is intentionally a no-op (RunPython.noop) because
  deleting roles on rollback could cascade-delete employee records, which
  is almost never the desired behaviour in production.
- The app registry is accessed via the historical model returned by
  migrations.RunPython so this migration is future-proof if the Role
  model ever gains new required fields.
"""
from django.db import migrations


ROLES = [
    {
        "code": "ORG_ADMIN",
        "name": "Organization Administrator",
        "description": (
            "Full administrative control over the organization. "
            "Can configure workflows, manage employees, departments, "
            "designations, locations, and all request types."
        ),
    },
    {
        "code": "SUPER_ADMIN",
        "name": "Super Administrator",
        "description": (
            "Platform-level super administrator. Elevated privileges "
            "above ORG_ADMIN; reserved for platform operators."
        ),
    },
    {
        "code": "ADMIN",
        "name": "Administrator",
        "description": (
            "Organization-scoped administrator. Can manage employees "
            "and organizational settings but cannot configure workflows."
        ),
    },
    {
        "code": "HR_HEAD",
        "name": "HR Head",
        "description": (
            "Head of Human Resources. Acts as an approver in HR-related "
            "approval chains and can view all employee records."
        ),
    },
    {
        "code": "MANAGER",
        "name": "Manager",
        "description": (
            "Line manager / team lead. Acts as a first-level approver "
            "for requests submitted by their direct reports."
        ),
    },
    {
        "code": "IT_HEAD",
        "name": "IT Head",
        "description": (
            "Head of Information Technology. Acts as an approver in "
            "IT-related approval chains such as equipment and software access."
        ),
    },
    {
        "code": "UNIT_HEAD",
        "name": "Unit Head",
        "description": (
            "Head of a business unit or cost centre. Acts as an approver "
            "for requests originating from their unit."
        ),
    },
    {
        "code": "EMPLOYEE",
        "name": "Employee",
        "description": (
            "Standard employee. Can submit requests and track their own "
            "approval status. Cannot approve requests."
        ),
    },
]


def seed_roles(apps, schema_editor):
    """
    Create the canonical RBAC roles if they do not already exist.
    Existing rows are left untouched (name / description are NOT
    overwritten) so that organizations that have customised role labels
    are not affected.
    """
    Role = apps.get_model("rbac", "Role")
    db_alias = schema_editor.connection.alias

    for role_data in ROLES:
        Role.objects.using(db_alias).get_or_create(
            code=role_data["code"],
            defaults={
                "name": role_data["name"],
                "description": role_data["description"],
                "is_active": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("rbac", "0002_alter_permission_options_and_more"),
    ]

    operations = [
        migrations.RunPython(
            seed_roles,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
