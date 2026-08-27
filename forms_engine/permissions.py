from employees.models import Employee
from workflow.models.instances import WorkflowStepInstance


def can_comment_on_request(user, submission):
    """
    Reusable permission check determining if a user can post notes on a request.
    Allowed:
    1. Requester (owner)
    2. Currently assigned approver on a pending workflow step
    3. Authorized organization administrators (HR_HEAD, ADMIN, ORG_ADMIN, SUPER_ADMIN)
    """
    if not user or not user.is_authenticated or not submission:
        return False

    # 1. Requester
    if submission.submitted_by_id == user.pk:
        return True

    # 2. Currently assigned approver on a pending step
    if submission.workflow_instance_id:
        is_assigned = WorkflowStepInstance.objects.filter(
            workflow_instance_id=submission.workflow_instance_id,
            status="PENDING",
            assigned_to=user,
        ).exists()
        if is_assigned:
            return True

    # 3. Authorized organization administrator
    employee = Employee.objects.filter(user=user, organization=submission.organization).select_related("role").first()
    if employee and employee.role and employee.role.code in ["HR_HEAD", "ADMIN", "ORG_ADMIN", "SUPER_ADMIN"]:
        return True

    return False
