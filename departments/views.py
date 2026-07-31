from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from employees.permissions import role_required, HR_ROLES
from .models import Department
from .forms import DepartmentForm
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from employees.models import Employee

@login_required
@role_required(*HR_ROLES)
def department_list(request):
    query = request.GET.get("q", "")
    departments = Department.objects.for_tenant(request.tenant).order_by("name")
    
    if query:
        departments = departments.filter(
            Q(name__icontains=query) | Q(code__icontains=query)
        )
        
    paginator = Paginator(departments, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    return render(request, "departments/department_list.html", {
        "page_obj": page_obj,
        "query": query,
    })

@login_required
@role_required(*HR_ROLES)
def department_create(request):
    if request.method == "POST":
        form = DepartmentForm(request.POST, tenant=request.tenant)
        if form.is_valid():
            dept = form.save(commit=False)
            dept.organization = request.tenant
            dept.save()
            messages.success(request, "Department created successfully.")
            return redirect("department-list")
    else:
        form = DepartmentForm(tenant=request.tenant)
        
    return render(request, "departments/department_form.html", {
        "form": form,
        "title": "Add Department"
    })

@login_required
@role_required(*HR_ROLES)
def department_update(request, pk):
    department = get_object_or_404(Department.objects.for_tenant(request.tenant), pk=pk)
    
    if request.method == "POST":
        form = DepartmentForm(request.POST, instance=department, tenant=request.tenant)
        if form.is_valid():
            form.save()
            messages.success(request, "Department updated successfully.")
            return redirect("department-list")
    else:
        form = DepartmentForm(instance=department, tenant=request.tenant)
        
    return render(request, "departments/department_form.html", {
        "form": form,
        "title": "Edit Department",
        "department": department
    })

@login_required
@role_required(*HR_ROLES)
def department_deactivate(request, pk):
    department = get_object_or_404(Department.objects.for_tenant(request.tenant), pk=pk)
    
    if request.method == "POST":
        if Employee.objects.filter(department=department, is_active=True).exists():
            messages.error(request, "Cannot deactivate department with active employees.")
        else:
            department.is_active = False
            department.save(update_fields=["is_active"])
            messages.success(request, "Department deactivated successfully.")
        return redirect("department-list")
        
    return render(request, "departments/department_confirm_deactivate.html", {
        "department": department
    })
