from accounts.models import User
from employees.models import Employee


class ApproverResolutionError(Exception):
    """Raised when an approver cannot be resolved for the configured strategy."""

    pass


class AmbiguousApproverError(ApproverResolutionError):
    """
    Raised when more than one active approver matches
    the same role in an organization.
    """

    def __init__(self, role_code, organization):
        self.role_code = role_code
        self.organization = organization

        super().__init__(
            f"Ambiguous approver resolution for role '{role_code}' "
            f"in organization '{organization}'"
        )


class ApproverResolver:

    @staticmethod
    def resolve(employee, step_definition):
        """
        Resolve the approver for an employee request.

        Supported strategies:
        - MANAGER
        - ROLE
        - SPECIFIC_USER
        """

        # =====================================================
        # MANAGER
        # =====================================================

        if step_definition.approver_type == "MANAGER":
            return (
                employee.manager.user
                if employee.manager
                else None
            )

        # =====================================================
        # SPECIFIC USER
        # =====================================================

        if step_definition.approver_type == "SPECIFIC_USER":

            if not step_definition.specific_approver_id:
                return None

            specific_user = step_definition.specific_approver

            # The configured user must be an active employee
            # belonging to the same organization as requester.
            employee_profile = (
                Employee.objects
                .filter(
                    user=specific_user,
                    organization=employee.organization,
                    is_active=True,
                )
                .first()
            )

            if employee_profile is None:
                return None

            return specific_user

        # =====================================================
        # ROLE
        # =====================================================

        if step_definition.approver_type == "ROLE":

            role_code = (
                step_definition.role_code or ""
            ).upper()

            if not role_code:
                return None

            matches = list(
                User.objects.filter(
                    employee_profile__role__code__iexact=role_code,
                    employee_profile__is_active=True,
                    employee_profile__organization=employee.organization,
                ).distinct()
            )

            # Multiple matching employees would make routing
            # arbitrary, so fail instead of using .first().
            if len(matches) > 1:
                raise AmbiguousApproverError(
                    role_code,
                    employee.organization,
                )

            return matches[0] if matches else None

        # =====================================================
        # UNKNOWN STRATEGY
        # =====================================================

        raise ApproverResolutionError(
            f"Unsupported approver strategy: "
            f"'{step_definition.approver_type}'"
        )

