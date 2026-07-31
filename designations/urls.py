from django.urls import path
from . import views

urlpatterns = [
    path("designations/", views.designation_list, name="designation-list"),
    path("designations/add/", views.designation_create, name="designation-create"),
    path("designations/<int:pk>/edit/", views.designation_update, name="designation-update"),
    path("designations/<int:pk>/deactivate/", views.designation_deactivate, name="designation-deactivate"),
]
