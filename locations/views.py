from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from employees.permissions import role_required, HR_ROLES
from .models import Location
from .forms import LocationForm
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from employees.models import Employee

@login_required
@role_required(*HR_ROLES)
def location_list(request):
    query = request.GET.get("q", "")
    locations = Location.objects.for_tenant(request.tenant).order_by("name")
    
    if query:
        locations = locations.filter(
            Q(name__icontains=query) | Q(code__icontains=query) | Q(city__icontains=query)
        )
        
    paginator = Paginator(locations, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    return render(request, "locations/location_list.html", {
        "page_obj": page_obj,
        "query": query,
    })

@login_required
@role_required(*HR_ROLES)
def location_create(request):
    if request.method == "POST":
        form = LocationForm(request.POST, tenant=request.tenant)
        if form.is_valid():
            loc = form.save(commit=False)
            loc.organization = request.tenant
            loc.save()
            messages.success(request, "Location created successfully.")
            return redirect("location-list")
    else:
        form = LocationForm(tenant=request.tenant)
        
    return render(request, "locations/location_form.html", {
        "form": form,
        "title": "Add Location"
    })

@login_required
@role_required(*HR_ROLES)
def location_update(request, pk):
    location = get_object_or_404(Location.objects.for_tenant(request.tenant), pk=pk)
    
    if request.method == "POST":
        form = LocationForm(request.POST, instance=location, tenant=request.tenant)
        if form.is_valid():
            form.save()
            messages.success(request, "Location updated successfully.")
            return redirect("location-list")
    else:
        form = LocationForm(instance=location, tenant=request.tenant)
        
    return render(request, "locations/location_form.html", {
        "form": form,
        "title": "Edit Location",
        "location": location
    })

@login_required
@role_required(*HR_ROLES)
def location_deactivate(request, pk):
    location = get_object_or_404(Location.objects.for_tenant(request.tenant), pk=pk)
    
    if request.method == "POST":
        if Employee.objects.filter(location=location, is_active=True).exists():
            messages.error(request, "Cannot deactivate location with active employees.")
        else:
            location.is_active = False
            location.save(update_fields=["is_active"])
            messages.success(request, "Location deactivated successfully.")
        return redirect("location-list")
        
    return render(request, "locations/location_confirm_deactivate.html", {
        "location": location
    })
