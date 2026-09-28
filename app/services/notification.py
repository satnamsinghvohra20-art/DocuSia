from urllib.parse import quote

def sanitize_phone(phone: str) -> str:
    """Normalize Indian phone number to 91XXXXXXXXXX format for WhatsApp."""
    digits = "".join(filter(str.isdigit, phone or ""))
    if len(digits) == 10:
        return f"91{digits}"
    elif len(digits) == 12 and digits.startswith("91"):
        return digits
    elif len(digits) > 10:
        return digits[-10:] if not digits.startswith("91") else digits
    return digits


def get_whatsapp_urls(agreement, base_url: str = "http://127.0.0.1:8000") -> dict:
    """Generates ready-to-send WhatsApp Click-to-Chat deep links."""
    owner_phone = sanitize_phone(agreement.owner_mobile)
    tenant_phone = sanitize_phone(agreement.tenant_mobile)
    
    # 1. Draft Review Message to Owner
    owner_msg = (
        f"Namaste {agreement.owner_name} ji,\n\n"
        f"Your Maharashtra Leave & License Agreement draft ({agreement.agreement_no}) for the property at "
        f"*{agreement.property_address}* has been prepared by Dashmesh Properties.\n\n"
        f"📋 *Monthly Rent:* INR {agreement.rent:,} /-\n"
        f"🔒 *Security Deposit:* INR {agreement.deposit:,} /-\n"
        f"📅 *Period:* {agreement.start_date.strftime('%d-%b-%Y')} to {agreement.end_date.strftime('%d-%b-%Y')}\n\n"
        f"👉 View Draft & Status: {base_url}/agreements/{agreement.id}\n"
        f"📄 Download Legal PDF: {base_url}/agreements/{agreement.id}/pdf\n\n"
        f"Best regards,\nDashmesh Properties"
    )
    
    # 2. Draft Review Message to Tenant
    tenant_msg = (
        f"Hello {agreement.tenant_name},\n\n"
        f"Your Leave & License Agreement draft ({agreement.agreement_no}) for *{agreement.property_address}* "
        f"is ready for review.\n\n"
        f"📋 *Rent:* INR {agreement.rent:,} /-\n"
        f"🔒 *Deposit:* INR {agreement.deposit:,} /-\n"
        f"🏛️ *Govt Stamp Duty & Reg Fees:* INR {agreement.total_govt_fees:,} /-\n\n"
        f"👉 View Agreement: {base_url}/agreements/{agreement.id}\n"
        f"📄 Download Legal PDF: {base_url}/agreements/{agreement.id}/pdf\n\n"
        f"Dashmesh Properties Management"
    )

    # 3. Biometric Verification Alert
    bio_date_str = agreement.biometric_date or "To be scheduled"
    biometric_msg = (
        f"Important Update for Agreement {agreement.agreement_no}:\n\n"
        f"Doorstep biometric verification for {agreement.owner_name} & {agreement.tenant_name} is scheduled for:\n"
        f"🗓️ *{bio_date_str}*\n\n"
        f"Kindly keep your original Aadhaar and PAN cards available for biometric scanning.\n"
        f"Dashmesh Properties Compliance Desk"
    )

    # 4. Final Registered Index-II Notice
    index_msg = (
        f"🎉 Great News!\n\n"
        f"Your Leave & License Agreement *{agreement.agreement_no}* has been successfully registered with Maharashtra IGR.\n\n"
        f"📜 *Index-II Registration No:* {agreement.index_ii_no or 'Registered'}\n"
        f"Property: {agreement.property_address}\n\n"
        f"👉 Access your permanent records: {base_url}/agreements/{agreement.id}\n"
        f"Thank you for choosing Dashmesh Properties!"
    )

    return {
        "owner_review": f"https://wa.me/{owner_phone}?text={quote(owner_msg)}" if owner_phone else None,
        "tenant_review": f"https://wa.me/{tenant_phone}?text={quote(tenant_msg)}" if tenant_phone else None,
        "biometric_owner": f"https://wa.me/{owner_phone}?text={quote(biometric_msg)}" if owner_phone else None,
        "biometric_tenant": f"https://wa.me/{tenant_phone}?text={quote(biometric_msg)}" if tenant_phone else None,
        "index_owner": f"https://wa.me/{owner_phone}?text={quote(index_msg)}" if owner_phone else None,
        "index_tenant": f"https://wa.me/{tenant_phone}?text={quote(index_msg)}" if tenant_phone else None,
    }


def get_payment_whatsapp_url(payment, agreement, base_url: str = "http://127.0.0.1:8000") -> str | None:
    """Generates instant WhatsApp link with official rent receipt download."""
    tenant_phone = sanitize_phone(agreement.tenant_mobile)
    if not tenant_phone:
        return None
        
    msg = (
        f"Dear {agreement.tenant_name},\n\n"
        f"Your rent payment of *INR {payment.amount:,}* for *{payment.for_month_year}* has been successfully recorded.\n\n"
        f"🧾 *Receipt No:* {payment.receipt_no}\n"
        f"💳 *Mode:* {payment.payment_mode} (Ref: {payment.reference_no or 'Direct'})\n"
        f"🏠 *Property:* {agreement.property_address}\n\n"
        f"📥 Download Official HRA Exemption Receipt (PDF):\n"
        f"{base_url}/payments/{payment.id}/receipt\n\n"
        f"Dashmesh Properties"
    )
    return f"https://wa.me/{tenant_phone}?text={quote(msg)}"
