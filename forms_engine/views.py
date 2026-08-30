import os
from datetime import datetime, time
from django.db import transaction

from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden, FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from django.views.decorators.http import require_POST
from notifications.services import NotificationService

from employees.models import Employee
from employees.permissions import can_approve, role_required
from workflow.models.events import WorkflowEvent
from workflow.models.instances import WorkflowStepInstance
from workflow.services import WorkflowService

from .forms import DynamicForm
from .models import FormDefinition, FormSubmission, RequestAttachment, RequestComment
from .pdf_generator import generate_permission_pdf
from .services import FormEngineService
from .audit_service import AuditExportService
from .permissions import can_comment_on_request
from .validators import validate_attachment_security, sanitize_filename
from accounts.decorators import public_access
from django.core.exceptions import ValidationError


# =========================================================
# SUBMIT REQUEST
# =========================================================

@login_required
def submit_request(request, code):

    form_definition = get_object_or_404(
        FormDefinition.objects.filter(
            organization=request.tenant,
            is_published=True,
        ),
        code=code,
    )

    if request.method == "POST":

        form = DynamicForm(
            form_definition,
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            attachments = request.FILES.getlist('attachments')
            
            # Hardened attachment validation
            validation_error = None
            for f in attachments:
                try:
                    validate_attachment_security(f)
                except ValidationError as ve:
                    validation_error = str(ve.message if hasattr(ve, "message") else ve)
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
                        clean_name = sanitize_filename(f.name)
                        RequestAttachment.objects.create(
                            submission=submission,
                            file=f,
                            original_filename=clean_name,
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
        FormSubmission.objects.for_tenant(request.tenant)
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
            workflow_instance__organization=request.tenant,
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
            workflow_instance__organization=request.tenant,
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
    attachment = get_object_or_404(RequestAttachment.objects.filter(submission__organization=request.tenant), pk=pk)
    submission = attachment.submission
    
    if not can_view_request(request.user, submission):
        return HttpResponseForbidden("Permission Denied")
        
    return FileResponse(attachment.file, as_attachment=True, filename=attachment.original_filename)

@login_required
def request_detail(request, pk):

    submission = get_object_or_404(
        FormSubmission.objects.for_tenant(request.tenant).select_related(
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
    # INTERNAL NOTES & DISCUSSION
    # =====================================================

    can_comment = can_comment_on_request(request.user, submission)
    comments = (
        submission.comments
        .select_related("author")
        .all()
    )
    comment_author_ids = [c.author_id for c in comments]
    emp_map = {
        emp.user_id: emp
        for emp in Employee.objects.filter(user_id__in=comment_author_ids, organization=submission.organization).select_related("role", "designation", "department")
    }
    comments_list = []
    for c in comments:
        emp = emp_map.get(c.author_id)
        role_label = emp.role.name if (emp and emp.role) else ("Requester" if c.author_id == submission.submitted_by_id else "Staff")
        first = c.author.first_name or ""
        last = c.author.last_name or ""
        if first and last:
            initials = (first[0] + last[0]).upper()
        elif first:
            initials = first[:2].upper()
        else:
            initials = c.author.username[:2].upper()
            
        comments_list.append({
            "id": c.pk,
            "author": c.author,
            "author_name": c.author.get_full_name() or c.author.username or c.author.email,
            "role_label": role_label,
            "initials": initials,
            "message": c.message,
            "created_at": c.created_at,
            "is_requester": c.author_id == submission.submitted_by_id,
            "is_current_user": c.author_id == request.user.pk,
        })

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
            "comments": comments_list,
            "can_comment": can_comment,
        },
    )


# =========================================================
# ADD INTERNAL NOTE / COMMENT
# =========================================================

@login_required
@require_POST
def add_request_comment(request, pk):
    """
    Adds an internal note/discussion message to a request.
    Notifies the counterpart (approver if requester commented, or requester if approver commented).
    """
    submission = get_object_or_404(
        FormSubmission.objects.for_tenant(request.tenant).select_related(
            "workflow_instance",
            "submitted_by",
            "organization",
        ),
        pk=pk,
    )

    if not can_comment_on_request(request.user, submission):
        return HttpResponseForbidden("Permission Denied: You cannot comment on this request.")

    message = request.POST.get("message", "").strip()
    if not message:
        messages.error(request, "Note cannot be empty.")
        return redirect(f"/requests/{pk}/#discussion")

    if len(message) > 2000:
        messages.error(request, "Note exceeds maximum limit of 2000 characters.")
        return redirect(f"/requests/{pk}/#discussion")

    # Create RequestComment record (independent of WorkflowEvent)
    RequestComment.objects.create(
        submission=submission,
        author=request.user,
        message=message,
    )

    # Trigger notifications based on author role
    author_name = request.user.get_full_name() or request.user.username or request.user.email
    preview_msg = message if len(message) <= 100 else f"{message[:97]}..."

    # If approver/admin commented -> notify requester
    if request.user != submission.submitted_by:
        NotificationService.notify(
            recipient=submission.submitted_by,
            notification_type="COMMENT",
            title=f"New Note on {submission.form.name}",
            message=f"{author_name} left a note: \"{preview_msg}\"",
            workflow_instance=submission.workflow_instance,
        )
    # If requester commented/replied -> notify currently assigned approver
    else:
        if submission.workflow_instance:
            pending_step = (
                WorkflowStepInstance.objects
                .filter(workflow_instance=submission.workflow_instance, status="PENDING")
                .select_related("assigned_to")
                .first()
            )
            if pending_step and pending_step.assigned_to and pending_step.assigned_to != request.user:
                NotificationService.notify(
                    recipient=pending_step.assigned_to,
                    notification_type="COMMENT",
                    title=f"Requester Replied: {submission.form.name}",
                    message=f"{author_name} replied: \"{preview_msg}\"",
                    workflow_instance=submission.workflow_instance,
                )

    messages.success(request, "Internal note posted successfully.")
    return redirect(f"/requests/{pk}/#discussion")


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
        workflow_instance__organization=request.tenant,
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
        workflow_instance__organization=request.tenant,
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
        FormDefinition.objects.for_tenant(request.tenant)
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
        FormSubmission.objects.for_tenant(request.tenant).select_related(
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

@public_access
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

# =========================================================
# REQUEST TYPE MANAGEMENT
# =========================================================

from workflow.models import WorkflowDefinition, WorkflowVersion
from django.core.paginator import Paginator
from django.db.models import Q
from .forms import RequestTypeForm

@login_required
@role_required("ORG_ADMIN", "SUPER_ADMIN", "ADMIN", "HR_HEAD")
def request_type_list(request):
    query = request.GET.get("q", "")
    request_types = FormDefinition.objects.for_tenant(request.tenant).order_by("name")
    
    if query:
        request_types = request_types.filter(
            Q(name__icontains=query) | Q(code__icontains=query)
        )
        
    paginator = Paginator(request_types, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    return render(request, "forms_engine/request_type_list.html", {
        "page_obj": page_obj,
        "query": query,
    })

@login_required
@role_required("ORG_ADMIN", "SUPER_ADMIN", "ADMIN", "HR_HEAD")
def request_type_create(request):
    if request.method == "POST":
        form = RequestTypeForm(request.POST, tenant=request.tenant)
        if form.is_valid():
            with transaction.atomic():
                workflow_def = WorkflowDefinition.objects.create(
                    organization=request.tenant,
                    name=form.cleaned_data["name"],
                    code=form.cleaned_data["code"],
                    description=form.cleaned_data["description"]
                )
                
                workflow_version = WorkflowVersion.objects.create(
                    workflow=workflow_def,
                    version=1,
                    is_latest=True
                )
                
                form_def = form.save(commit=False)
                form_def.organization = request.tenant
                form_def.workflow = workflow_version
                form_def.is_published = False
                form_def.save()
                
            messages.success(request, "Basic information saved successfully.")
            return redirect("request-type-fields", pk=form_def.pk)
    else:
        form = RequestTypeForm(tenant=request.tenant)
        
    return render(request, "forms_engine/request_type_form.html", {
        "form": form,
        "title": "Create Request Type"
    })

@login_required
@role_required("ORG_ADMIN", "SUPER_ADMIN", "ADMIN", "HR_HEAD")
def request_type_summary(request, pk):
    request_type = get_object_or_404(FormDefinition.objects.for_tenant(request.tenant), pk=pk)
    
    return render(request, "forms_engine/request_type_summary.html", {
        "request_type": request_type,
        "fields_count": request_type.fields.count(),
        "steps_count": request_type.workflow.steps.count(),
    })

@login_required
@role_required("ORG_ADMIN", "SUPER_ADMIN", "ADMIN", "HR_HEAD")
def request_type_publish(request, pk):
    request_type = get_object_or_404(FormDefinition.objects.for_tenant(request.tenant), pk=pk)
    
    if request.method == "POST":
        if request_type.is_published:
            messages.error(request, "Request type is already published.")
            return redirect("request-type-list")
            
        if not request_type.fields.exists():
            messages.error(request, "Cannot publish request type without any fields.")
            return redirect("request-type-list")
            
        if not request_type.workflow.steps.exists():
            messages.error(request, "Cannot publish request type without any approval steps.")
            return redirect("request-type-list")
            
        request_type.is_published = True
        request_type.save(update_fields=["is_published"])
        messages.success(request, "Request type published successfully.")
        
    return redirect("request-type-list")

from .models import FormField
from .forms import FormFieldForm

@login_required
@role_required("ORG_ADMIN", "SUPER_ADMIN", "ADMIN", "HR_HEAD")
def request_type_fields(request, pk):
    request_type = get_object_or_404(FormDefinition.objects.for_tenant(request.tenant), pk=pk)
    fields = request_type.fields.all()
    return render(request, "forms_engine/request_type_fields.html", {
        "request_type": request_type,
        "fields": fields,
    })

@login_required
@role_required("ORG_ADMIN", "SUPER_ADMIN", "ADMIN", "HR_HEAD")
def request_type_field_add(request, pk):
    request_type = get_object_or_404(FormDefinition.objects.for_tenant(request.tenant), pk=pk)
    
    if request_type.is_published:
        messages.error(request, "Cannot add fields to a published request type.")
        return redirect("request-type-fields", pk=request_type.pk)

    if request.method == "POST":
        form = FormFieldForm(request.POST, form_definition=request_type)
        if form.is_valid():
            field = form.save(commit=False)
            field.form = request_type
            field.save()
            messages.success(request, "Field added successfully.")
            return redirect("request-type-fields", pk=request_type.pk)
    else:
        form = FormFieldForm(form_definition=request_type)

    return render(request, "forms_engine/request_type_field_form.html", {
        "request_type": request_type,
        "form": form,
        "title": "Add Field",
    })

@login_required
@role_required("ORG_ADMIN", "SUPER_ADMIN", "ADMIN", "HR_HEAD")
def request_type_field_edit(request, rt_pk, field_pk):
    request_type = get_object_or_404(FormDefinition.objects.for_tenant(request.tenant), pk=rt_pk)
    field = get_object_or_404(FormField, pk=field_pk, form=request_type)

    if request_type.is_published:
        messages.error(request, "Cannot edit fields of a published request type.")
        return redirect("request-type-fields", pk=request_type.pk)

    if request.method == "POST":
        form = FormFieldForm(request.POST, instance=field, form_definition=request_type)
        if form.is_valid():
            form.save()
            messages.success(request, "Field updated successfully.")
            return redirect("request-type-fields", pk=request_type.pk)
    else:
        form = FormFieldForm(instance=field, form_definition=request_type)

    return render(request, "forms_engine/request_type_field_form.html", {
        "request_type": request_type,
        "form": form,
        "title": "Edit Field",
    })

@login_required
@role_required("ORG_ADMIN", "SUPER_ADMIN", "ADMIN", "HR_HEAD")
def request_type_field_delete(request, rt_pk, field_pk):
    request_type = get_object_or_404(FormDefinition.objects.for_tenant(request.tenant), pk=rt_pk)
    field = get_object_or_404(FormField, pk=field_pk, form=request_type)

    if request_type.is_published:
        messages.error(request, "Cannot delete fields of a published request type.")
        return redirect("request-type-fields", pk=request_type.pk)

    if request.method == "POST":
        field.delete()
        messages.success(request, "Field deleted successfully.")
        
    return redirect("request-type-fields", pk=request_type.pk)

from workflow.models import WorkflowStepDefinition
from .forms import WorkflowStepForm

@login_required
@role_required("ORG_ADMIN", "SUPER_ADMIN", "ADMIN", "HR_HEAD")
def request_type_steps(request, pk):
    request_type = get_object_or_404(FormDefinition.objects.for_tenant(request.tenant), pk=pk)
    steps = request_type.workflow.steps.all()
    return render(request, "forms_engine/request_type_steps.html", {
        "request_type": request_type,
        "steps": steps,
    })

@login_required
@role_required("ORG_ADMIN", "SUPER_ADMIN", "ADMIN", "HR_HEAD")
def request_type_step_add(request, pk):
    request_type = get_object_or_404(FormDefinition.objects.for_tenant(request.tenant), pk=pk)
    
    if request_type.is_published:
        messages.error(request, "Cannot add steps to a published request type.")
        return redirect("request-type-steps", pk=request_type.pk)

    if request.method == "POST":
        form = WorkflowStepForm(request.POST, workflow_version=request_type.workflow, tenant=request.tenant)
        if form.is_valid():
            step = form.save(commit=False)
            step.workflow_version = request_type.workflow
            step.save()
            messages.success(request, "Step added successfully.")
            return redirect("request-type-steps", pk=request_type.pk)
    else:
        form = WorkflowStepForm(workflow_version=request_type.workflow, tenant=request.tenant)

    return render(request, "forms_engine/request_type_step_form.html", {
        "request_type": request_type,
        "form": form,
        "title": "Add Approval Step",
    })

@login_required
@role_required("ORG_ADMIN", "SUPER_ADMIN", "ADMIN", "HR_HEAD")
def request_type_step_edit(request, rt_pk, step_pk):
    request_type = get_object_or_404(FormDefinition.objects.for_tenant(request.tenant), pk=rt_pk)
    step = get_object_or_404(WorkflowStepDefinition, pk=step_pk, workflow_version=request_type.workflow)

    if request_type.is_published:
        messages.error(request, "Cannot edit steps of a published request type.")
        return redirect("request-type-steps", pk=request_type.pk)

    if request.method == "POST":
        form = WorkflowStepForm(request.POST, instance=step, workflow_version=request_type.workflow, tenant=request.tenant)
        if form.is_valid():
            form.save()
            messages.success(request, "Step updated successfully.")
            return redirect("request-type-steps", pk=request_type.pk)
    else:
        form = WorkflowStepForm(instance=step, workflow_version=request_type.workflow, tenant=request.tenant)

    return render(request, "forms_engine/request_type_step_form.html", {
        "request_type": request_type,
        "form": form,
        "title": "Edit Approval Step",
    })

@login_required
@role_required("ORG_ADMIN", "SUPER_ADMIN", "ADMIN", "HR_HEAD")
def request_type_step_delete(request, rt_pk, step_pk):
    request_type = get_object_or_404(FormDefinition.objects.for_tenant(request.tenant), pk=rt_pk)
    step = get_object_or_404(WorkflowStepDefinition, pk=step_pk, workflow_version=request_type.workflow)

    if request_type.is_published:
        messages.error(request, "Cannot delete steps of a published request type.")
        return redirect("request-type-steps", pk=request_type.pk)

    if request.method == "POST":
        step.delete()
        messages.success(request, "Step deleted successfully.")
        
    return redirect("request-type-steps", pk=request_type.pk)


# =========================================================
# AUDIT TRAIL & COMPLIANCE CSV EXPORT
# =========================================================

@login_required
@role_required("ORG_ADMIN", "SUPER_ADMIN", "ADMIN")
def export_audit_trail(request):
    """
    Exports a comprehensive activity audit trail CSV for the organization.
    """
    status_filter = request.GET.get("status")
    csv_data = AuditExportService.generate_organization_audit_csv(
        organization=request.tenant,
        status_filter=status_filter,
    )
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Anukram_Audit_Trail_{timestamp}.csv"

    response = HttpResponse(csv_data, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def export_approval_history_csv(request):
    """
    Exports the logged-in approver's personal decision history CSV.
    """
    status_filter = request.GET.get("status")
    csv_data = AuditExportService.generate_approver_history_csv(
        user=request.user,
        organization=request.tenant,
        status_filter=status_filter,
    )
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Anukram_Approval_History_{timestamp}.csv"

    response = HttpResponse(csv_data, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


