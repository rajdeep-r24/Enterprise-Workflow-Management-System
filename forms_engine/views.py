import os
from datetime import datetime, time
from django.db import transaction

from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden, FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from employees.models import Employee
from employees.permissions import can_approve, role_required
from workflow.models.events import WorkflowEvent
from workflow.models.instances import WorkflowStepInstance
from workflow.services import WorkflowService

from .forms import DynamicForm
from .models import FormDefinition, FormSubmission, RequestAttachment
from .pdf_generator import generate_permission_pdf
from .services import FormEngineService


# =========================================================
# SUBMIT REQUEST
# =========================================================

@login_required
def submit_request(request, code):

    form_definition = get_object_or_404(
        FormDefinition,
        code=code,
        is_published=True,
    )

    if request.method == "POST":

        form = DynamicForm(
            form_definition,
            request.POST,
        )

        if form.is_valid():

            attachments = request.FILES.getlist('attachments')
            
            # Validation
            validation_error = None
            max_size = 10 * 1024 * 1024
            allowed_exts = {'.pdf', '.png', '.jpg', '.jpeg', '.doc', '.docx', '.xls', '.xlsx'}
            
            for f in attachments:
                if f.size > max_size:
                    validation_error = f"File {f.name} exceeds the 10MB size limit."
                    break
                ext = os.path.splitext(f.name)[1].lower()
                if ext not in allowed_exts:
                    validation_error = f"File {f.name} has an invalid extension. Allowed extensions are PDF, PNG, JPG, DOC/X, XLS/X."
                    break
                    
            if validation_error:
                messages.error(request, validation_error)
                return render(
                    request,
                    "forms_engine/submit_request.html",
                    {
                        "form": form,
                        "form_definition": form_definition,
                    },
                )

            try:
                with transaction.atomic():
                    submission = FormEngineService.submit(
                        form_definition,
                        request.user,
                        form.cleaned_data,
                    )
                    
                    for f in attachments:
                        RequestAttachment.objects.create(
                            submission=submission,
                            file=f,
                            original_filename=f.name,
                            uploaded_by=request.user
                        )
                
                messages.success(
                    request,
                    "Request submitted successfully.",
                )

                return redirect("dashboard")
            except Exception as e:
                messages.error(
                    request,
                    f"An error occurred during submission: {str(e)}"
                )

    else:

        form = DynamicForm(
            form_definition,
        )

    return render(
        request,
        "forms_engine/submit_request.html",
        {
            "form": form,
            "form_definition": form_definition,
        },
    )


# =========================================================
# MY REQUESTS
# =========================================================

@login_required
def my_requests(request):

    submissions = (
        FormSubmission.objects
        .select_related(
            "form",
            "workflow_instance__current_step",
        )
        .filter(
            submitted_by=request.user,
        )
        .order_by("-created_at")
    )

    return render(
        request,
        "forms_engine/my_requests.html",
        {
            "submissions": submissions,
        },
    )


# =========================================================
# APPROVAL INBOX
# =========================================================

@login_required
@role_required(
    "MANAGER",
    "HR_HEAD",
    "IT_HEAD",
    "UNIT_HEAD",
    "ADMIN",
    "ORG_ADMIN",
    "SUPER_ADMIN",
)
def approval_inbox(request):

    approvals = (
        WorkflowStepInstance.objects
        .select_related(
            "workflow_instance",
            "workflow_instance__initiated_by",
            "workflow_instance__current_step",
            "step_definition",
        )
        .filter(
            status="PENDING",
            assigned_to=request.user,
        )
        .order_by("-created_at")
    )

    return render(
        request,
        "forms_engine/approval_inbox.html",
        {
            "approvals": approvals,
        },
    )


# =========================================================
# APPROVAL HISTORY (audit view for approvers)
# =========================================================

