from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.shortcuts import get_object_or_404
from .forms import EmployeeRegistrationForm, EmployeeForm
from .models import Employee
from django.db import transaction
from accounts.forms import UserUpdateForm
from django.core.paginator import Paginator
from .services import EmployeeService, InvitationService
from .permissions import role_required, HR_ROLES
from accounts.decorators import public_access
from django.contrib import messages
from django.core.exceptions import ValidationError

@login_required
def profile(request):
    employee = getattr(request.user, "employee_profile", None)

    return render(
        request, "employees/profile.html", {"employee": employee}
    )


from django.db.models import Q

@login_required
@role_required(*HR_ROLES)
def employee_list(request):

    query = request.GET.get("q", "")

    employees = Employee.objects.for_tenant(request.tenant).filter(
    is_active=True).select_related(
        "user",
        "department",
        "designation",
        "organization",
        "location",
    )

    if query:
        employees = employees.filter(
            Q(employee_code__icontains=query)
            | Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(user__email__icontains=query)
            | Q(department__name__icontains=query)
            | Q(designation__name__icontains=query)
        )

    paginator = Paginator(employees, 10)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "employees/employee_list.html",
        {
            "page_obj": page_obj,
            "query": query,
        },
    )


@login_required
@role_required(*HR_ROLES)
def employee_detail(request, pk):
    
    employee = get_object_or_404(
        Employee.objects.for_tenant(request.tenant).select_related(
            "user",
            "organization",
            "department",
            "designation",
            "location",
        ),
        pk=pk,
    )

    return render(
        request,
        "employees/employee_detail.html",
        {
            "employee": employee,
        },
    )


@login_required
@role_required(*HR_ROLES)
def employee_create(request):
    if request.method == "POST":
        form = EmployeeRegistrationForm(request.POST, tenant=request.tenant)

        if form.is_valid():
            employee = form.save()
            
            # Create invitation
            invitation, raw_token = InvitationService.create_invitation(employee, request.user)
            
            # For local development testing
            print(f"\n--- ONBOARDING INVITATION CREATED ---")
            print(f"Employee: {employee.user.email}")
            print(f"Raw Token: {raw_token}")
            print(f"-------------------------------------\n")
            
            return redirect("employee-list")

    else:
        form = EmployeeRegistrationForm(tenant=request.tenant)

    return render(
        request,
        "employees/employee_create.html",
        {"form": form},
    )


@login_required
@transaction.atomic
@role_required(*HR_ROLES)
def employee_update(request, pk):
    employee = get_object_or_404(Employee.objects.for_tenant(request.tenant), pk=pk)

    if request.method == "POST":

        user_form = UserUpdateForm(
            request.POST,
            instance=employee.user,
        )

        employee_form = EmployeeForm(
            request.POST,
            instance=employee,
            tenant=request.tenant,
        )

        if user_form.is_valid() and employee_form.is_valid():

            user_form.save()
            employee_form.save()

            return redirect("employee-detail", pk=employee.pk)

    else:

        user_form = UserUpdateForm(
            instance=employee.user,
        )

        employee_form = EmployeeForm(
            instance=employee,
            tenant=request.tenant,
        )

    return render(
        request,
        "employees/employee_update.html",
        {
            "user_form": user_form,
            "employee_form": employee_form,
            "employee": employee,
        },
    )

@login_required
@transaction.atomic
@role_required(*HR_ROLES)
def employee_deactivate(request, pk):
    employee = get_object_or_404(Employee.objects.for_tenant(request.tenant), pk=pk)

    if request.method == "POST":
        EmployeeService.deactivate(employee)

        return redirect("employee-list")

    return render(
        request,
        "employees/employee_confirm_deactivate.html",
        {
            "employee": employee,
        },
    )

@public_access
def employee_onboarding(request, token):
    try:
        invitation = InvitationService.validate_token(token)
    except ValidationError:
        return render(request, "employees/onboarding_invalid.html")

    if request.method == "POST":
        # Note: import EmployeeOnboardingForm if not already imported
        from .forms import EmployeeOnboardingForm
        form = EmployeeOnboardingForm(request.POST)
        if form.is_valid():
            InvitationService.accept_invitation(token, form.cleaned_data["password"])
            messages.success(request, "Your account has been activated successfully. You can now login.")
            return redirect("login")
    else:
        from .forms import EmployeeOnboardingForm
        form = EmployeeOnboardingForm()

    return render(
        request,
        "employees/onboarding.html",
        {"form": form, "invitation": invitation}
    )

