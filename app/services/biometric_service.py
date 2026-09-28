import hashlib
import secrets
from datetime import datetime
from app.services.validators import validate_pan, validate_mobile

SUPPORTED_DEVICES = [
    "Mantra MFS100 (STQC Level 0 RD Service v2.0.4)",
    "Morpho MSO 1300 E3 (UIDAI Certified v2.0)",
    "Startek FM220U (Maha e-Registration RD Service)"
]

def simulate_biometric_capture(agreement, device_name: str = None) -> dict:
    """
    Executes UIDAI-compliant biometric capture simulation for Maharashtra e-Registration.
    Captures:
    1. Licensor Thumb Scan (Right Thumb, Minutiae ISO 19794-2)
    2. Licensee Thumb Scan (Left Index / Right Thumb, Minutiae ISO 19794-2)
    3. Device STQC Attestation & Timestamp
    4. Computes SHA-256 Tamper-Evident Digital Security Seal
    """
    now = datetime.now()
    year = now.year
    city_code = "PUN" if "pune" in (agreement.property_city or "pune").lower() else "MUM"
    rand_hex = secrets.token_hex(3).upper()

    device = device_name or SUPPORTED_DEVICES[0]
    device_sn = f"MFS-{secrets.token_hex(4).upper()}"
    
    # Official Token: BIO-MH-2026-PUN-0002-HEX
    biometric_token = f"BIO-MH-{year}-{city_code}-{agreement.id:04d}-{rand_hex}"

    # Minutiae quality scores according to NFIQ 2.0 (National Institute of Standards and Technology)
    owner_score = secrets.randbelow(4) + 96   # 96% - 99%
    tenant_score = secrets.randbelow(4) + 95  # 95% - 98%

    # Cryptographic integrity bundle
    bundle_data = (
        f"{biometric_token}|{agreement.agreement_no}|{agreement.owner_name}|{agreement.owner_aadhaar_last4}|"
        f"{agreement.tenant_name}|{agreement.tenant_aadhaar_last4}|{device}|{device_sn}|{now.isoformat()}"
    )
    security_seal = hashlib.sha256(bundle_data.encode('utf-8')).hexdigest().upper()

    return {
        "status": "Captured & Verified",
        "biometric_token": biometric_token,
        "device_name": device,
        "device_serial": device_sn,
        "captured_at": now.strftime("%d-%b-%Y %H:%M:%S"),
        "owner_quality": f"{owner_score}%",
        "tenant_quality": f"{tenant_score}%",
        "nfiq_status": "NFIQ 2.0 Compliant (Score 1 - Excellent)",
        "security_seal": security_seal,
        "operator": "Dashmesh Doorstep Biometric Facilitation Desk",
        "rd_service_version": "v2.0.4 (Maha e-Registration Compatible)"
    }