@login_required
@role_required(
    "MANAGER",
    "HR_HEAD",
    "IT_HEAD",
    "UNIT_HEAD",
    "ADMIN",
    "ORG_ADMIN",
    "SUPER_ADMIN",
)
def approval_history(request):

    history = (
        WorkflowStepInstance.objects
        .select_related(
            "workflow_instance",
            "workflow_instance__initiated_by",
            "workflow_instance__formsubmission",
            "workflow_instance__formsubmission__form",
            "step_definition",
        )
        .filter(
            assigned_to=request.user,
        )
        .exclude(
            status="PENDING",
        )
        .order_by("-action_at", "-created_at")
    )

    status_filter = request.GET.get("status")
    if status_filter in ("APPROVED", "REJECTED"):
        history = history.filter(status=status_filter)

    return render(
        request,
        "forms_engine/approval_history.html",
        {
            "history": history,
            "status_filter": status_filter,
            "approved_count": WorkflowStepInstance.objects.filter(assigned_to=request.user, status="APPROVED").count(),
            "rejected_count": WorkflowStepInstance.objects.filter(assigned_to=request.user, status="REJECTED").count(),
        },
    )


# =========================================================
# REQUEST DETAILS
# =========================================================

def can_view_request(user, submission):
    is_owner = (submission.submitted_by == user)
    if is_owner:
        return True

    if can_approve(user):
        return True

    employee = Employee.objects.filter(user=user).select_related("role").first()
    if employee and employee.role.code in ["HR_HEAD", "ADMIN", "ORG_ADMIN", "SUPER_ADMIN"]:
        return True

    is_assigned_approver = WorkflowStepInstance.objects.filter(
        workflow_instance=submission.workflow_instance,
        status="PENDING",
        assigned_to=user
    ).exists()
    
    return is_assigned_approver

@login_required
def download_attachment(request, pk):
    attachment = get_object_or_404(RequestAttachment, pk=pk)
    submission = attachment.submission
    
    if not can_view_request(request.user, submission):
        return HttpResponseForbidden("Permission Denied")
        
    return FileResponse(attachment.file, as_attachment=True, filename=attachment.original_filename)

@login_required
def request_detail(request, pk):

    submission = get_object_or_404(
        FormSubmission.objects.select_related(
            "form",
            "submitted_by",
            "workflow_instance__current_step",
        ),
        pk=pk,
    )

    employee = (
        Employee.objects
        .filter(
            user=request.user,
        )
        .select_related(
            "role",
        )
        .first()
    )

    # Check if current user owns this request
    is_owner = (
        submission.submitted_by
        == request.user
    )

    # Get ONLY the currently pending workflow step
    current_step = (
        WorkflowStepInstance.objects
        .filter(
            workflow_instance=submission.workflow_instance,
            status="PENDING",
        )
        .select_related(
            "assigned_to",
            "step_definition",
        )
        .first()
    )

    # Check if current user is the current approver
    is_assigned_approver = bool(
        current_step
        and current_step.assigned_to
        == request.user
    )

    # Check if user has administrative permission
    is_hr = bool(
        employee
        and employee.role.code
        in [
            "HR_HEAD",
            "ADMIN",
            "ORG_ADMIN",
            "SUPER_ADMIN",
        ]
    )

    # =====================================================
    # CHECK IF USER CAN REVOKE PERMISSION
    # =====================================================

    can_revoke = bool(
        employee
        and employee.role.code
        in [
            "HR_HEAD",
            "ADMIN",
            "ORG_ADMIN",
            "SUPER_ADMIN",
        ]
        and submission.status == "APPROVED"
    )

    # =====================================================
    # ACCESS CONTROL
    # =====================================================

    if not can_view_request(request.user, submission):
        return HttpResponseForbidden(
            "Permission Denied"
        )

    # =====================================================
    # FORM VALUES
    # =====================================================

    values = (
        submission.values
        .select_related(
            "field",
        )
        .all()
        .order_by(
            "field__order",
        )
    )

    # =====================================================
    # WORKFLOW TIMELINE
    # =====================================================

    events = (
        WorkflowEvent.objects
        .filter(
            workflow_instance=submission.workflow_instance,
        )
        .select_related(
            "performed_by",
        )
        .order_by(
            "created_at",
        )
    )

    # =====================================================
    # RENDER PAGE
    # =====================================================

    return render(
        request,
        "forms_engine/request_detail.html",
        {
            "submission": submission,
            "values": values,
            "current_step": current_step,
            "is_assigned_approver": is_assigned_approver,
            "can_take_action": is_assigned_approver,
            "can_revoke": can_revoke,
            "events": events,
        },
    )


