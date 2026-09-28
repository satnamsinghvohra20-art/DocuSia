from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from pathlib import Path
from datetime import datetime
from app.services.stamp_calculator import num_to_words_inr

def build_receipt_pdf(payment, agreement, out_path: Path) -> Path:
    """Generates an official Rent Receipt for HRA Exemption under Sec 10(13A)."""
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=45,
        rightMargin=45,
        topMargin=45,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'ReceiptTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        alignment=1,
        textColor=colors.HexColor('#0f172a')
    )

    sub_style = ParagraphStyle(
        'ReceiptSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        alignment=1,
        textColor=colors.HexColor('#b45309'),
        spaceAfter=15
    )

    meta_style = ParagraphStyle(
        'ReceiptMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )

    body_style = ParagraphStyle(
        'ReceiptBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=16,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=12
    )

    table_header = ParagraphStyle(
        'ReceiptTH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#0f172a')
    )

    table_cell = ParagraphStyle(
        'ReceiptTC',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#1e293b')
    )

    story = []

    # Header
    story.append(Paragraph("DASHMESH PROPERTIES", title_style))
    story.append(Paragraph("OFFICIAL RENT RECEIPT", ParagraphStyle('Sub', parent=title_style, fontSize=12, leading=15, textColor=colors.HexColor('#2563eb'))))
    story.append(Paragraph("VALID FOR HRA TAX EXEMPTION CLAIM UNDER SECTION 10(13A) OF THE INCOME TAX ACT, 1961", sub_style))

    # Top Meta Bar
    receipt_no = getattr(payment, 'receipt_no', f"REC-{payment.id:05d}")
    pay_date = payment.payment_date.strftime('%d-%b-%Y') if hasattr(payment.payment_date, 'strftime') else str(payment.payment_date)
    meta_table_data = [
        [
            Paragraph(f"<b>Receipt No:</b> {receipt_no}", meta_style),
            Paragraph(f"<b>Date:</b> {pay_date}", meta_style),
            Paragraph(f"<b>Agreement Ref:</b> {agreement.agreement_no}", meta_style)
        ]
    ]
    t_meta = Table(meta_table_data, colWidths=[170, 150, 185])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 15))

    # Core Receipt Paragraph
    amount_words = num_to_words_inr(payment.amount)
    body_text = (
        f"Received with thanks from <b>{agreement.tenant_name}</b> (Tenant / Licensee, Mobile: +91 {agreement.tenant_mobile}) "
        f"the sum of <b>INR {payment.amount:,} /-</b> (<i>{amount_words}</i>) by way of <b>{payment.payment_mode}</b> "
        f"(Transaction / Reference No: <b>{payment.reference_no or 'N/A'}</b>) towards the rent for the month of "
        f"<b>{payment.for_month_year}</b> for the residential premises located at:<br/><br/>"
        f"<b>{agreement.property_address}</b>"
    )
    story.append(Paragraph(body_text, body_style))
    story.append(Spacer(1, 10))

    # Landlord & Property Table
    landlord_pan = getattr(agreement, 'owner_pan', None) or 'Not Disclosed'
    tenant_pan = getattr(agreement, 'tenant_pan', None) or 'Not Disclosed'

    details_data = [
        [
            Paragraph("<b>Landlord / Licensor Name:</b>", table_header),
            Paragraph(f"{agreement.owner_name}", table_cell),
            Paragraph("<b>Landlord PAN:</b>", table_header),
            Paragraph(f"<b>{landlord_pan}</b>", table_cell)
        ],
        [
            Paragraph("<b>Tenant / Licensee Name:</b>", table_header),
            Paragraph(f"{agreement.tenant_name}", table_cell),
            Paragraph("<b>Tenant PAN:</b>", table_header),
            Paragraph(f"{tenant_pan}", table_cell)
        ],
        [
            Paragraph("<b>Payment Type:</b>", table_header),
            Paragraph(f"{payment.payment_type}", table_cell),
            Paragraph("<b>Rent Period:</b>", table_header),
            Paragraph(f"{payment.for_month_year}", table_cell)
        ],
        [
            Paragraph("<b>Payment Mode:</b>", table_header),
            Paragraph(f"{payment.payment_mode}", table_cell),
            Paragraph("<b>Ref / UTR No:</b>", table_header),
            Paragraph(f"{payment.reference_no or 'Direct Transfer'}", table_cell)
        ]
    ]
    t_details = Table(details_data, colWidths=[140, 160, 100, 105])
    t_details.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fafaf9')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_details)
    story.append(Spacer(1, 20))

    # Revenue stamp & Landlord Signature Box
    sign_data = [
        [
            Paragraph(
                "<font color='#94a3b8'>[ Affix INR 1 /- Revenue<br/>Stamp if payment made in<br/>Cash exceeding INR 5,000 ]</font>",
                ParagraphStyle('StampNote', parent=table_cell, alignment=1)
            ),
            Paragraph(
                f"<br/><br/><br/>________________________________________<br/>"
                f"<b>Signature of Landlord / Licensor</b><br/>"
                f"({agreement.owner_name})<br/>"
                f"PAN: {landlord_pan}",
                table_cell
            )
        ]
    ]
    t_sign = Table(sign_data, colWidths=[230, 275])
    t_sign.setStyle(TableStyle([
        ('BOX', (0,0), (0,0), 1, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#f8fafc')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(KeepTogether([t_sign]))
    story.append(Spacer(1, 20))

    # Footer note
    footer_note = (
        "<font size='7.5' color='#64748b'>"
        "Note: As per CBDT Circular No. 8/2013, quoting Landlord's PAN is mandatory if aggregate annual rent exceeds INR 1,00,000. "
        "This electronic receipt is generated by Dashmesh Properties Management System on behalf of the landlord/licensor."
        "</font>"
    )
    story.append(Paragraph(footer_note, styles['Normal']))

    doc.build(story)
    return out_path
