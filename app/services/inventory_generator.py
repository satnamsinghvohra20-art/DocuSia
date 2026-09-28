from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from pathlib import Path
from datetime import datetime

def build_inventory_pdf(agreement, items: list, out_path: Path) -> Path:
    """
    Generates official Schedule II: Property Inspection & Inventory Handover Report.
    Used for move-in and move-out possession sign-off between Licensor and Licensee.
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
        'InvTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        alignment=1,
        textColor=colors.HexColor('#0f172a')
    )

    sub_style = ParagraphStyle(
        'InvSub',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        alignment=1,
        textColor=colors.HexColor('#d97706'),
        spaceAfter=12
    )

    section_header_style = ParagraphStyle(
        'SecHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=10,
        spaceAfter=4
    )

    th_style = ParagraphStyle(
        'TH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#0f172a')
    )

    tc_style = ParagraphStyle(
        'TC',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#334155')
    )

    story = []

    # Title
    story.append(Paragraph("DASHMESH PROPERTIES", title_style))
    story.append(Paragraph("SCHEDULE II: PROPERTY INSPECTION & INVENTORY HANDOVER REPORT", sub_style))

    # Meta Box
    meta_data = [
        [
            Paragraph(f"<b>Agreement Ref:</b> {agreement.agreement_no}", tc_style),
            Paragraph(f"<b>Handover Date:</b> {agreement.start_date.strftime('%d-%b-%Y')}", tc_style),
            Paragraph(f"<b>Furnishing Status:</b> {agreement.furnishing_status or 'Semi-Furnished'}", tc_style)
        ],
        [
            Paragraph(f"<b>Licensor (Owner):</b> {agreement.owner_name} (+91 {agreement.owner_mobile})", tc_style),
            Paragraph(f"<b>Licensee (Tenant):</b> {agreement.tenant_name} (+91 {agreement.tenant_mobile})", tc_style),
            Paragraph(f"<b>City:</b> {agreement.property_city or 'Pune'}", tc_style)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[175, 205, 140])
    t_meta.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 8))

    # SECTION 1: UTILITY METER READINGS & KEY HANDOVER
    story.append(Paragraph("1. UTILITY METER READINGS & POSSESSION KEYS", section_header_style))
    elec_no = getattr(agreement, 'electricity_consumer_no', 'N/A') or 'N/A'
    meter_data = [
        [
            Paragraph("<b>Utility Meter</b>", th_style),
            Paragraph("<b>Consumer / Account No</b>", th_style),
            Paragraph("<b>Starting Reading at Possession</b>", th_style),
            Paragraph("<b>Remarks</b>", th_style)
        ],
        [
            Paragraph("Electricity (MSEDCL/Tata/Adani)", tc_style),
            Paragraph(f"{elec_no}", tc_style),
            Paragraph("Recorded on meter display", tc_style),
            Paragraph("Bill up to possession cleared by Licensor", tc_style)
        ],
        [
            Paragraph("Piped Gas (MGL / MNGL)", tc_style),
            Paragraph("Active Connection", tc_style),
            Paragraph("Initial Meter Units: _____ units", tc_style),
            Paragraph("Tenant pays ongoing consumption", tc_style)
        ],
        [
            Paragraph("Possession Keys Handover", tc_style),
            Paragraph("Main Door: 3 sets | Bedroom: 2 sets", tc_style),
            Paragraph("All keys tested and working", tc_style),
            Paragraph("To be returned in same count on vacate", tc_style)
        ]
    ]
    t_meter = Table(meter_data, colWidths=[140, 130, 120, 130])
    t_meter.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meter)
    story.append(Spacer(1, 8))

    # SECTION 2: FIXTURES, FITTINGS & INVENTORY MATRIX
    story.append(Paragraph("2. INVENTORY & CONDITION MATRIX (SCHEDULE II)", section_header_style))
    
    inv_rows = [
        [
            Paragraph("<b>#</b>", th_style),
            Paragraph("<b>Area / Room</b>", th_style),
            Paragraph("<b>Item Name & Description</b>", th_style),
            Paragraph("<b>Quantity</b>", th_style),
            Paragraph("<b>Move-In Condition</b>", th_style),
            Paragraph("<b>Remarks / Notes</b>", th_style)
        ]
    ]

    default_items = [
        ("Living Room", "Ceiling Fans (Havells / Crompton)", "2", "Working / Good", "Clean & operational"),
        ("Living Room", "LED Tube Lights / Warm Spotlights", "4", "Working / Good", "All fixtures tested"),
        ("Living Room", "Sofa Set (3+1+1) & Center Table", "1", "Good Condition", "Fabric upholstery intact"),
        ("Kitchen", "Modular Kitchen Cabinets & Trolleys", "1 Set", "Good Condition", "Smooth sliding runners"),
        ("Kitchen", "Kitchen Chimney & Exhaust Fan", "1", "Working / Clean", "Blower operational"),
        ("Master Bedroom", "1.5 Ton Split Inverter Air Conditioner", "1", "Working / Serviced", "Remote handed over"),
        ("Master Bedroom", "Double Bed with Mattress & Wardrobe", "1", "Good Condition", "3-door wooden wardrobe"),
        ("Bathrooms", "Storage Water Geyser (25 Litres)", "2", "Working / Clean", "Tested hot water flow"),
        ("Washroom / Balcony", "Curtain Rods & Window Mesh/Grills", "Complete", "Intact", "Safety grills installed")
    ]

    # Combine database items or fallback to standard checklist
    source_items = items if items else default_items
    
    for idx, it in enumerate(source_items, 1):
        if isinstance(it, tuple):
            room, item_name, qty, cond, rem = it
        else:
            room = getattr(it, 'room', 'General')
            item_name = getattr(it, 'item_name', 'Item')
            qty = str(getattr(it, 'quantity', 1))
            cond = getattr(it, 'condition', 'Good')
            rem = getattr(it, 'remarks', 'Inspected')
            
        inv_rows.append([
            Paragraph(str(idx), tc_style),
            Paragraph(room, tc_style),
            Paragraph(item_name, tc_style),
            Paragraph(qty, tc_style),
            Paragraph(f"<b>{cond}</b>", tc_style),
            Paragraph(rem, tc_style)
        ])

    t_inv = Table(inv_rows, colWidths=[20, 95, 165, 45, 95, 100])
    t_inv.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_inv)
    story.append(Spacer(1, 10))

    # SECTION 3: MUTUAL SIGN-OFF & POSSESSION ACKNOWLEDGMENT
    story.append(Paragraph("3. POSSESSION & CONDITION SIGN-OFF", section_header_style))
    ack_p = (
        "The Licensee confirms receipt of the licensed premises and all fixtures, fittings, appliances, and keys "
        "listed above in good, tenantable and working order on this date. The Licensee agrees to maintain the same "
        "diligently and return them in identical state upon termination of license, fair wear and tear excepted."
    )
    story.append(Paragraph(ack_p, ParagraphStyle('AckText', parent=tc_style, fontSize=8, leading=11, spaceAfter=8)))

    sign_data = [
        [
            Paragraph(
                f"<br/><br/><br/>________________________________________<br/>"
                f"<b>HANDED OVER BY (Licensor / Owner)</b><br/>"
                f"{agreement.owner_name} (+91 {agreement.owner_mobile})",
                tc_style
            ),
            Paragraph(
                f"<br/><br/><br/>________________________________________<br/>"
                f"<b>ACCEPTED & RECEIVED BY (Licensee / Tenant)</b><br/>"
                f"{agreement.tenant_name} (+91 {agreement.tenant_mobile})",
                tc_style
            )
        ]
    ]
    t_sign = Table(sign_data, colWidths=[260, 260])
    t_sign.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94a3b8')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(KeepTogether([t_sign]))

    doc.build(story)
    return out_path
