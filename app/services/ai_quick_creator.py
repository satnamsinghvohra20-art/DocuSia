import re
from datetime import date, datetime, timedelta
from pathlib import Path
from app.services.stamp_calculator import calculate_stamp_duty
from app.services.police_ai_service import ai_autofill_police_form, ai_process_submission
from app.services.police_ack_generator import build_police_ack_pdf
from app.services.police_form_generator import build_police_form_pdf
from app.services.pdf_generator import build_legal_pdf
from app.services.biometric_service import simulate_biometric_capture
from app.services.biometric_cert_generator import build_biometric_cert_pdf

def parse_quick_text(raw_text: str) -> dict:
    """
    Parses unstructured text, notes, or WhatsApp chats to extract key Leave & License entities.
    """
    text_lower = raw_text.lower()
    
    # 1. Rent extraction (e.g., "rent 25000", "rent: 25k", "25000/month", "rent is 22,000")
    rent = 25000
    rent_match = re.search(r'rent\s*[:=\-]?\s*(?:inr|rs\.?|₹)?\s*(\d{1,2}[,\d]{3,6}|\d{1,2}k)', text_lower)
    if not rent_match:
        rent_match = re.search(r'(?:inr|rs\.?|₹)\s*(\d{1,2}[,\d]{3,6})', text_lower)
    if rent_match:
        val = rent_match.group(1).replace(',', '')
        if val.endswith('k'):
            rent = int(float(val[:-1]) * 1000)
        else:
            try: rent = int(val)
            except ValueError: rent = 25000

    # 2. Deposit extraction (e.g., "deposit 60000", "dep: 50k", "deposit 1 lakh", "security 75,000")
    deposit = rent * 3
    dep_match = re.search(r'(?:deposit|dep|security)\s*[:=\-]?\s*(?:inr|rs\.?|₹)?\s*(\d{1,3}[,\d]{3,6}|\d{1,2}k|\d+(?:\.\d+)?\s*lakh)', text_lower)
    if dep_match:
        val = dep_match.group(1).replace(',', '').strip()
        if 'lakh' in val:
            num = float(re.findall(r'\d+(?:\.\d+)?', val)[0])
            deposit = int(num * 100000)
        elif val.endswith('k'):
            deposit = int(float(val[:-1]) * 1000)
        else:
            try: deposit = int(val)
            except ValueError: deposit = rent * 3

    # 3. Phone numbers (10 digits starting with 6-9)
    phones = re.findall(r'(?:(?:\+91|91|0)?[-\s]?)?([6-9]\d{9})\b', raw_text)
    owner_phone = phones[0] if len(phones) > 0 else "9822001122"
    tenant_phone = phones[1] if len(phones) > 1 else "9823334455"

    # 4. Names extraction
    # Look for "owner: Name", "landlord: Name", "licensor: Name"
    owner_name = "Satnam Singh"
    owner_match = re.search(r'(?:owner|landlord|licensor)\s*[:=\-]?\s*([A-Za-z\s\.\'\-]+?)(?:\n|,|;|\band\b|phone|mobile|\d{10}|$)', raw_text, re.IGNORECASE)
    if owner_match and len(owner_match.group(1).strip()) > 2:
        owner_name = owner_match.group(1).strip().title()

    tenant_name = "Rahul Sharma"
    tenant_match = re.search(r'(?:tenant|licensee|renter)\s*[:=\-]?\s*([A-Za-z\s\.\'\-]+?)(?:\n|,|;|\band\b|phone|mobile|\d{10}|$)', raw_text, re.IGNORECASE)
    if tenant_match and len(tenant_match.group(1).strip()) > 2:
        tenant_name = tenant_match.group(1).strip().title()

    # 5. Address extraction
    address = "Flat No. 402, B-Wing, Rohan Mithila, Viman Nagar, Pune - 411014"
    addr_match = re.search(r'(?:address|flat|property|premises|unit|house)\s*[:=\-]?\s*([^\n;]+)', raw_text, re.IGNORECASE)
    if addr_match and len(addr_match.group(1).strip()) > 8:
        candidate = addr_match.group(1).strip()
        candidate = re.split(r'\b(?:rent|deposit|tenant|owner|phone)\b', candidate, flags=re.IGNORECASE)[0].strip()
        if len(candidate) > 8:
            if not candidate.lower().startswith('flat') and not candidate.lower().startswith('house'):
                address = f"Flat {candidate}"
            else:
                address = candidate

    # 6. City inference
    city = "Pune"
    if "mumbai" in text_lower or "bandra" in text_lower or "andheri" in text_lower or "powai" in text_lower:
        city = "Mumbai"
    elif "thane" in text_lower or "ghodbunder" in text_lower:
        city = "Thane"
    elif "navi mumbai" in text_lower or "vashi" in text_lower:
        city = "Navi Mumbai"

    # 7. Start date (default: 1st of next month)
    today = date.today()
    if today.month == 12:
        start_date = date(today.year + 1, 1, 1)
    else:
        start_date = date(today.year, today.month + 1, 1)

    date_match = re.search(r'(?:from|start|date)\s*[:=\-]?\s*(\d{1,2})[/\-\s](?:([A-Za-z]{3,9})|(\d{1,2}))[/\-\s]?(\d{2,4})?', text_lower)
    if date_match:
        try:
            day = int(date_match.group(1))
            month_str = date_match.group(2)
            if month_str:
                month_map = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
                for m_k, m_v in month_map.items():
                    if m_k in month_str:
                        start_date = date(today.year if today.month <= m_v else today.year + 1, m_v, min(day, 28))
                        break
        except Exception:
            pass

    return {
        "owner_name": owner_name,
        "owner_mobile": owner_phone,
        "tenant_name": tenant_name,
        "tenant_mobile": tenant_phone,
        "property_address": address,
        "property_city": city,
        "rent": rent,
        "deposit": deposit,
        "start_date": start_date
    }


