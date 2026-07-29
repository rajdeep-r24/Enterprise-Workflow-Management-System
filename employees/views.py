from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.shortcuts import get_object_or_404
from .forms import EmployeeRegistrationForm, EmployeeForm
from .models import Employee
from django.db import transaction
from accounts.forms import UserUpdateForm
from django.core.paginator import Paginator
from .services import EmployeeService
from .permissions import role_required

@login_required
def profile(request):
    employee = getattr(request.user, "employee_profile", None)

    return render(
        request, "employees/profile.html", {"employee": employee}
    )


from django.db.models import Q

@login_required
@role_required("HR_HEAD", "ADMIN")
def employee_list(request):

    query = request.GET.get("q", "")

    employees = Employee.objects.filter(
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


def employee_detail(request, pk):
    
    employee = get_object_or_404(
        Employee.objects.select_related(
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
@role_required("HR_HEAD", "ADMIN")
def employee_create(request):
    if request.method == "POST":
        form = EmployeeRegistrationForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("employee-list")

    else:
        form = EmployeeRegistrationForm()

    return render(
        request,
        "employees/employee_create.html",
        {"form": form},
    )


@login_required
@transaction.atomic
@role_required("HR_HEAD", "ADMIN")
def employee_update(request, pk):
    employee = get_object_or_404(Employee, pk=pk)

    if request.method == "POST":

        user_form = UserUpdateForm(
            request.POST,
            instance=employee.user,
        )

        employee_form = EmployeeForm(
            request.POST,
            instance=employee,
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
@role_required("HR_HEAD", "ADMIN")
def employee_deactivate(request, pk):
    employee = get_object_or_404(Employee, pk=pk)

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
