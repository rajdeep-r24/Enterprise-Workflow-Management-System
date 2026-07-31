from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from employees.permissions import role_required, HR_ROLES
from .models import Designation
from .forms import DesignationForm
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from employees.models import Employee

@login_required
@role_required(*HR_ROLES)
def designation_list(request):
    query = request.GET.get("q", "")
    designations = Designation.objects.for_tenant(request.tenant).order_by("level", "name")
    
    if query:
        designations = designations.filter(
            Q(name__icontains=query) | Q(code__icontains=query)
        )
        
    paginator = Paginator(designations, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    return render(request, "designations/designation_list.html", {
        "page_obj": page_obj,
        "query": query,
    })

@login_required
@role_required(*HR_ROLES)
def designation_create(request):
    if request.method == "POST":
        form = DesignationForm(request.POST, tenant=request.tenant)
        if form.is_valid():
            desg = form.save(commit=False)
            desg.organization = request.tenant
            desg.save()
            messages.success(request, "Designation created successfully.")
            return redirect("designation-list")
    else:
        form = DesignationForm(tenant=request.tenant)
        
    return render(request, "designations/designation_form.html", {
        "form": form,
        "title": "Add Designation"
    })

@login_required
@role_required(*HR_ROLES)
def designation_update(request, pk):
    designation = get_object_or_404(Designation.objects.for_tenant(request.tenant), pk=pk)
    
    if request.method == "POST":
        form = DesignationForm(request.POST, instance=designation, tenant=request.tenant)
        if form.is_valid():
            form.save()
            messages.success(request, "Designation updated successfully.")
            return redirect("designation-list")
    else:
        form = DesignationForm(instance=designation, tenant=request.tenant)
        
    return render(request, "designations/designation_form.html", {
        "form": form,
        "title": "Edit Designation",
        "designation": designation
    })

@login_required
@role_required(*HR_ROLES)
def designation_deactivate(request, pk):
    designation = get_object_or_404(Designation.objects.for_tenant(request.tenant), pk=pk)
    
    if request.method == "POST":
        if Employee.objects.filter(designation=designation, is_active=True).exists():
            messages.error(request, "Cannot deactivate designation with active employees.")
        else:
            designation.is_active = False
            designation.save(update_fields=["is_active"])
            messages.success(request, "Designation deactivated successfully.")
        return redirect("designation-list")
        
    return render(request, "designations/designation_confirm_deactivate.html", {
        "designation": designation
    })