# =========================================================
# APPROVE REQUEST
# =========================================================

@login_required
@role_required(
    "MANAGER",
    "HR_HEAD",
    "IT_HEAD",
    "UNIT_HEAD",
    "ADMIN",
    "ORG_ADMIN",
    "SUPER_ADMIN",
)
def approve_request(request, pk):

    step = get_object_or_404(
        WorkflowStepInstance,
        pk=pk,
        assigned_to=request.user,
        status="PENDING",
    )

    submission = get_object_or_404(
        FormSubmission,
        workflow_instance=step.workflow_instance,
    )

    if request.method != "POST":

        return redirect(
            "request-detail",
            submission.pk,
        )

    remarks = request.POST.get(
        "remarks",
        "",
    )

    password = request.POST.get(
        "password",
    )

    user = authenticate(
        request,
        username=request.user.email,
        password=password,
    )

    if user is None:

        messages.error(
            request,
            "Incorrect password.",
        )

        return redirect(
            "request-detail",
            submission.pk,
        )

    WorkflowService.approve(
        step,
        request.user,
        remarks,
    )

    messages.success(
        request,
        "Request approved successfully.",
    )

    return redirect(
        "approval-inbox"
    )


# =========================================================
# REJECT REQUEST
# =========================================================

@login_required
@role_required(
    "MANAGER",
    "HR_HEAD",
    "IT_HEAD",
    "UNIT_HEAD",
    "ADMIN",
    "ORG_ADMIN",
    "SUPER_ADMIN",
)
def reject_request(request, pk):

    step = get_object_or_404(
        WorkflowStepInstance,
        pk=pk,
        assigned_to=request.user,
        status="PENDING",
    )

    submission = get_object_or_404(
        FormSubmission,
        workflow_instance=step.workflow_instance,
    )

    if request.method != "POST":

        return redirect(
            "request-detail",
            submission.pk,
        )

    remarks = request.POST.get(
        "remarks",
        "",
    )

    password = request.POST.get(
        "password",
    )

    if not remarks.strip():

        messages.error(
            request,
            "Reason is required.",
        )

        return redirect(
            "request-detail",
            submission.pk,
        )

    user = authenticate(
        request,
        username=request.user.email,
        password=password,
    )

    if user is None:

        messages.error(
            request,
            "Incorrect password.",
        )

        return redirect(
            "request-detail",
            submission.pk,
        )

    WorkflowService.reject(
        step,
        request.user,
        remarks,
    )

    messages.success(
        request,
        "Request rejected.",
    )

    return redirect(
        "approval-inbox"
    )


# =========================================================
# NEW REQUEST
# =========================================================

@login_required
def new_request(request):

    forms = (
        FormDefinition.objects
        .filter(
            is_published=True,
        )
        .order_by(
            "name",
        )
    )

    return render(
        request,
        "forms_engine/new_request.html",
        {
            "forms": forms,
        },
    )


# =========================================================
# GENERATE PERMISSION PDF
# =========================================================

@login_required
def permission_pdf(request, pk):

    submission = get_object_or_404(
        FormSubmission.objects.select_related(
            "submitted_by",
            "workflow_instance",
        ),
        pk=pk,
    )

    if submission.status != "APPROVED":

        return HttpResponseForbidden(
            "This permission has not been fully approved."
        )

    employee = (
        Employee.objects
        .filter(
            user=request.user,
        )
        .select_related(
            "role",
        )
        .first()
    )

    is_owner = (
        submission.submitted_by
        == request.user
    )

    is_authorized_staff = bool(
        employee
        and employee.role.code
        in [
            "HR_HEAD",
            "ADMIN",
            "ORG_ADMIN",
            "SUPER_ADMIN",
        ]
    )

    if not (
        is_owner
        or is_authorized_staff
    ):

        return HttpResponseForbidden(
            "Permission Denied"
        )

    pdf = generate_permission_pdf(
        submission
    )

    response = HttpResponse(
        pdf,
        content_type="application/pdf",
    )

    filename = (
        submission.permission_id
        or f"permission_{submission.pk}"
    )

    response[
        "Content-Disposition"
    ] = (
        f'inline; filename="{filename}.pdf"'
    )

    return response


