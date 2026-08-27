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
        "requests/<int:pk>/comment/",
        views.add_request_comment,
        name="add-request-comment",
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

    path(
        "request-types/",
        views.request_type_list,
        name="request-type-list",
    ),

    path(
        "request-types/add/",
        views.request_type_create,
        name="request-type-create",
    ),

    path(
        "request-types/<int:pk>/summary/",
        views.request_type_summary,
        name="request-type-summary",
    ),

    path(
        "request-types/<int:pk>/publish/",
        views.request_type_publish,
        name="request-type-publish",
    ),

    path(
        "request-types/<int:pk>/fields/",
        views.request_type_fields,
        name="request-type-fields",
    ),

    path(
        "request-types/<int:pk>/fields/add/",
        views.request_type_field_add,
        name="request-type-field-add",
    ),

    path(
        "request-types/<int:rt_pk>/fields/<int:field_pk>/edit/",
        views.request_type_field_edit,
        name="request-type-field-edit",
    ),

    path(
        "request-types/<int:rt_pk>/fields/<int:field_pk>/delete/",
        views.request_type_field_delete,
        name="request-type-field-delete",
    ),
    
    path(
        "request-types/<int:pk>/steps/",
        views.request_type_steps,
        name="request-type-steps",
    ),

    path(
        "request-types/<int:pk>/steps/add/",
        views.request_type_step_add,
        name="request-type-step-add",
    ),

    path(
        "request-types/<int:rt_pk>/steps/<int:step_pk>/edit/",
        views.request_type_step_edit,
        name="request-type-step-edit",
    ),

    path(
        "request-types/<int:rt_pk>/steps/<int:step_pk>/delete/",
        views.request_type_step_delete,
        name="request-type-step-delete",
    ),

    path(
        "export-audit-trail/",
        views.export_audit_trail,
        name="export-audit-trail",
    ),

    path(
        "approvals/history/export/",
        views.export_approval_history_csv,
        name="export-approval-history-csv",
    ),
]
