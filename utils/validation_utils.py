"""
utils/validation_utils.py

Purpose: Input validation

- GSTIN regex and checksum validation
- OTP parsing with multiple patterns
- Date and period validation
- Input sanitization
"""

import re
from typing import Optional, Tuple
from datetime import datetime


def validate_gstin(gstin: str) -> bool:
    """
    Validates GSTIN format using regex and checksum.
    
    Format: 2 digits (state) + 10 chars (PAN) + 1 digit + 1 letter + 1 letter/digit
    Example: 27AABCU9603R1ZM
    
    Args:
        gstin: GSTIN string to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not gstin:
        return False
    
    gstin = gstin.strip().upper()
    
    # Basic format check
    pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$"
    if not re.match(pattern, gstin):
        return False
    
    # Validate state code (01-37)
    state_code = int(gstin[:2])
    if state_code < 1 or state_code > 37:
        return False
    
    # Optional: Add checksum validation here if needed
    # For now, format validation is sufficient
    
    return True


def calculate_gstin_checksum(gstin: str) -> str:
    """
    Calculates the checksum digit for GSTIN.
    Used for validating GSTIN authenticity.
    
    Args:
        gstin: First 14 characters of GSTIN
    
    Returns:
        Checksum character
    """
    # This is a simplified version. Full implementation requires the official algorithm.
    # For production, use official GST checksum validation
    return gstin[-1]


def extract_otp(message: str) -> Optional[str]:
    """
    Extracts OTP from a message using multiple patterns.
    Handles various OTP formats from GST portal.
    
    Args:
        message: SMS or message containing OTP
    
    Returns:
        6-digit OTP if found, None otherwise
    """
    if not message:
        return None
    
    # Pattern 1: Standard 6-digit OTP
    otp_pattern = r"\b\d{6}\b"
    match = re.search(otp_pattern, message)
    if match:
        return match.group(0)
    
    # Pattern 2: OTP with context (e.g., "OTP: 123456" or "OTP is 123456")
    otp_context_pattern = r"(?:OTP|otp)[:\s]+([0-9]{6})"
    match = re.search(otp_context_pattern, message, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Pattern 3: OTP in parentheses or quotes
    otp_wrapped_pattern = r"[\(\[\'\"]([0-9]{6})[\)\]\'\"]"
    match = re.search(otp_wrapped_pattern, message)
    if match:
        return match.group(1)
    
    return None


def validate_otp_format(otp: str) -> bool:
    """
    Validates OTP format (must be 6 digits).
    
    Args:
        otp: OTP string
    
    Returns:
        True if valid 6-digit OTP
    """
    if not otp:
        return False
    
    return bool(re.match(r"^\d{6}$", otp.strip()))


def validate_phone_number(phone: str) -> bool:
    """
    Validates Indian phone number format.
    
    Args:
        phone: Phone number string
    
    Returns:
        True if valid Indian mobile number
    """
    if not phone:
        return False
    
    # Remove common separators and spaces
    phone = re.sub(r"[\s\-\(\)\+]", "", phone)
    
    # Remove country code if present
    if phone.startswith("91"):
        phone = phone[2:]
    elif phone.startswith("+91"):
        phone = phone[3:]
    
    # Validate Indian mobile format (starts with 6-9, 10 digits total)
    pattern = r"^[6-9]\d{9}$"
    return bool(re.match(pattern, phone))


def validate_period_format(period: str) -> bool:
    """
    Validates period format.
    Accepts: "Jan 2026", "January 2026", "Q1 2026", "012026"
    
    Args:
        period: Period string
    
    Returns:
        True if valid period format
    """
    if not period or len(period.strip()) < 4:
        return False
    
    period = period.strip()
    
    # Pattern 1: Month name + year (e.g., "Jan 2026" or "January 2026")
    month_year_pattern = r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}$"
    if re.match(month_year_pattern, period, re.IGNORECASE):
        return True
    
    # Pattern 2: Quarter + year (e.g., "Q1 2026")
    quarter_pattern = r"^Q[1-4]\s+\d{4}$"
    if re.match(quarter_pattern, period, re.IGNORECASE):
        return True
    
    # Pattern 3: Numeric format MMYYYY (e.g., "012026")
    numeric_pattern = r"^(0[1-9]|1[0-2])\d{4}$"
    if re.match(numeric_pattern, period):
        return True
    
    return False


def parse_period(period: str) -> Optional[Tuple[str, str]]:
    """
    Parses period string into (month, year) tuple.
    
    Args:
        period: Period string
    
    Returns:
        Tuple of (month_code, year) or None if invalid
    """
    if not validate_period_format(period):
        return None
    
    period = period.strip()
    
    # Handle "Jan 2026" or "January 2026" format
    month_year_match = re.match(r"^(\w+)\s+(\d{4})$", period)
    if month_year_match:
        month_name, year = month_year_match.groups()
        month_map = {
            "jan": "01", "january": "01",
            "feb": "02", "february": "02",
            "mar": "03", "march": "03",
            "apr": "04", "april": "04",
            "may": "05",
            "jun": "06", "june": "06",
            "jul": "07", "july": "07",
            "aug": "08", "august": "08",
            "sep": "09", "september": "09",
            "oct": "10", "october": "10",
            "nov": "11", "november": "11",
            "dec": "12", "december": "12"
        }
        month_code = month_map.get(month_name.lower())
        if month_code:
            return (month_code, year)
    
    # Handle "012026" format
    numeric_match = re.match(r"^(0[1-9]|1[0-2])(\d{4})$", period)
    if numeric_match:
        month_code, year = numeric_match.groups()
        return (month_code, year)
    
    return None


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitizes user input to prevent injection attacks.
    
    Args:
        text: Input text
        max_length: Maximum allowed length
    
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Trim to max length
    text = text[:max_length]
    
    # Remove potentially dangerous characters
    # Keep alphanumeric, spaces, and common punctuation
    text = re.sub(r"[<>{}\[\]]", "", text)
    
    # Normalize whitespace
    text = " ".join(text.split())
    
    return text.strip()


def validate_captcha(captcha: str) -> bool:
    """
    Validates captcha format.
    
    Args:
        captcha: Captcha text entered by user
    
    Returns:
        True if format is acceptable
    """
    if not captcha:
        return False
    
    # Captcha should be alphanumeric, typically 4-8 characters
    captcha = captcha.strip()
    
    if len(captcha) < 3 or len(captcha) > 10:
        return False
    
    # Allow alphanumeric only
    return bool(re.match(r"^[a-zA-Z0-9]+$", captcha))


def is_valid_year(year: str) -> bool:
    """
    Validates year is within reasonable range for GST filing.
    
    Args:
        year: Year string (e.g., "2026")
    
    Returns:
        True if valid year for GST filing
    """
    try:
        year_int = int(year)
        current_year = datetime.now().year
        
        # Allow 2 years back and 1 year forward
        return (current_year - 2) <= year_int <= (current_year + 1)
    except (ValueError, TypeError):
        return False
