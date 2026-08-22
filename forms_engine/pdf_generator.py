from io import BytesIO

import qrcode

from django.conf import settings
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from employees.models import Employee


def generate_permission_pdf(submission):

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    elements = []

    # =====================================================
    # STYLES
    # =====================================================

    title_style = ParagraphStyle(
        "Title",
        fontName="Helvetica-Bold",
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        fontName="Helvetica-Bold",
        fontSize=11,
        alignment=TA_CENTER,
        spaceAfter=15,
    )

    normal_style = ParagraphStyle(
        "Normal",
        fontName="Helvetica",
        fontSize=9,
    )

    center_style = ParagraphStyle(
        "Center",
        fontName="Helvetica",
        fontSize=8,
        alignment=TA_CENTER,
    )

    bold_center_style = ParagraphStyle(
        "BoldCenter",
        fontName="Helvetica-Bold",
        fontSize=8,
        alignment=TA_CENTER,
    )

    verification_title_style = ParagraphStyle(
        "VerificationTitle",
        fontName="Helvetica-Bold",
        fontSize=9,
        alignment=TA_CENTER,
        spaceAfter=3,
    )

    # =====================================================
    # APPROVAL HISTORY
    # =====================================================

    if submission.workflow_instance:
        approved_steps = (
            submission.workflow_instance.steps
            .filter(status="APPROVED")
            .select_related(
                "assigned_to",
                "step_definition",
            )
            .order_by("created_at")
        )
        approvers = list(approved_steps)
    else:
        approvers = []

    # =====================================================
    # HELPER FUNCTIONS
    # =====================================================

    def approver_name(step):
        if not step or not step.assigned_to:
            return "-"
        return step.assigned_to.get_full_name() or step.assigned_to.email

    def approver_role(step):
        if not step:
            return "Approver"
        if step.assigned_to:
            employee = Employee.objects.filter(user=step.assigned_to).first()
            if employee and employee.role:
                return employee.role.display_name
        if step.step_definition:
            if step.step_definition.role_code:
                from rbac.models import Role
                return Role.get_display_name(step.step_definition.role_code)
            if step.step_definition.name:
                return step.step_definition.name
        return "Approver"

    def approval_time(step):
        if not step or not step.action_at:
            return ""
        local_time = timezone.localtime(step.action_at)
        return local_time.strftime("%d/%m/%Y %I:%M %p")

    def signature_image(step):
        if not step or not step.assigned_to:
            return Spacer(1, 18 * mm)

        employee = Employee.objects.filter(user=step.assigned_to).first()

        if employee and employee.digital_signature:
            try:
                return Image(
                    employee.digital_signature.path,
                    width=30 * mm,
                    height=12 * mm,
                )
            except Exception:
                pass

        return Paragraph("Digitally Approved", center_style)

    def generate_qr_code():
        if not submission.verification_token:
            return None

        base_url = settings.PUBLIC_BASE_URL.rstrip("/")
        verification_url = f"{base_url}/verify/{submission.verification_token}/"

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(verification_url)
        qr.make(fit=True)

        qr_image = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = BytesIO()
        qr_image.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)

        return qr_buffer

    # =====================================================
    # HEADING
    # =====================================================

    organization_name = submission.organization.name if submission.organization else "Unknown Organization"
    elements.append(Paragraph(organization_name, title_style))

    form_title = submission.form.name.upper() if submission.form else "REQUEST FORM"
    elements.append(Paragraph(form_title, subtitle_style))

    # =====================================================
    # REQUEST METADATA
    # =====================================================

    submitted_by = submission.submitted_by
    full_name = submitted_by.get_full_name() or submitted_by.email
    created_at = timezone.localtime(submission.created_at).strftime('%d/%m/%Y %I:%M %p')
    status_display = submission.get_status_display()
    req_id = submission.permission_id or str(submission.id)

    metadata_data = [
        [
            Paragraph("<b>Request ID:</b>", normal_style),
            Paragraph(req_id, normal_style),
            Paragraph("<b>Status:</b>", normal_style),
            Paragraph(status_display, normal_style),
        ],
        [
            Paragraph("<b>Requester:</b>", normal_style),
            Paragraph(full_name, normal_style),
            Paragraph("<b>Date Submitted:</b>", normal_style),
            Paragraph(created_at, normal_style),
        ],
    ]

    metadata_table = Table(metadata_data, colWidths=[25*mm, 60*mm, 30*mm, 55*mm])
    metadata_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    
    elements.append(metadata_table)
    elements.append(Spacer(1, 10))

    # =====================================================
    # DYNAMIC FORM FIELDS TABLE
    # =====================================================

    data = []
    
    for item in submission.values.select_related("field").order_by("field__order"):
        field_label = item.field.label
        raw_val = item.value
        
        # Format boolean values nicely
        if isinstance(raw_val, bool):
            display_val = "Yes" if raw_val else "No"
        elif isinstance(raw_val, list):
            display_val = ", ".join(str(v) for v in raw_val)
        else:
            display_val = str(raw_val) if raw_val is not None else "-"
            
        if not display_val.strip():
            display_val = "-"

        data.append([
            Paragraph(f"<b>{field_label}</b>", normal_style),
            Paragraph(display_val, normal_style)
        ])

    if not data:
        data = [[Paragraph("<i>No form data provided</i>", normal_style), ""]]

    details_table = Table(data, colWidths=[65 * mm, 105 * mm])
    details_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.7, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ])
    )

    elements.append(details_table)
    elements.append(Spacer(1, 10))

    # =====================================================
    # APPROVAL SECTION
    # =====================================================

    if approvers:
        # Determine column width based on number of approvers (max 170mm total)
        # If there are many approvers, we split them into chunks of 3
        chunk_size = 3
        approver_chunks = [approvers[i:i + chunk_size] for i in range(0, len(approvers), chunk_size)]
        
        elements.append(Paragraph("<b>Approval History:</b>", normal_style))
        elements.append(Spacer(1, 5))
        
        for chunk in approver_chunks:
            col_width = 170 * mm / len(chunk)
            
            approval_data = [
                [signature_image(step) for step in chunk],
                [Paragraph(approver_name(step), center_style) for step in chunk],
                [Paragraph(f"<b>{approver_role(step)}</b>", bold_center_style) for step in chunk],
                [Paragraph(approval_time(step), center_style) for step in chunk],
            ]

            approval_table = Table(approval_data, colWidths=[col_width] * len(chunk))
            approval_table.setStyle(
                TableStyle([
                    ("GRID", (0, 0), (-1, -1), 0.7, colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ])
            )
            elements.append(approval_table)
            elements.append(Spacer(1, 5))
            
    else:
        elements.append(Paragraph("<b>Approval History:</b> No approvals yet.", normal_style))
        elements.append(Spacer(1, 10))

    elements.append(Spacer(1, 10))

    # =====================================================
    # STAMP + QR VERIFICATION
    # =====================================================

    organization = submission.organization

    qr_buffer = generate_qr_code()
    if qr_buffer:
        qr_image = Image(qr_buffer, width=28 * mm, height=28 * mm)
    else:
        qr_image = Paragraph("Verification unavailable", center_style)

    # Organization stamp
    stamp_image = ""
    if organization and organization.official_stamp:
        try:
            stamp_image = Image(
                organization.official_stamp.path,
                width=28 * mm,
                height=28 * mm,
            )
        except Exception:
            pass

    permission_id = submission.permission_id or str(submission.id)

    verification_info = [
        Paragraph("<b>DOCUMENT VERIFICATION</b>", verification_title_style),
        Paragraph(
            (
                "Scan the QR code to verify "
                "this request against the "
                "live Anukram system."
            ),
            center_style,
        ),
        Spacer(1, 3),
        Paragraph(f"<b>Reference ID:</b><br/>{permission_id}", center_style),
    ]

    verification_table = Table(
        [
            [stamp_image, verification_info, qr_image],
        ],
        colWidths=[45 * mm, 80 * mm, 45 * mm],
        rowHeights=[36 * mm],
    )

    verification_table.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ])
    )

    elements.append(verification_table)
    elements.append(Spacer(1, 8))
    elements.append(
        Paragraph(
            (
                "<para alignment='center'>"
                "<b>Official Stamp</b>"
                "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
                "This document is electronically verifiable."
                "</para>"
            ),
            center_style,
        )
    )

    # =====================================================
    # GENERATE PDF
    # =====================================================

    document.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    return pdf
