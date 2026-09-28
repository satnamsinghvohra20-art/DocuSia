import math

def calculate_stamp_duty(
    monthly_rent: int,
    deposit: int,
    months: int = 11,
    non_refundable_deposit: int = 0,
    area_type: str = "urban"
) -> dict:
    """
    Maharashtra Leave & License Stamp Duty & Registration Fee Calculator
    Standard Formula:
      Total Rent = monthly_rent * months
      Imputed Interest on refundable deposit = (deposit * 0.10) * (months / 12)
      Total Consideration Value (V) = Total Rent + non_refundable_deposit + Imputed Interest
      Stamp Duty = 0.25% of V (rounded up to nearest multiple of Rs 100, min Rs 100)
      Registration Fee:
        - Urban (Municipal Corp: Mumbai, Pune, Thane, Navi Mumbai, PCMC, etc.): Rs 1,000
        - Rural (Gram Panchayat / Rural Councils): Rs 500
    """
    total_rent = monthly_rent * months
    imputed_deposit_interest = (deposit * 0.10) * (months / 12.0)
    total_consideration = total_rent + non_refundable_deposit + imputed_deposit_interest
    
    # 0.25% stamp duty
    raw_stamp_duty = total_consideration * 0.0025
    
    # Round up to nearest Rs 100 with minimum Rs 100
    stamp_duty = max(100, math.ceil(raw_stamp_duty / 100.0) * 100)
    
    # Registration fee
    is_urban = area_type.lower() != "rural"
    reg_fee = 1000 if is_urban else 500
    
    total_govt_fees = stamp_duty + reg_fee
    
    return {
        "monthly_rent": monthly_rent,
        "deposit": deposit,
        "months": months,
        "total_rent": total_rent,
        "imputed_deposit_interest": round(imputed_deposit_interest, 2),
        "total_consideration": round(total_consideration, 2),
        "stamp_duty": int(stamp_duty),
        "registration_fee": reg_fee,
        "total_govt_fees": int(total_govt_fees),
        "area_type": "Urban (Municipal Corporation)" if is_urban else "Rural (Gram Panchayat)"
    }


def num_to_words_inr(n: int) -> str:
    """Helper to convert Indian Rupee amounts into words for legal contracts."""
    if n == 0:
        return "Zero Rupees"
    
    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
             "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
             "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    
    def two_digits(num):
        if num < 20:
            return units[num]
        return tens[num // 10] + (" " + units[num % 10] if num % 10 != 0 else "")
    
    def three_digits(num):
        res = ""
        hundreds = num // 100
        remainder = num % 100
        if hundreds > 0:
            res += units[hundreds] + " Hundred"
            if remainder > 0:
                res += " and "
        if remainder > 0:
            res += two_digits(remainder)
        return res

    parts = []
    crores = n // 10000000
    n %= 10000000
    if crores > 0:
        parts.append(two_digits(crores) + " Crore")
        
    lakhs = n // 100000
    n %= 100000
    if lakhs > 0:
        parts.append(two_digits(lakhs) + " Lakh")
        
    thousands = n // 1000
    n %= 1000
    if thousands > 0:
        parts.append(two_digits(thousands) + " Thousand")
        
    if n > 0:
        parts.append(three_digits(n))
        
    return " ".join(parts).strip() + " Rupees Only"