# =========================================================
# PUBLIC PERMISSION VERIFICATION
# =========================================================

def verify_permission(request, token):

    submission = (
        FormSubmission.objects
        .select_related(
            "submitted_by",
            "form",
            "workflow_instance",
        )
        .filter(
            verification_token=token,
            status="APPROVED",
        )
        .first()
    )

    # Invalid token or permission
    if submission is None:

        return render(
            request,
            "forms_engine/verify_permission.html",
            {
                "verification_status": "INVALID",
                "submission": None,
                "values": {},
            },
        )

    # Convert stored form values into a dictionary
    values = {}

    for item in (
        submission.values
        .select_related(
            "field",
        )
        .all()
    ):

        values[
            item.field.field_name
        ] = item.value

    # Default status
    verification_status = "VALID"

    # -----------------------------------------
    # REVOKED CHECK
    # -----------------------------------------

    if submission.is_revoked:

        verification_status = "REVOKED"

    # -----------------------------------------
    # EXPIRY CHECK
    # -----------------------------------------

    elif values.get("to_date"):

        try:

            to_date = values.get(
                "to_date"
            )

            to_time = values.get(
                "to_time"
            )

            # Convert stored date string
            if isinstance(
                to_date,
                str,
            ):

                expiry_date = (
                    datetime
                    .fromisoformat(
                        to_date
                    )
                    .date()
                )

            else:

                expiry_date = to_date

            # Convert stored time string
            if to_time:

                if isinstance(
                    to_time,
                    str,
                ):

                    expiry_time = (
                        time.fromisoformat(
                            to_time
                        )
                    )

                else:

                    expiry_time = to_time

            else:

                expiry_time = time.max

            expiry_datetime = datetime.combine(
                expiry_date,
                expiry_time,
            )

            # Make datetime timezone aware
            if timezone.is_naive(
                expiry_datetime
            ):

                expiry_datetime = (
                    timezone.make_aware(
                        expiry_datetime
                    )
                )

            if (
                timezone.now()
                > expiry_datetime
            ):

                verification_status = (
                    "EXPIRED"
                )

        except (
            ValueError,
            TypeError,
        ):

            # Do not expose internal errors
            pass

    return render(
        request,
        "forms_engine/verify_permission.html",
        {
            "verification_status": verification_status,
            "submission": submission,
            "values": values,
        },
    )

@login_required
@role_required(
    "HR_HEAD",
    "ADMIN",
    "ORG_ADMIN",
    "SUPER_ADMIN",
)
def revoke_permission(request, pk):

    submission = get_object_or_404(
        FormSubmission,
        pk=pk,
        status="APPROVED",
    )

    # Already revoked
    if submission.is_revoked:
        messages.warning(
            request,
            "This permission has already been revoked.",
        )
        return redirect(
            "request-detail",
            submission.pk,
        )

    # Never allow revocation through GET
    if request.method != "POST":
        return redirect(
            "request-detail",
            submission.pk,
        )

    reason = request.POST.get(
        "reason",
        "",
    ).strip()

    password = request.POST.get(
        "password",
        "",
    )

    # Reason is mandatory
    if not reason:
        messages.error(
            request,
            "A revocation reason is required.",
        )
        return redirect(
            "request-detail",
            submission.pk,
        )

    # Re-authenticate the person revoking
    user = authenticate(
        request,
        username=request.user.email,
        password=password,
    )

    if user is None:
        messages.error(
            request,
            "Incorrect password.",
        )
        return redirect(
            "request-detail",
            submission.pk,
        )

    # Revoke permission
    submission.is_revoked = True
    submission.revoked_at = timezone.now()
    submission.revoked_by = request.user
    submission.revocation_reason = reason

    submission.save(
        update_fields=[
            "is_revoked",
            "revoked_at",
            "revoked_by",
            "revocation_reason",
        ]
    )

    submission.save(
        update_fields=[
            "is_revoked",
            "revoked_at",
            "revocation_reason",
        ]
    )

    messages.success(
        request,
        "Permission revoked successfully.",
    )

    return redirect(
        "request-detail",
        submission.pk,
    )
