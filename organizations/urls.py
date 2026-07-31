from django.urls import path
from . import views

urlpatterns = [
    path("signup/", views.organization_signup, name="organization_signup"),
]
