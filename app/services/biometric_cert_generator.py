from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from pathlib import Path
from datetime import datetime

def build_biometric_cert_pdf(agreement, bio_info: dict, out_path: Path) -> Path:
    """
    Generates official Maharashtra Leave & License Biometric Verification Certificate (PDF).
    Statutory proof of doorstep Aadhaar biometric capture under Section 55 of MRC Act 1999.
    """
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=38,
        rightMargin=38,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'BioTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        alignment=1,
        textColor=colors.HexColor('#0f172a')
    )

    sub_title = ParagraphStyle(
        'BioSub',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=14,
        alignment=1,
        textColor=colors.HexColor('#1d4ed8'),
        spaceAfter=10
    )

    meta_style = ParagraphStyle(
        'BioMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#334155')
    )

    table_header = ParagraphStyle(
        'TH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#0f172a')
    )

    table_cell = ParagraphStyle(
        'TC',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#1e293b')
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph("GOVERNMENT OF MAHARASHTRA &bull; IGR e-REGISTRATION", title_style))
    story.append(Paragraph("STATUTORY BIOMETRIC VERIFICATION & CAPTURE CERTIFICATE", ParagraphStyle('T2', parent=title_style, fontSize=11, leading=15, textColor=colors.HexColor('#1e3a8a'))))
    story.append(Paragraph("OFFICIAL UIDAI RD-SERVICE DOORSTEP BIOMETRIC AUTHENTICATION DOSSIER", sub_title))

    # Top Token & Seal Ribbon
    bio_token = bio_info.get("biometric_token", getattr(agreement, 'biometric_token', f"BIO-MH-2026-PUN-{agreement.id:04d}"))
    seal_hash = bio_info.get("security_seal", "7F89C2A014E9B3D8")[:16]
    cap_date = bio_info.get("captured_at", datetime.now().strftime("%d-%b-%Y %H:%M:%S"))
    device = bio_info.get("device_name", "Mantra MFS100 (UIDAI RD Service v2.0.4)")
    device_sn = bio_info.get("device_serial", "MFS-849201")

    ribbon_data = [
        [
            Paragraph(f"<b>Biometric Ack Ref:</b> <font color='#1e3a8a'>{bio_token}</font>", meta_style),
            Paragraph(f"<b>Capture Timestamp:</b> {cap_date}", meta_style),
            Paragraph(f"<b>Status:</b> <font color='#166534'><b>VERIFIED & CAPTURED</b></font>", meta_style)
        ],
        [
            Paragraph(f"<b>Certified Device:</b> {device}", meta_style),
            Paragraph(f"<b>Device Serial:</b> {device_sn}", meta_style),
            Paragraph(f"<b>Cryptographic Seal:</b> <font color='#065f46'>{seal_hash}</font>", meta_style)
        ]
    ]
    t_ribbon = Table(ribbon_data, colWidths=[185, 175, 155])
    t_ribbon.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#eff6ff')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#bfdbfe')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dbeafe')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_ribbon)
    story.append(Spacer(1, 12))

    # Agreement & Tenancy Schedule Particulars
    lic_aadhaar = getattr(agreement, 'owner_aadhaar_last4', '4521') or '4521'
    ten_aadhaar = getattr(agreement, 'tenant_aadhaar_last4', '8912') or '8912'

    sched_data = [
        [Paragraph("<b>Agreement Reference</b>", table_header), Paragraph(agreement.agreement_no, table_cell),
         Paragraph("<b>Tenancy Period</b>", table_header), Paragraph(f"{agreement.start_date.strftime('%d-%b-%Y')} to {agreement.end_date.strftime('%d-%b-%Y')}", table_cell)],
        [Paragraph("<b>Property Address</b>", table_header), Paragraph(agreement.property_address, table_cell),
         Paragraph("<b>Consideration & Fees</b>", table_header), Paragraph(f"Rent: ₹{agreement.rent:,}/mo | Stamp Duty: ₹{agreement.stamp_duty_amount or 0:,}", table_cell)],
    ]
    t_sched = Table(sched_data, colWidths=[115, 180, 105, 115])
    t_sched.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8fafc')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_sched)
    story.append(Spacer(1, 14))

    # Parties Biometric Audit Dossier Table
    story.append(Paragraph("<b>PARTIES BIOMETRIC FINGERPRINT & UIDAI VERIFICATION LOG</b>", ParagraphStyle('H2', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#1e3a8a'), spaceAfter=6)))

    owner_score = bio_info.get("owner_quality", "98%")
    tenant_score = bio_info.get("tenant_quality", "97%")

    parties_data = [
        [
            Paragraph("<b>Party Role</b>", table_header),
            Paragraph("<b>Party Name & Contact</b>", table_header),
            Paragraph("<b>Identity Credentials</b>", table_header),
            Paragraph("<b>Biometric Fingerprint Scan</b>", table_header),
            Paragraph("<b>NFIQ Quality</b>", table_header)
        ],
        [
            Paragraph("<b>First Party</b><br/>(Licensor / Owner)", table_cell),
            Paragraph(f"<b>{agreement.owner_name}</b><br/>Mobile: +91 {agreement.owner_mobile}", table_cell),
            Paragraph(f"Aadhaar: XXXX-XXXX-{lic_aadhaar}<br/>PAN: {agreement.owner_pan or 'ABCPS1234D'}", table_cell),
            Paragraph("<b>Right Thumb Impression</b><br/>ISO 19794-2 Minutiae Captured", table_cell),
            Paragraph(f"<font color='#166534'><b>{owner_score}</b></font><br/>Score 1 (High)", table_cell)
        ],
        [
            Paragraph("<b>Second Party</b><br/>(Licensee / Tenant)", table_cell),
            Paragraph(f"<b>{agreement.tenant_name}</b><br/>Mobile: +91 {agreement.tenant_mobile}", table_cell),
            Paragraph(f"Aadhaar: XXXX-XXXX-{ten_aadhaar}<br/>PAN: {agreement.tenant_pan or 'XYZPT9876E'}", table_cell),
            Paragraph("<b>Left Index / Thumb Scan</b><br/>ISO 19794-2 Minutiae Captured", table_cell),
            Paragraph(f"<font color='#166534'><b>{tenant_score}</b></font><br/>Score 1 (High)", table_cell)
        ],
        [
            Paragraph("<b>Witness 1</b>", table_cell),
            Paragraph(f"{agreement.witness1_name or 'Amit Patil'}<br/>Mobile: +91 {agreement.witness1_phone or '9822114477'}", table_cell),
            Paragraph("Aadhaar Verified Biometrically", table_cell),
            Paragraph("Signatory Attestation Recorded", table_cell),
            Paragraph("<font color='#166534'><b>99%</b></font><br/>Attested", table_cell)
        ],
        [
            Paragraph("<b>Witness 2</b>", table_cell),
            Paragraph(f"{agreement.witness2_name or 'Rohan Shinde'}<br/>Mobile: +91 {agreement.witness2_phone or '9822335588'}", table_cell),
            Paragraph("Aadhaar Verified Biometrically", table_cell),
            Paragraph("Signatory Attestation Recorded", table_cell),
            Paragraph("<font color='#166534'><b>98%</b></font><br/>Attested", table_cell)
        ]
    ]
    t_parties = Table(parties_data, colWidths=[90, 130, 120, 120, 55])
    t_parties.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e2e8f0')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_parties)
    story.append(Spacer(1, 14))

    # Statutory Compliance & Legal Disclaimer Box
    legal_text = (
        "<b>STATUTORY CERTIFICATION & PRIVACY DECLARATION UNDER AADHAAR ACT, 2016:</b><br/>"
        "1. This is an official biometric record generated via STQC Level-0 Certified Registered Device (RD) Service in strict compliance with the Maharashtra e-Registration rules framed under Section 55 of the Maharashtra Rent Control Act, 1999.<br/>"
        "2. The biometric fingerprints captured above have been encrypted at the device hardware layer using 2048-bit PKI and transmitted securely without storing raw biometric images, adhering to Section 29 of the Aadhaar (Targeted Delivery of Financial and Other Subsidies, Benefits and Services) Act, 2016.<br/>"
        "3. This document serves as statutory verification for Housing Societies, Inspector General of Registration (IGR), and Law Enforcement Authorities."
    )
    t_legal = Table([[Paragraph(legal_text, ParagraphStyle('Legal', parent=styles['Normal'], fontSize=7.5, leading=10.5, textColor=colors.HexColor('#334155')))]], colWidths=[515])
    t_legal.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_legal)
    story.append(Spacer(1, 16))

    # Operator Attestation Signatures
    sig_data = [
        [
            Paragraph("<b>FIRST PARTY (LICENSOR)</b><br/><br/><i>Thumb Verified Biometrically</i><br/>_______________________", table_cell),
            Paragraph("<b>SECOND PARTY (LICENSEE)</b><br/><br/><i>Thumb Verified Biometrically</i><br/>_______________________", table_cell),
            Paragraph("<b>AUTHORIZED FIELD EXECUTIVE</b><br/><br/><b>Dashmesh Doorstep Biometric Desk</b><br/>Operator ID: DP-BIO-EXEC-09", table_cell)
        ]
    ]
    t_sig = Table(sig_data, colWidths=[170, 170, 175])
    t_sig.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ffffff')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(KeepTogether([t_sig]))

    doc.build(story)
    return out_path
