from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas
from pathlib import Path
from datetime import datetime
from app.services.stamp_calculator import num_to_words_inr

class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print 'Page X of Y' in footer."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        w, h = A4
        # Header (pages after page 1)
        if self._pageNumber > 1:
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748b"))
            self.drawString(40, h - 30, "DASHMESH PROPERTIES — LEAVE & LICENSE AGREEMENT")
            self.drawRightString(w - 40, h - 30, f"Ref: {getattr(self, 'agreement_no', '')}")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(40, h - 34, w - 40, h - 34)

        # Footer
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(40, 38, w - 40, 38)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawString(40, 26, "Draft for Maharashtra IGR e-Registration | Dashmesh Properties Management System")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(w - 40, 26, page_str)
        self.restoreState()


def build_legal_pdf(a, out_path: Path) -> Path:
    """Generates an executive Maharashtra Leave & License Agreement PDF."""
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=45,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()
    
    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=1, # Center
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        alignment=1,
        textColor=colors.HexColor('#b45309'), # Amber/Gold
        spaceAfter=15
    )
    
    meta_style = ParagraphStyle(
        'MetaStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )
    
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=8
    )
    
    clause_title_style = ParagraphStyle(
        'ClauseTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=8,
        spaceAfter=3
    )
    
    alert_box_style = ParagraphStyle(
        'AlertBox',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#991b1b'),
        alignment=1
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#1e293b')
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#0f172a')
    )

    story = []

    # Title & Legal Headings
    story.append(Paragraph("LEAVE AND LICENSE AGREEMENT", title_style))
    story.append(Paragraph("UNDER SECTION 55 OF THE MAHARASHTRA RENT CONTROL ACT, 1999", subtitle_style))
    
    # Meta badge table
    meta_data = [
        [
            Paragraph(f"<b>Agreement Ref:</b> {a.agreement_no}", meta_style),
            Paragraph(f"<b>Date of Execution:</b> {datetime.now().strftime('%d-%b-%Y')}", meta_style),
            Paragraph(f"<b>Status:</b> {a.status.upper()}", meta_style)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[200, 180, 135])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 14))

    # Preamble
    preamble = (
        f"THIS AGREEMENT OF LEAVE AND LICENSE is made and entered into at Maharashtra, on this "
        f"<b>{datetime.now().strftime('%d')}</b> day of <b>{datetime.now().strftime('%B, %Y')}</b>, "
        f"BY AND BETWEEN:"
    )
    story.append(Paragraph(preamble, body_style))
    story.append(Spacer(1, 6))

    # Licensor & Licensee Box
    licensor_pan = getattr(a, 'owner_pan', None) or 'Not Specified'
    tenant_pan = getattr(a, 'tenant_pan', None) or 'Not Specified'
    licensor_aadhaar = getattr(a, 'owner_aadhaar_last4', None)
    tenant_aadhaar = getattr(a, 'tenant_aadhaar_last4', None)
    lic_aadhaar_str = f"XXXX-XXXX-{licensor_aadhaar}" if licensor_aadhaar else "Verified via Biometrics"
    ten_aadhaar_str = f"XXXX-XXXX-{tenant_aadhaar}" if tenant_aadhaar else "Verified via Biometrics"

    parties_data = [
        [
            Paragraph("<b>LICENSOR (Owner / First Party)</b>", table_header_style),
            Paragraph("<b>LICENSEE (Tenant / Second Party)</b>", table_header_style)
        ],
        [
            Paragraph(
                f"<b>Name:</b> {a.owner_name}<br/>"
                f"<b>Mobile:</b> +91 {a.owner_mobile}<br/>"
                f"<b>PAN:</b> {licensor_pan}<br/>"
                f"<b>Aadhaar Ref:</b> {lic_aadhaar_str}<br/>"
                f"Hereinafter referred to as the <b>'LICENSOR'</b> (which expression shall include legal heirs, executors, and assigns).",
                table_cell_style
            ),
            Paragraph(
                f"<b>Name:</b> {a.tenant_name}<br/>"
                f"<b>Mobile:</b> +91 {a.tenant_mobile}<br/>"
                f"<b>PAN:</b> {tenant_pan}<br/>"
                f"<b>Aadhaar Ref:</b> {ten_aadhaar_str}<br/>"
                f"Hereinafter referred to as the <b>'LICENSEE'</b> (which expression shall include legal heirs, executors, and assigns).",
                table_cell_style
            )
        ]
    ]
    t_parties = Table(parties_data, colWidths=[255, 260])
    t_parties.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#ffffff')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_parties)
    story.append(Spacer(1, 12))

    # Commercial Terms Summary Box
    rent_words = num_to_words_inr(a.rent)
    deposit_words = num_to_words_inr(a.deposit)
    stamp_duty_val = getattr(a, 'stamp_duty_amount', 0) or 0
    reg_fee_val = getattr(a, 'registration_fee', 0) or 1000

    terms_data = [
        [
            Paragraph("<b>Monthly License Fee:</b>", table_header_style),
            Paragraph(f"INR {a.rent:,} /- ({rent_words})", table_cell_style),
            Paragraph("<b>Period:</b>", table_header_style),
            Paragraph(f"{a.start_date.strftime('%d-%b-%Y')} to {a.end_date.strftime('%d-%b-%Y')}", table_cell_style)
        ],
        [
            Paragraph("<b>Security Deposit:</b>", table_header_style),
            Paragraph(f"INR {a.deposit:,} /- ({deposit_words})", table_cell_style),
            Paragraph("<b>Notice Period:</b>", table_header_style),
            Paragraph(f"{a.notice_period}", table_cell_style)
        ],
        [
            Paragraph("<b>Lock-in Period:</b>", table_header_style),
            Paragraph(f"{a.lock_in}", table_cell_style),
            Paragraph("<b>Permitted Use:</b>", table_header_style),
            Paragraph(f"{a.purpose}", table_cell_style)
        ],
        [
            Paragraph("<b>Stamp Duty:</b>", table_header_style),
            Paragraph(f"INR {stamp_duty_val:,} /-", table_cell_style),
            Paragraph("<b>Registration Fee:</b>", table_header_style),
            Paragraph(f"INR {reg_fee_val:,} /- (Urban Corp)", table_cell_style)
        ]
    ]
    t_terms = Table(terms_data, colWidths=[115, 150, 110, 140])
    t_terms.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fafaf9')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e7e5e4')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e7e5e4')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_terms)
    story.append(Spacer(1, 14))

    # Covenants and Conditions
    clauses = [
        ("1. Grant of License", 
         f"The Licensor hereby grants unto the Licensee the temporary, revocable leave and license to occupy and use "
         f"the residential premises described in Schedule I hereunder, purely for residential purposes and for no other purpose whatsoever."),
        
        ("2. Term & Tenure",
         f"The license is granted for a fixed period commencing from <b>{a.start_date.strftime('%d-%b-%Y')}</b> "
         f"and expiring on <b>{a.end_date.strftime('%d-%b-%Y')}</b>, subject to earlier termination as herein provided."),

        ("3. Monthly License Fee (Rent)",
         f"The Licensee covenants to pay to the Licensor a monthly license fee of <b>INR {a.rent:,}</b> "
         f"({rent_words}) on or before the 5th day of each calendar English month in advance via electronic bank transfer/UPI."),

        ("4. Interest-Free Refundable Security Deposit",
         f"The Licensee has deposited with the Licensor an interest-free refundable security deposit of <b>INR {a.deposit:,}</b> "
         f"({deposit_words}). The Licensor shall refund this security deposit to the Licensee upon peaceful, vacant handover of the premises, "
         f"subject to deductions for unpaid license fees, utility arrears, or repair costs for any physical damage beyond normal wear and tear."),

        ("5. Electricity, Water and Utility Charges",
         "The Licensee covenants to bear and punctually pay all monthly electricity bills, piped cooking gas (PNG/LPG), water charges, "
         "internet subscriptions, and other utility charges directly to the concerned utility service providers during the license term."),

        ("6. Society Maintenance & Taxes",
         "Regular society maintenance charges and municipal property taxes shall be borne and paid by the Licensor, unless otherwise mutually agreed."),

        ("7. Permitted Use & Conduct",
         f"The premises shall be used exclusively for <b>{a.purpose}</b> purposes by the Licensee and approved family members. "
         "The Licensee shall not commit any nuisance, illegal acts, or breach the by-laws of the housing society."),

        ("8. Prohibition on Sub-letting",
         "The Licensee shall strictly NOT sub-let, assign, transfer, or part with the possession of the licensed premises or any portion thereof to any third party."),

        ("9. Lock-in Period & Termination Notice",
         f"Both parties agree to a Lock-in period of <b>{a.lock_in}</b>. Subsequent to the lock-in period, either party may terminate "
         f"this agreement by serving a written notice of <b>{a.notice_period}</b> to the other party."),

        ("10. Inspection & Right of Entry",
         "The Licensor or authorized representatives shall have the right to inspect the licensed premises at reasonable daytime hours upon giving prior notice to the Licensee."),

        ("11. Handover on Expiry",
         "Upon expiry or earlier termination of the license, the Licensee shall immediately vacate and hand over quiet, vacant, and peaceful possession of the premises in good tenable condition."),

        ("12. Stamp Duty, Registration & Compliance",
         "Under Section 55 of the Maharashtra Rent Control Act, 1999, every tenancy agreement must be registered. "
         "Both parties covenant to provide necessary Aadhaar biometrics, identity documents, and signatures required for the official registration."),

        ("13. Tenant Police Information",
         "In compliance with directives issued by the Commissioner of Police / Superintendent of Police, Maharashtra, "
         "the tenant verification and information report shall be submitted to the local police station / Citizen Portal."),

        ("14. Special Terms & Conditions",
         a.special_terms if a.special_terms and a.special_terms.strip() else "None specified. Standard statutory Maharashtra covenants apply.")
    ]

    for c_title, c_text in clauses:
        story.append(Paragraph(c_title, clause_title_style))
        story.append(Paragraph(c_text, body_style))

    story.append(Spacer(1, 10))

    # Schedule I - Premises
    story.append(Paragraph("SCHEDULE I — LICENSED PREMISES", clause_title_style))
    furnishing = getattr(a, 'furnishing_status', 'Semi-Furnished') or 'Semi-Furnished'
    elec_no = getattr(a, 'electricity_consumer_no', 'Provided at Handover') or 'Provided at Handover'
    
    sched_data = [
        [
            Paragraph("<b>Property Address:</b>", table_header_style),
            Paragraph(f"{a.property_address}", table_cell_style)
        ],
        [
            Paragraph("<b>Property Type:</b>", table_header_style),
            Paragraph(f"{a.property_type}", table_cell_style)
        ],
        [
            Paragraph("<b>Furnishing Status:</b>", table_header_style),
            Paragraph(f"{furnishing}", table_cell_style)
        ],
        [
            Paragraph("<b>Electricity Consumer No:</b>", table_header_style),
            Paragraph(f"{elec_no}", table_cell_style)
        ]
    ]
    t_sched = Table(sched_data, colWidths=[160, 355])
    t_sched.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_sched)
    story.append(Spacer(1, 16))

    # Execution & Signature Block
    story.append(Paragraph("IN WITNESS WHEREOF the parties hereto have signed this agreement on the day and year first hereinabove written.", body_style))
    story.append(Spacer(1, 10))

    w1_name = getattr(a, 'witness1_name', '') or 'Witness 1'
    w1_phone = getattr(a, 'witness1_phone', '') or ''
    w2_name = getattr(a, 'witness2_name', '') or 'Witness 2'
    w2_phone = getattr(a, 'witness2_phone', '') or ''

    sign_data = [
        [
            Paragraph("<b>SIGNED AND DELIVERED</b> by Licensor:<br/><br/><br/>_______________________________<br/><b>" + a.owner_name + "</b><br/>Licensor (Owner)", table_cell_style),
            Paragraph("<b>SIGNED AND DELIVERED</b> by Licensee:<br/><br/><br/>_______________________________<br/><b>" + a.tenant_name + "</b><br/>Licensee (Tenant)", table_cell_style)
        ],
        [
            Paragraph("<b>IN THE PRESENCE OF WITNESS 1:</b><br/><br/><br/>_______________________________<br/><b>Name:</b> " + w1_name + "<br/><b>Mobile:</b> " + w1_phone, table_cell_style),
            Paragraph("<b>IN THE PRESENCE OF WITNESS 2:</b><br/><br/><br/>_______________________________<br/><b>Name:</b> " + w2_name + "<br/><b>Mobile:</b> " + w2_phone, table_cell_style)
        ]
    ]
    t_sign = Table(sign_data, colWidths=[255, 260])
    t_sign.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94a3b8')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(KeepTogether([t_sign]))
    story.append(Spacer(1, 15))

    # Disclaimer Alert Footer Box
    alert_text = (
        "<b>LEGAL NOTICE & STATUTORY DISCLAIMER:</b> This draft is prepared through the Dashmesh Properties "
        "Management Portal for execution and filing. Registration of Leave & License agreements is mandatory under "
        "Section 55 of Maharashtra Rent Control Act, 1999. Final legal validity requires payment of Stamp Duty and "
        "registration via the IGR Maharashtra e-Registration / Sub-Registrar Office."
    )
    t_alert = Table([[Paragraph(alert_text, alert_box_style)]], colWidths=[515])
    t_alert.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fef2f2')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#fca5a5')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(KeepTogether([t_alert]))

    # Set canvas custom attribute for header
    def on_first_page(canvas_obj, doc_obj):
        canvas_obj.agreement_no = a.agreement_no

    doc.build(story, canvasmaker=NumberedCanvas, onFirstPage=on_first_page, onLaterPages=on_first_page)
    return out_path
