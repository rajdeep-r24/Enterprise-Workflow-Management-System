from django.urls import path

from . import views

urlpatterns = [
    path(
        "request/<slug:code>/",
        views.submit_request,
        name="submit-request",
    ),

    path(
        "my-requests/",
        views.my_requests,
        name="my-requests",
    ),

    path(
        "requests/<int:pk>/",
        views.request_detail,
        name="request-detail",
    ),

    path(
        "attachment/<int:pk>/download/",
        views.download_attachment,
        name="download-attachment",
    ),

    path(
        "approvals/",
        views.approval_inbox,
        name="approval-inbox",
    ),

    path(
        "approvals/history/",
        views.approval_history,
        name="approval-history",
    ),

    path(
        "approvals/<int:pk>/approve/",
        views.approve_request,
        name="approve-request",
    ),

    path(
        "approvals/<int:pk>/reject/",
        views.reject_request,
        name="reject-request",
    ),

    path(
    "new-request/",
    views.new_request,
    name="new-request",
    ),

    path(
    "requests/<int:pk>/permission-pdf/",
    views.permission_pdf,
    name="permission-pdf",
    ),

    path(
    "verify/<uuid:token>/",
    views.verify_permission,
    name="verify-permission",
    ),

    path(
    "permissions/<int:pk>/revoke/",
    views.revoke_permission,
    name="revoke-permission",
    ),
]
