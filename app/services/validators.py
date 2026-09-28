import re

# Verhoeff algorithm multiplication and permutation tables for Aadhaar checksum verification
VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

def validate_pan(pan: str) -> tuple[bool, str]:
    """Validates Indian Permanent Account Number (PAN) statutory format."""
    if not pan:
        return False, "PAN cannot be empty"
    pan = pan.strip().upper()
    if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan):
        return False, f"Invalid PAN format: '{pan}'. Expected 5 letters, 4 digits, 1 letter (e.g. ABCDE1234F)"
    # 4th character denotes entity: P=Person/Individual, C=Company, H=HUF, F=Firm, T=Trust
    entity = pan[3]
    if entity not in 'PCHFATBLJG':
        return False, f"Invalid entity character in PAN: '{entity}'"
    return True, "Valid PAN"

def validate_aadhaar_verhoeff(aadhaar: str) -> bool:
    """Verhoeff algorithm checksum validation for 12-digit Indian Aadhaar number."""
    digits = re.sub(r'[\s\-]', '', aadhaar)
    if not re.match(r'^\d{12}$', digits):
        return False
    # First digit of Aadhaar cannot be 0 or 1
    if digits[0] in '01':
        return False
    c = 0
    for i, item in enumerate(reversed(digits)):
        c = VERHOEFF_D[c][VERHOEFF_P[i % 8][int(item)]]
    return c == 0

def validate_mobile(mobile: str) -> tuple[bool, str]:
    """Validates 10-digit Indian mobile number."""
    if not mobile:
        return False, "Mobile cannot be empty"
    clean = re.sub(r'[\s\-\+]', '', mobile)
    if clean.startswith('91') and len(clean) == 12:
        clean = clean[2:]
    elif clean.startswith('0') and len(clean) == 11:
        clean = clean[1:]
    if re.match(r'^[6-9]\d{9}$', clean):
        return True, clean
    return False, f"Invalid Indian mobile number: '{mobile}'. Must be 10 digits starting with 6, 7, 8, or 9."

def sanitize_text(text: str, max_len: int = 500) -> str:
    """Sanitizes user input to prevent injection while preserving Indian address characters."""
    if not text:
        return ""
    cleaned = text.strip()
    # Strip potential HTML/script tags
    cleaned = re.sub(r'<[^>]*>', '', cleaned)
    # Remove null bytes or non-printable controls
    cleaned = "".join(ch for ch in cleaned if ord(ch) >= 32 or ch in "\n\r\t")
    return cleaned[:max_len]
