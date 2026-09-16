from django.urls import path
from . import views

urlpatterns = [
    path("code-suggestion/", views.code_suggestion, name="code-suggestion"),
    path("openapi.json", views.openapi_schema, name="openapi-schema"),
    path("docs/", views.api_docs, name="api-docs"),
]
