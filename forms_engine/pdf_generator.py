from io import BytesIO

import qrcode

from django.conf import settings
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
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
        fontSize=9,
        alignment=TA_CENTER,
        spaceAfter=10,
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
    # FORM VALUES
    # =====================================================

    values = {}

    for item in submission.values.select_related("field").all():
        values[item.field.field_name] = item.value

    # =====================================================
    # APPROVAL HISTORY
    # =====================================================

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

    first_approver = (
        approvers[0]
        if len(approvers) > 0
        else None
    )

    hr_approver = (
        approvers[1]
        if len(approvers) > 1
        else None
    )

    unit_approver = (
        approvers[2]
        if len(approvers) > 2
        else None
    )

    # =====================================================
    # HELPER FUNCTIONS
    # =====================================================

    def checkbox(selected):

        box = Table(
            [
                [
                    "X"
                    if selected
                    else ""
                ]
            ],
            colWidths=[
                5 * mm
            ],
            rowHeights=[
                5 * mm
            ],
        )

        box.setStyle(
            TableStyle([
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    1,
                    colors.black,
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, -1),
                    "Helvetica-Bold",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
            ])
        )

        return box


    def checkbox_option(
        label,
        selected,
    ):

        return Table(
            [
                [
                    checkbox(selected),
                    Paragraph(
                        label,
                        normal_style,
                    ),
                ]
            ],
            colWidths=[
                7 * mm,
                30 * mm,
            ],
        )


    def approver_name(step):

        if (
            not step
            or not step.assigned_to
        ):
            return "-"

        return (
            step.assigned_to.get_full_name()
            or step.assigned_to.email
        )


    def approval_time(step):

        if (
            not step
            or not step.action_at
        ):
            return ""

        local_time = timezone.localtime(
            step.action_at
        )

        return local_time.strftime(
            "%d/%m/%Y %I:%M %p"
        )


    def signature_image(step):

        if (
            not step
            or not step.assigned_to
        ):

            return Spacer(
                1,
                18 * mm,
            )

        employee = (
            Employee.objects
            .filter(
                user=step.assigned_to
            )
            .first()
        )

        if (
            employee
            and employee.digital_signature
        ):

            try:

                return Image(
                    employee.digital_signature.path,
                    width=30 * mm,
                    height=12 * mm,
                )

            except Exception:
                pass

        return Paragraph(
            "Digitally Approved",
            center_style,
        )


    def generate_qr_code():

        if not submission.verification_token:
            return None

        base_url = settings.PUBLIC_BASE_URL.rstrip("/")

        verification_url = (
            f"{base_url}"
            f"/verify/"
            f"{submission.verification_token}/"
        )

        qr = qrcode.QRCode(
            version=None,
            error_correction=(
                qrcode.constants.ERROR_CORRECT_H
            ),
            box_size=10,
            border=4,
        )

        qr.add_data(
            verification_url
        )

        qr.make(
            fit=True
        )

        qr_image = qr.make_image(
            fill_color="black",
            back_color="white",
        )

        qr_buffer = BytesIO()

        qr_image.save(
            qr_buffer,
            format="PNG",
        )

        qr_buffer.seek(0)

        return qr_buffer


    # =====================================================
    # HEADING
    # =====================================================

    elements.append(
        Paragraph(
            "Ipca Laboratories Ltd. Athal",
            title_style,
        )
    )

    elements.append(
        Paragraph(
            "PERMISSION FOR CAMERA, LAPTOP AND MOBILE PHONES",
            subtitle_style,
        )
    )

    created_at = timezone.localtime(
        submission.created_at
    )

    elements.append(
        Paragraph(
            (
                "<b>Date:</b> "
                f"{created_at.strftime('%d/%m/%Y')}"
            ),
            normal_style,
        )
    )

    elements.append(
        Spacer(
            1,
            6,
        )
    )

    # =====================================================
    # USER DETAILS
    # =====================================================

    submitted_by = submission.submitted_by

    full_name = (
        submitted_by.get_full_name()
        or submitted_by.email
    )

    user_type = getattr(
        submitted_by,
        "user_type",
        "EMPLOYEE",
    )

    # =====================================================
    # EMPLOYEE / VISITOR
    # =====================================================

    person_type = Table(
        [
            [
                checkbox_option(
                    "Company Employee",
                    user_type == "EMPLOYEE",
                ),

                checkbox_option(
                    "Visitor",
                    user_type == "GUEST",
                ),
            ]
        ],
        colWidths=[
            58 * mm,
            50 * mm,
        ],
    )

    # =====================================================
    # PERMISSION TYPE
    # =====================================================

    permission_for = Table(
        [
            [
                checkbox_option(
                    "Camera",
                    bool(
                        values.get(
                            "camera"
                        )
                    ),
                ),

                checkbox_option(
                    "Laptop",
                    bool(
                        values.get(
                            "laptop"
                        )
                    ),
                ),

                checkbox_option(
                    "Mobile Phone",
                    bool(
                        values.get(
                            "mobile_phone"
                        )
                    ),
                ),
            ]
        ],
        colWidths=[
            38 * mm,
            38 * mm,
            45 * mm,
        ],
    )

    # =====================================================
    # MAIN DETAILS TABLE
    # =====================================================

    data = [

        [
            Paragraph(
                "<b>Name of Person</b>",
                normal_style,
            ),
            full_name,
        ],

        [
            Paragraph(
                "<b>Company Employee / Visitor</b>",
                normal_style,
            ),
            person_type,
        ],

        [
            Paragraph(
                "<b>Permission required for</b>",
                normal_style,
            ),
            permission_for,
        ],

        [
            Paragraph(
                "<b>Purpose of use</b>",
                normal_style,
            ),
            values.get(
                "purpose",
                "-",
            ),
        ],

        [
            Paragraph(
                "<b>Department / Area of use</b>",
                normal_style,
            ),
            values.get(
                "department",
                "-",
            ),
        ],

        [
            Paragraph(
                "<b>From Date</b>",
                normal_style,
            ),
            values.get(
                "from_date",
                "-",
            ),
        ],

        [
            Paragraph(
                "<b>From Time</b>",
                normal_style,
            ),
            values.get(
                "from_time",
                "-",
            ),
        ],

        [
            Paragraph(
                "<b>To Date</b>",
                normal_style,
            ),
            values.get(
                "to_date",
                "-",
            ),
        ],

        [
            Paragraph(
                "<b>To Time</b>",
                normal_style,
            ),
            values.get(
                "to_time",
                "-",
            ),
        ],
    ]

    details_table = Table(
        data,
        colWidths=[
            55 * mm,
            115 * mm,
        ],
    )

    details_table.setStyle(
        TableStyle([
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.7,
                colors.black,
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE",
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                6,
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                6,
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                7,
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                7,
            ),
        ])
    )

    elements.append(
        details_table
    )

    elements.append(
        Spacer(
            1,
            10,
        )
    )

    # =====================================================
    # APPROVAL SECTION
    # =====================================================

    approval_data = [

        [
            Paragraph(
                "<b>Approved by:</b>",
                normal_style,
            ),
            "",
            "",
        ],

        [
            signature_image(
                first_approver
            ),

            signature_image(
                hr_approver
            ),

            signature_image(
                unit_approver
            ),
        ],

        [
            Paragraph(
                approver_name(
                    first_approver
                ),
                center_style,
            ),

            Paragraph(
                approver_name(
                    hr_approver
                ),
                center_style,
            ),

            Paragraph(
                approver_name(
                    unit_approver
                ),
                center_style,
            ),
        ],

        [
            Paragraph(
                "<b>Department Head</b>",
                bold_center_style,
            ),

            Paragraph(
                "<b>HR Head</b>",
                bold_center_style,
            ),

            Paragraph(
                "<b>Unit Head</b>",
                bold_center_style,
            ),
        ],

        [
            Paragraph(
                approval_time(
                    first_approver
                ),
                center_style,
            ),

            Paragraph(
                approval_time(
                    hr_approver
                ),
                center_style,
            ),

            Paragraph(
                approval_time(
                    unit_approver
                ),
                center_style,
            ),
        ],
    ]

    approval_table = Table(
        approval_data,
        colWidths=[
            56 * mm,
            56 * mm,
            56 * mm,
        ],
    )

    approval_table.setStyle(
        TableStyle([
            (
                "SPAN",
                (0, 0),
                (-1, 0),
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.7,
                colors.black,
            ),
            (
                "ALIGN",
                (0, 1),
                (-1, -1),
                "CENTER",
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE",
            ),
            (
                "TOPPADDING",
                (0, 1),
                (-1, -1),
                5,
            ),
            (
                "BOTTOMPADDING",
                (0, 1),
                (-1, -1),
                5,
            ),
        ])
    )

    elements.append(
        approval_table
    )

    # =====================================================
    # STAMP + QR VERIFICATION
    # =====================================================

    organization = (
        submission.form.organization
    )

    qr_buffer = generate_qr_code()

    # QR image
    if qr_buffer:

        qr_image = Image(
            qr_buffer,
            width=28 * mm,
            height=28 * mm,
        )

    else:

        qr_image = Paragraph(
            "Verification unavailable",
            center_style,
        )

    # Organization stamp
    if organization.official_stamp:

        try:

            stamp_image = Image(
                organization.official_stamp.path,
                width=28 * mm,
                height=28 * mm,
            )

        except Exception:

            stamp_image = ""

    else:

        stamp_image = ""

    permission_id = (
        submission.permission_id
        or "-"
    )

    verification_info = [

        Paragraph(
            "<b>DOCUMENT VERIFICATION</b>",
            verification_title_style,
        ),

        Paragraph(
            (
                "Scan the QR code to verify "
                "this permission against the "
                "live ForgeFlow system."
            ),
            center_style,
        ),

        Spacer(
            1,
            3,
        ),

        Paragraph(
            (
                "<b>Permission ID:</b><br/>"
                f"{permission_id}"
            ),
            center_style,
        ),

    ]

    verification_table = Table(
        [
            [
                stamp_image,

                verification_info,

                qr_image,
            ],
        ],
        colWidths=[
            45 * mm,
            80 * mm,
            45 * mm,
        ],
        rowHeights=[
            36 * mm,
        ],
    )

    verification_table.setStyle(
        TableStyle([
            (
                "BOX",
                (0, 0),
                (-1, -1),
                0.7,
                colors.black,
            ),
            (
                "INNERGRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.black,
            ),
            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER",
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE",
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                5,
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                5,
            ),
        ])
    )

    elements.append(
        Spacer(
            1,
            8,
        )
    )

    elements.append(
        verification_table
    )

    elements.append(
        Spacer(
            1,
            3,
        )
    )

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

    document.build(
        elements
    )

    pdf = buffer.getvalue()

    buffer.close()

    return pdf