def create_full_automated_agreement(dbs, AgreementModel, DocumentModel, InventoryItemModel, AuditLogModel, storage_dir: Path, data: dict):
    """
    Zero-Friction AI Agreement Generator:
    Takes parsed data, fills in all statutory Maharashtra particulars,
    calculates stamp duty, generates agreement + inventory + police dossier + ack certificate!
    """
    now = datetime.now()
    year = now.year
    count = dbs.query(AgreementModel).count() + 1
    agreement_no = f"DP-L&L-{year}-{count:05d}"

    start_date = data.get("start_date", date.today())
    end_date = start_date + timedelta(days=334)

    rent = int(data.get("rent", 25000))
    deposit = int(data.get("deposit", 75000))
    property_city = data.get("property_city", "Pune")
    property_address = data.get("property_address", "Flat No. 402, B-Wing, Baner, Pune - 411045")

    stamp_res = calculate_stamp_duty(
        monthly_rent=rent,
        deposit=deposit,
        months=11,
        area_type="urban" if property_city.lower() in ["pune", "mumbai", "thane", "navi mumbai"] else "rural"
    )

    owner_name = data.get("owner_name", "Satnam Singh")
    owner_mobile = data.get("owner_mobile", "9822001122")
    tenant_name = data.get("tenant_name", "Rahul Sharma")
    tenant_mobile = data.get("tenant_mobile", "9823334455")

    owner_pan = data.get("owner_pan") or f"ABCPS{count:04d}D"
    owner_aadhaar = data.get("owner_aadhaar_last4") or "4521"
    tenant_pan = data.get("tenant_pan") or f"XYZPT{count:04d}E"
    tenant_aadhaar = data.get("tenant_aadhaar_last4") or "8912"

    a = AgreementModel(
        agreement_no=agreement_no,
        owner_name=owner_name,
        owner_mobile=owner_mobile,
        owner_pan=owner_pan,
        owner_aadhaar_last4=owner_aadhaar,
        tenant_name=tenant_name,
        tenant_mobile=tenant_mobile,
        tenant_pan=tenant_pan,
        tenant_aadhaar_last4=tenant_aadhaar,
        property_address=property_address,
        property_type="Residential Flat",
        property_city=property_city,
        pincode=data.get("pincode", "411045"),
        furnishing_status="Semi-Furnished",
        electricity_consumer_no=f"01584{count:05d}92",
        rent=rent,
        deposit=deposit,
        maintenance_charges=0,
        escalation_percent=5,
        start_date=start_date,
        end_date=end_date,
        notice_period="30 days",
        lock_in="None",
        purpose="Residential",
        special_terms="Society maintenance included in rent. 1-month advance notice required for early termination.",
        stamp_duty_amount=stamp_res["stamp_duty"],
        registration_fee=stamp_res["registration_fee"],
        total_govt_fees=stamp_res["total_govt_fees"],
        witness1_name="Amit Patil",
        witness1_phone="9822114477",
        witness2_name="Rohan Shinde",
        witness2_phone="9822335588",
        status="Active",
        registration_status="Not Started",
        police_status="Completed"
    )

    dbs.add(a)
    dbs.commit()
    dbs.refresh(a)

    # 1. Auto-Seed Schedule II Standard Inventory Items
    standard_inventory = [
        ("Living Room", "Ceiling Fan with Regulator", "2", "Good / Working", "Crompton High-Speed 1200mm"),
        ("Living Room", "LED Tube Light 20W", "2", "Good / Working", "Philips Warm White"),
        ("Kitchen", "Modular Kitchen Cabinets & S.S. Sink", "1 Set", "Good / Working", "Granite counter, clean sink"),
        ("Master Bedroom", "Ceiling Fan & LED Tube Light", "1 Each", "Good / Working", "Smooth operation"),
        ("Bathroom", "Instant Water Geyser 15L", "1", "Good / Working", "AO Smith Electric Geyser"),
        ("Entrance", "Main Door Keys & Society Access Fob", "2 Sets", "Brand New", "Original Godrej lock keys")
    ]
    for room, item_name, qty, cond, remarks in standard_inventory:
        item = InventoryItemModel(
            agreement_id=a.id,
            room=room,
            item_name=item_name,
            quantity=qty,
            condition=cond,
            remarks=remarks
        )
        dbs.add(item)

    # 2. Run AI Police Verification Autofill & Submission Pipeline
    enriched_police = ai_autofill_police_form(a)
    a.tenant_occupation = enriched_police.get("tenant_occupation")
    a.tenant_workplace_name = enriched_police.get("tenant_workplace_name")
    a.tenant_workplace_address = enriched_police.get("tenant_workplace_address")
    a.tenant_permanent_address = enriched_police.get("tenant_permanent_address")
    a.emergency_contact_name = enriched_police.get("emergency_contact_name")
    a.emergency_contact_phone = enriched_police.get("emergency_contact_phone")
    a.vehicle_details = enriched_police.get("vehicle_details")

    submission_res = ai_process_submission(a, enriched_police)
    a.police_token_no = submission_res["ack_token"]
    a.police_status = "Completed"

    # 3. Run UIDAI Biometric Capture Simulation & Attestation
    bio_res = simulate_biometric_capture(a)
    a.biometric_status = "Completed"
    a.biometric_token = bio_res["biometric_token"]
    a.biometric_device = bio_res["device_name"]
    a.biometric_quality_score = bio_res["owner_quality"]
    a.security_seal_hash = bio_res["security_seal"]
    a.biometric_date = bio_res["captured_at"]

    # 4. Generate Official PDFs
    legal_pdf = storage_dir / f"{a.agreement_no}_legal_draft.pdf"
    build_legal_pdf(a, legal_pdf)

    form_pdf = storage_dir / f"{a.agreement_no}_Police_Tenant_Verification_Form.pdf"
    build_police_form_pdf(a, form_pdf)

    ack_pdf = storage_dir / f"{a.agreement_no}_Police_Verification_Ack.pdf"
    build_police_ack_pdf(a, submission_res, ack_pdf)

    bio_pdf = storage_dir / f"{a.agreement_no}_Biometric_Verification_Certificate.pdf"
    build_biometric_cert_pdf(a, bio_res, bio_pdf)

    # 5. Save Documents in Vault
    doc_ack = DocumentModel(
        agreement_id=a.id,
        filename=f"{a.agreement_no}_Police_Verification_Ack.pdf",
        path=str(ack_pdf),
        doc_type="Police Verification Ack"
    )
    doc_legal = DocumentModel(
        agreement_id=a.id,
        filename=f"{a.agreement_no}_legal_draft.pdf",
        path=str(legal_pdf),
        doc_type="Agreement Draft"
    )
    doc_bio = DocumentModel(
        agreement_id=a.id,
        filename=f"{a.agreement_no}_Biometric_Verification_Certificate.pdf",
        path=str(bio_pdf),
        doc_type="Biometric Certificate"
    )
    dbs.add(doc_ack)
    dbs.add(doc_legal)
    dbs.add(doc_bio)

    # 5. Log Audit Trail
    log1 = AuditLogModel(
        agreement_id=a.id,
        action=f"AI 1-Prompt Agreement Created with Stamp Duty: INR {a.stamp_duty_amount:,}",
        actor="AI Smart Engine"
    )
    log2 = AuditLogModel(
        agreement_id=a.id,
        action=f"AI Auto-Submitted Police Verification: Token {a.police_token_no} (Station: {submission_res['police_station']})",
        actor="AI Police Desk"
    )
    dbs.add(log1)
    dbs.add(log2)

    dbs.commit()
    dbs.refresh(a)

    return a
