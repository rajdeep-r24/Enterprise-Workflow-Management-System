from django.urls import path
from . import views

urlpatterns = [
    path("code-suggestion/", views.code_suggestion, name="code-suggestion"),
]
