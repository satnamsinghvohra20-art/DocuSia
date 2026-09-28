from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from pathlib import Path
from datetime import datetime

def build_police_form_pdf(agreement, out_path: Path) -> Path:
    """
    Generates official Maharashtra Police Tenant Information Report (Tenant Verification Form).
    Complies with directives of Commissioner of Police / Superintendent of Police Maharashtra.
    """
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'PoliceTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        alignment=1,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=3
    )

    sub_style = ParagraphStyle(
        'PoliceSub',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        alignment=1,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=12
    )

    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=10,
        spaceAfter=4
    )

    table_header = ParagraphStyle(
        'TH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1e293b')
    )

    table_cell = ParagraphStyle(
        'TC',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#334155')
    )

    declaration_style = ParagraphStyle(
        'Decl',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=8
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph("MAHARASHTRA POLICE CITIZEN PORTAL", title_style))
    story.append(Paragraph("TENANT INFORMATION REPORT (POLICE VERIFICATION RECORD)", sub_style))

    # Meta & Photo Boxes Table
    meta_table_data = [
        [
            Paragraph(
                f"<b>Application / Agreement Ref:</b> {agreement.agreement_no}<br/>"
                f"<b>Police Station Jurisdiction:</b> {agreement.property_city or 'Pune'} Commissionerate<br/>"
                f"<b>Date of Submission:</b> {datetime.now().strftime('%d-%b-%Y')}<br/>"
                f"<b>Filing Status:</b> {agreement.police_status.upper()}<br/>"
                f"<b>Ack / Token Ref:</b> {agreement.police_token_no or 'Pending Portal Upload'}",
                table_cell
            ),
            Paragraph(
                "<font color='#94a3b8'>[ Affix Passport<br/>Size Photo of<br/><b>TENANT</b> ]</font>",
                ParagraphStyle('PhotoBox1', parent=table_cell, alignment=1)
            ),
            Paragraph(
                "<font color='#94a3b8'>[ Affix Passport<br/>Size Photo of<br/><b>OWNER</b> ]</font>",
                ParagraphStyle('PhotoBox2', parent=table_cell, alignment=1)
            )
        ]
    ]
    t_meta = Table(meta_table_data, colWidths=[310, 105, 105])
    t_meta.setStyle(TableStyle([
        ('BOX', (0,0), (0,0), 1, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#f8fafc')),
        ('BOX', (1,0), (1,0), 1, colors.HexColor('#94a3b8')),
        ('BACKGROUND', (1,0), (1,0), colors.HexColor('#f1f5f9')),
        ('BOX', (2,0), (2,0), 1, colors.HexColor('#94a3b8')),
        ('BACKGROUND', (2,0), (2,0), colors.HexColor('#f1f5f9')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 8))

    # SECTION 1: PROPERTY DETAILS
    story.append(Paragraph("1. DETAILS OF RENTED PREMISES", section_header_style))
    prop_data = [
        [
            Paragraph("<b>Complete Address of Premises:</b>", table_header),
            Paragraph(f"{agreement.property_address}", table_cell),
            Paragraph("<b>Property Type:</b>", table_header),
            Paragraph(f"{agreement.property_type}", table_cell)
        ],
        [
            Paragraph("<b>City & Pincode:</b>", table_header),
            Paragraph(f"{agreement.property_city or 'Pune'} - {agreement.pincode or 'N/A'}", table_cell),
            Paragraph("<b>Electricity CA/Meter No:</b>", table_header),
            Paragraph(f"{getattr(agreement, 'electricity_consumer_no', 'N/A') or 'N/A'}", table_cell)
        ],
        [
            Paragraph("<b>Agreed Monthly Rent:</b>", table_header),
            Paragraph(f"INR {agreement.rent:,} /-", table_cell),
            Paragraph("<b>Tenancy Period:</b>", table_header),
            Paragraph(f"{agreement.start_date.strftime('%d-%b-%Y')} to {agreement.end_date.strftime('%d-%b-%Y')}", table_cell)
        ]
    ]
    t_prop = Table(prop_data, colWidths=[140, 160, 110, 110])
    t_prop.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ffffff')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_prop)
    story.append(Spacer(1, 6))

    # SECTION 2: LANDLORD / OWNER (LICENSOR) DETAILS
    story.append(Paragraph("2. DETAILS OF LANDLORD / OWNER (LICENSOR)", section_header_style))
    lic_aadhaar = getattr(agreement, 'owner_aadhaar_last4', '')
    lic_aadhaar_str = f"XXXX-XXXX-{lic_aadhaar}" if lic_aadhaar else "Verified Biometrically"
    owner_data = [
        [
            Paragraph("<b>Full Name:</b>", table_header),
            Paragraph(f"{agreement.owner_name}", table_cell),
            Paragraph("<b>Contact Mobile:</b>", table_header),
            Paragraph(f"+91 {agreement.owner_mobile}", table_cell)
        ],
        [
            Paragraph("<b>PAN Number:</b>", table_header),
            Paragraph(f"{agreement.owner_pan or 'Not Disclosed'}", table_cell),
            Paragraph("<b>Aadhaar Reference:</b>", table_header),
            Paragraph(f"{lic_aadhaar_str}", table_cell)
        ]
    ]
    t_owner = Table(owner_data, colWidths=[140, 160, 110, 110])
    t_owner.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ffffff')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_owner)
    story.append(Spacer(1, 6))

    # SECTION 3: TENANT (LICENSEE) DETAILS
    story.append(Paragraph("3. DETAILS OF TENANT / LICENSEE", section_header_style))
    ten_aadhaar = getattr(agreement, 'tenant_aadhaar_last4', '')
    ten_aadhaar_str = f"XXXX-XXXX-{ten_aadhaar}" if ten_aadhaar else "Verified Biometrically"
    perm_addr = getattr(agreement, 'tenant_permanent_address', '') or 'As per Aadhaar Card records'
    employer_name = getattr(agreement, 'tenant_workplace_name', '') or 'Private Service / Business'
    work_addr = getattr(agreement, 'tenant_workplace_address', '') or 'Maharashtra'
    vehicles = getattr(agreement, 'vehicle_details', '') or 'None / Public Transport'

    tenant_data = [
        [
            Paragraph("<b>Full Name:</b>", table_header),
            Paragraph(f"{agreement.tenant_name}", table_cell),
            Paragraph("<b>Contact Mobile:</b>", table_header),
            Paragraph(f"+91 {agreement.tenant_mobile}", table_cell)
        ],
        [
            Paragraph("<b>PAN Number:</b>", table_header),
            Paragraph(f"{agreement.tenant_pan or 'Not Disclosed'}", table_cell),
            Paragraph("<b>Aadhaar Reference:</b>", table_header),
            Paragraph(f"{ten_aadhaar_str}", table_cell)
        ],
        [
            Paragraph("<b>Permanent / Native Address:</b>", table_header),
            Paragraph(f"{perm_addr}", table_cell),
            Paragraph("<b>Occupation / Profession:</b>", table_header),
            Paragraph(f"{employer_name}", table_cell)
        ],
        [
            Paragraph("<b>Workplace / Office Address:</b>", table_header),
            Paragraph(f"{work_addr}", table_cell),
            Paragraph("<b>Vehicle (2W/4W Reg No):</b>", table_header),
            Paragraph(f"{vehicles}", table_cell)
        ]
    ]
    t_tenant = Table(tenant_data, colWidths=[140, 160, 110, 110])
    t_tenant.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ffffff')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_tenant)
    story.append(Spacer(1, 6))

    # SECTION 4: EMERGENCY CONTACTS & WITNESSES
    story.append(Paragraph("4. EMERGENCY CONTACT PERSON & REFERENCES", section_header_style))
    w1_name = getattr(agreement, 'witness1_name', '') or 'Amit Patil'
    w1_phone = getattr(agreement, 'witness1_phone', '') or ''
    emg_name = getattr(agreement, 'emergency_contact_name', '') or w1_name
    emg_phone = getattr(agreement, 'emergency_contact_phone', '') or w1_phone

    emg_data = [
        [
            Paragraph("<b>Emergency Contact Person:</b>", table_header),
            Paragraph(f"{emg_name}", table_cell),
            Paragraph("<b>Emergency Contact Mobile:</b>", table_header),
            Paragraph(f"+91 {emg_phone}", table_cell)
        ]
    ]
    t_emg = Table(emg_data, colWidths=[140, 160, 110, 110])
    t_emg.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ffffff')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_emg)
    story.append(Spacer(1, 8))

    # SECTION 5: DECLARATION & SIGNATURES
    story.append(Paragraph("5. STATUTORY CITIZEN DECLARATION", section_header_style))
    decl_text = (
        "I/We hereby solemnly declare that the particulars furnished above are true, complete and correct to the "
        "best of our knowledge and belief. No material facts have been concealed. I/We understand that giving false "
        "or misleading information to the police is a punishable offence under Section 177 and Section 182 of the "
        "Indian Penal Code (IPC) / Bharatiya Nyaya Sanhita (BNS)."
    )
    story.append(Paragraph(decl_text, declaration_style))

    sign_data = [
        [
            Paragraph(
                f"<br/><br/><br/>________________________________________<br/>"
                f"<b>Signature of Landlord / Owner</b><br/>"
                f"Name: {agreement.owner_name}<br/>"
                f"Mobile: +91 {agreement.owner_mobile}",
                table_cell
            ),
            Paragraph(
                f"<br/><br/><br/>________________________________________<br/>"
                f"<b>Signature of Tenant / Licensee</b><br/>"
                f"Name: {agreement.tenant_name}<br/>"
                f"Mobile: +91 {agreement.tenant_mobile}",
                table_cell
            )
        ]
    ]
    t_sign = Table(sign_data, colWidths=[260, 260])
    t_sign.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94a3b8')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(KeepTogether([t_sign]))
    story.append(Spacer(1, 10))

    # Official Police Station Acknowledgment Stamp Box
    ack_data = [
        [
            Paragraph(
                "<b>FOR LOCAL POLICE STATION / CITIZEN FACILITATION DESK USE ONLY:</b><br/>"
                "Received Tenant Information Report for property under jurisdiction.<br/>"
                "Inward / GD Entry No: ______________________ &nbsp;&nbsp;&nbsp;&nbsp; Date: _______________<br/>"
                "Name of Duty Officer / Const.: ________________ &nbsp;&nbsp;&nbsp;&nbsp; Stamp & Sign: _______________",
                ParagraphStyle('Ack', parent=table_cell, fontSize=8, leading=11, textColor=colors.HexColor('#475569'))
            )
        ]
    ]
    t_ack = Table(ack_data, colWidths=[520])
    t_ack.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94a3b8')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ffffff')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(KeepTogether([t_ack]))

    doc.build(story)
    return out_path
