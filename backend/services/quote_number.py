"""
Quotation Number Generator & Amount-in-Words (Indian format)

Quotation Number Format:
  AD / (Customer Initials) / DDMM / FY / 4-char-alphanumeric
  Example: AD/AC/1103/25-26/Yz65

Amount in Words:
  Indian numbering system (Lakh, Crore)
  Example: "Forty Six Thousand Seventy Five Rupees Only"
"""

import random
import string
from datetime import datetime


def generate_quote_number(client_name: str = "") -> str:
    """
    Generate quotation number in format: AD/XX/DDMM/YY-YY/XXXX
    - AD = ACCU DESIGN
    - XX = First letter of each word in client name (max 3 chars)
    - DDMM = today's date
    - YY-YY = Indian Financial Year (April–March)
    - XXXX = 4-char alphanumeric unique ID
    """
    now = datetime.now()

    # Customer initials (Rule: 1st and 5th character, or last character if < 4)
    # Example: 'QuinTrans' -> 'QT', 'ABC' -> 'C'
    clean_name = client_name.strip()
    if clean_name:
        flat_name = clean_name.replace(" ", "")
        if len(flat_name) < 4:
            initials = flat_name[-1].upper() if flat_name else "XX"
        else:
            initials = flat_name[0].upper() + (flat_name[4].upper() if len(flat_name) > 4 else flat_name[-1].upper())
    else:
        initials = "XX"

    # Date format DDMM
    ddmm = now.strftime("%d%m")

    # Indian Financial Year (April to March)
    if now.month >= 4:
        fy = f"{now.year % 100}-{(now.year + 1) % 100}"
    else:
        fy = f"{(now.year - 1) % 100}-{now.year % 100}"

    # 4-char alphanumeric unique ID
    chars = string.ascii_letters + string.digits
    uid = "".join(random.choices(chars, k=4))

    return f"AD/{initials}/{ddmm}/{fy}/{uid}"


# ── Amount in Words (Indian numbering system) ────────────────────────────────

_ONES = [
    '', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
    'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
    'Seventeen', 'Eighteen', 'Nineteen',
]

_TENS = [
    '', '', 'Twenty', 'Thirty', 'Forty', 'Fifty',
    'Sixty', 'Seventy', 'Eighty', 'Ninety',
]


def _two_digit(n: int) -> str:
    if n < 20:
        return _ONES[n]
    return (_TENS[n // 10] + ' ' + _ONES[n % 10]).strip()


def _three_digit(n: int) -> str:
    if n < 100:
        return _two_digit(n)
    h = _ONES[n // 100] + ' Hundred'
    r = n % 100
    return (h + ' ' + _two_digit(r)).strip() if r else h


def number_to_words_indian(n: int) -> str:
    """Convert an integer to words in Indian numbering system."""
    if n == 0:
        return 'Zero'

    parts = []

    if n >= 10_00_00_000:  # Crore
        crore = n // 10_00_00_000
        parts.append(_three_digit(crore) + ' Crore')
        n %= 10_00_00_000

    if n >= 1_00_000:  # Lakh
        lakh = n // 1_00_000
        parts.append(_two_digit(lakh) + ' Lakh')
        n %= 1_00_000

    if n >= 1_000:  # Thousand
        thousand = n // 1_000
        parts.append(_two_digit(thousand) + ' Thousand')
        n %= 1_000

    if n > 0:
        parts.append(_three_digit(n))

    return ' '.join(parts)


def amount_in_words(amount: float) -> str:
    """
    Convert a rupee amount to words in Indian format.
    Example: 46075.50 → "Forty Six Thousand Seventy Five Rupees and Fifty Paise Only"
    """
    rupees = int(amount)
    paise = round((amount - rupees) * 100)

    words = number_to_words_indian(rupees) + ' Rupees'
    if paise > 0:
        words += ' and ' + number_to_words_indian(paise) + ' Paise'
    words += ' Only'
    return words
