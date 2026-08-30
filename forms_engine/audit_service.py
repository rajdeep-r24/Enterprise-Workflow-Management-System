import csv
import io
from django.utils import timezone
from employees.models import Employee
from forms_engine.models import FormSubmission, FormSubmissionValue
from workflow.models.instances import WorkflowStepInstance


class AuditExportService:
    @staticmethod
    def generate_organization_audit_csv(organization, status_filter=None, from_date=None, to_date=None):
        """
        Generates an audit log CSV of all form submissions and approval chains
        for the given organization, formatted for compliance and activity reviews.
        Returns a UTF-8 encoded string with BOM for Excel compatibility.
        """
        output = io.StringIO()
        # Add UTF-8 BOM so Excel opens special characters and formatting correctly
        output.write("\ufeff")
        
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Header Row
        writer.writerow([
            "Submission ID",
            "Permission ID",
            "Request Type",
            "Status",
            "Requester Name",
            "Requester Email",
            "Requester Department",
            "Submitted At (UTC)",
            "Completed At (UTC)",
            "Issued At (UTC)",
            "Submitted Data Summary",
            "Approval Chain Audit Trail",
            "Attachments Count",
            "Verification Token",
            "Is Revoked",
        ])

        # Query all organization submissions
        queryset = (
            FormSubmission.objects.filter(organization=organization)
            .select_related(
                "form",
                "submitted_by",
                "workflow_instance",
                "workflow_instance__workflow_version",
                "workflow_instance__workflow_version__workflow",
                "workflow_instance__current_step",
            )
            .prefetch_related(
                "values",
                "values__field",
                "attachments",
                "workflow_instance__steps",
                "workflow_instance__steps__step_definition",
                "workflow_instance__steps__assigned_to",
                "workflow_instance__events",
                "workflow_instance__events__performed_by",
            )
            .order_by("-pk")
        )

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if from_date:
            queryset = queryset.filter(workflow_instance__submitted_at__gte=from_date)

        if to_date:
            queryset = queryset.filter(workflow_instance__submitted_at__lte=to_date)

        # Cache employee lookups for performance
        employee_map = {
            emp.user_id: emp
            for emp in Employee.objects.filter(organization=organization).select_related("department", "designation")
        }

        for sub in queryset:
            requester = sub.submitted_by
            emp = employee_map.get(requester.pk)
            req_name = requester.get_full_name() or requester.username or requester.email
            req_email = requester.email
            req_dept = emp.department.name if (emp and emp.department) else "General"

            # Form data summary
            form_data_items = []
            for val in sub.values.all():
                raw_val = val.value
                if isinstance(raw_val, list):
                    raw_val = ", ".join(str(v) for v in raw_val)
                form_data_items.append(f"{val.field.label}: {raw_val}")
            form_data_summary = " | ".join(form_data_items) if form_data_items else "-"

            # Approval Chain
            approval_chain_parts = []
            if sub.workflow_instance:
                steps = sorted(
                    sub.workflow_instance.steps.all(),
                    key=lambda s: s.step_definition.step_order if s.step_definition else s.pk,
                )
                for idx, step in enumerate(steps, start=1):
                    assigned_name = (
                        step.assigned_to.get_full_name() or step.assigned_to.email
                        if step.assigned_to
                        else "Unassigned"
                    )
                    action_time = (
                        step.action_at.strftime("%Y-%m-%d %H:%M:%S")
                        if step.action_at
                        else "Pending"
                    )
                    remarks_str = f' (Remarks: "{step.remarks}")' if step.remarks else ""
                    approval_chain_parts.append(
                        f"[Step {idx}: {step.step_definition.name} - {assigned_name} -> {step.status} at {action_time}{remarks_str}]"
                    )

            approval_chain_str = " -> ".join(approval_chain_parts) if approval_chain_parts else "No Workflow Steps"

            sub_date = (
                sub.workflow_instance.submitted_at.strftime("%Y-%m-%d %H:%M:%S")
                if (sub.workflow_instance and sub.workflow_instance.submitted_at)
                else "-"
            )
            comp_date = (
                sub.workflow_instance.completed_at.strftime("%Y-%m-%d %H:%M:%S")
                if (sub.workflow_instance and sub.workflow_instance.completed_at)
                else "-"
            )
            issued_date = sub.issued_at.strftime("%Y-%m-%d %H:%M:%S") if sub.issued_at else "-"

            writer.writerow([
                sub.pk,
                sub.permission_id or "-",
                sub.form.name,
                sub.status,
                req_name,
                req_email,
                req_dept,
                sub_date,
                comp_date,
                issued_date,
                form_data_summary,
                approval_chain_str,
                sub.attachments.count(),
                str(sub.verification_token) if sub.verification_token else "-",
                "Yes" if sub.is_revoked else "No",
            ])

        return output.getvalue()

    @staticmethod
    def generate_approver_history_csv(user, organization, status_filter=None):
        """
        Generates a personal approval decision history CSV for a manager/approver.
        Returns a UTF-8 encoded string with BOM for Excel compatibility.
        """
        output = io.StringIO()
        output.write("\ufeff")
        
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        writer.writerow([
            "Step Action ID",
            "Submission ID",
            "Permission ID",
            "Request Type",
            "Requester Name",
            "Requester Email",
            "Step Name",
            "Your Decision",
            "Your Remarks",
            "Action Timestamp (UTC)",
            "Overall Request Status",
        ])

        queryset = (
            WorkflowStepInstance.objects.filter(
                workflow_instance__organization=organization,
                assigned_to=user,
            )
            .exclude(status="PENDING")
            .select_related(
                "workflow_instance",
                "workflow_instance__initiated_by",
                "workflow_instance__formsubmission",
                "workflow_instance__formsubmission__form",
                "step_definition",
            )
            .order_by("-action_at", "-created_at")
        )

        if status_filter in ("APPROVED", "REJECTED"):
            queryset = queryset.filter(status=status_filter)

        for step in queryset:
            wf = step.workflow_instance
            sub = getattr(wf, "formsubmission", None)
            req_user = wf.initiated_by
            req_name = req_user.get_full_name() or req_user.username or req_user.email
            form_name = sub.form.name if sub else (wf.workflow_version.workflow.name if wf.workflow_version else "-")
            perm_id = sub.permission_id if (sub and sub.permission_id) else "-"
            sub_id = sub.pk if sub else "-"
            action_time = step.action_at.strftime("%Y-%m-%d %H:%M:%S") if step.action_at else "-"

            writer.writerow([
                step.pk,
                sub_id,
                perm_id,
                form_name,
                req_name,
                req_user.email,
                step.step_definition.name if step.step_definition else "-",
                step.status,
                step.remarks or "-",
                action_time,
                wf.status,
            ])

        return output.getvalue()
