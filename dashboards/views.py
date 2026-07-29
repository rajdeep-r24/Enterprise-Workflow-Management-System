from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from employees.models import Employee
from workflow.models.instances import WorkflowInstance, WorkflowStepInstance


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
            "my_requests": WorkflowInstance.objects.filter(
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

    # HR / ADMIN Dashboard
    if role in [
        "HR_HEAD",
        "ADMIN",
        "ORG_ADMIN",
        "SUPER_ADMIN",
    ]:

        context.update({
            "total_employees": Employee.objects.count(),

            "pending_requests": WorkflowStepInstance.objects.filter(
                assigned_to=request.user,
                status="PENDING",
            ).count(),

            "approved_requests": WorkflowInstance.objects.filter(
                status="APPROVED",
            ).count(),

            "rejected_requests": WorkflowInstance.objects.filter(
                status="REJECTED",
            ).count(),
        })

    # Manager / IT / Unit Head Dashboard
    elif role in [
        "MANAGER",
        "IT_HEAD",
        "UNIT_HEAD",
    ]:

        context.update({
            "my_pending_approvals": WorkflowStepInstance.objects.filter(
                assigned_to=request.user,
                status="PENDING",
            ).count(),

            "my_requests": WorkflowInstance.objects.filter(
                initiated_by=request.user,
            ).count(),
        })

    # Normal Employee Dashboard
    else:

        context.update({
            "my_requests": WorkflowInstance.objects.filter(
                initiated_by=request.user,
            ).count(),
        })

    return render(
        request,
        "dashboards/dashboard.html",
        context,
    )
