from django.urls import path
from . import views

urlpatterns = [
    path(
        "profile/",
        views.profile,
        name="employee-profile",
    ),

    path(
        "employees/",
        views.employee_list,
        name="employee-list",
    ),

    path(
        "employees/<int:pk>/",
        views.employee_detail,
        name="employee-detail",
    ),

    path(
    "employees/create/",
    views.employee_create,
    name="employee-create",
    ),

    path(
    "employees/<int:pk>/edit/",
    views.employee_update,
    name="employee-update",
    ),

    path(
    "employees/<int:pk>/deactivate/",
    views.employee_deactivate,
    name="employee-deactivate",
    ),
]
