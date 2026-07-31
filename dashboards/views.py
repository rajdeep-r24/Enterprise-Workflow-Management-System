from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from employees.models import Employee
from workflow.models.instances import WorkflowInstance, WorkflowStepInstance


from accounts.decorators import public_access

@public_access
def landing(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "landing.html")


@login_required
def dashboard(request):

    # ==============================
    # EMPLOYEE DASHBOARD
    # ==============================

    employee = Employee.objects.filter(
        user=request.user
    ).select_related(
        "role"
    ).first()

    # Safety check for users without Employee profile
    if not employee:

        context = {
            "role": "USER",
            "my_requests": WorkflowInstance.objects.for_tenant(request.tenant).filter(
                initiated_by=request.user,
            ).count(),
        }

        return render(
            request,
            "dashboards/dashboard.html",
            context,
        )

    role = employee.role.code

    context = {
        "role": role,
    }

    # ORG_ADMIN Dashboard
    if role == "ORG_ADMIN":

        context.update({
            "total_employees": Employee.objects.for_tenant(request.tenant).filter(is_active=True).count(),

            "pending_requests": WorkflowInstance.objects.for_tenant(request.tenant).filter(
                status="IN_PROGRESS",
            ).count(),

            "approved_requests": WorkflowInstance.objects.for_tenant(request.tenant).filter(
                status="APPROVED",
            ).count(),

            "rejected_requests": WorkflowInstance.objects.for_tenant(request.tenant).filter(
                status="REJECTED",
            ).count(),
        })

    # Legacy / Compatibility Dashboard for ADMIN / SUPER_ADMIN
    elif role in [
        "ADMIN",
        "SUPER_ADMIN",
    ]:

        context.update({
            "total_employees": Employee.objects.for_tenant(request.tenant).filter(is_active=True).count(),

            "pending_requests": WorkflowStepInstance.objects.filter(
                workflow_instance__organization=request.tenant,
                assigned_to=request.user,
                status="PENDING",
            ).count(),

            "approved_requests": WorkflowInstance.objects.for_tenant(request.tenant).filter(
                status="APPROVED",
            ).count(),

            "rejected_requests": WorkflowInstance.objects.for_tenant(request.tenant).filter(
                status="REJECTED",
            ).count(),
        })

    # Approver Roles Dashboard
    elif role in [
        "HR_HEAD",
        "MANAGER",
        "IT_HEAD",
        "UNIT_HEAD",
    ]:

        context.update({
            "my_pending_approvals": WorkflowStepInstance.objects.filter(
                workflow_instance__organization=request.tenant,
                assigned_to=request.user,
                status="PENDING",
            ).count(),

            "my_requests": WorkflowInstance.objects.for_tenant(request.tenant).filter(
                initiated_by=request.user,
            ).count(),
        })

    # Normal Employee Dashboard
    else:

        context.update({
            "my_requests": WorkflowInstance.objects.for_tenant(request.tenant).filter(
                initiated_by=request.user,
            ).count(),
        })

    return render(
        request,
        "dashboards/dashboard.html",
        context,
    )
