from django.urls import path
from . import views

urlpatterns = [
    path("locations/", views.location_list, name="location-list"),
    path("locations/add/", views.location_create, name="location-create"),
    path("locations/<int:pk>/edit/", views.location_update, name="location-update"),
    path("locations/<int:pk>/deactivate/", views.location_deactivate, name="location-deactivate"),
]
