from django.urls import path
from . import views

urlpatterns = [
    path("departments/", views.department_list, name="department-list"),
    path("departments/add/", views.department_create, name="department-create"),
    path("departments/<int:pk>/edit/", views.department_update, name="department-update"),
    path("departments/<int:pk>/deactivate/", views.department_deactivate, name="department-deactivate"),
]
