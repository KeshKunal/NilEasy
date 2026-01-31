"""
utils/validation_utils.py

Purpose: Input validation

- GSTIN regex
- OTP parsing
- Date and period validation
"""

import re
from typing import Optional

def validate_gstin(gstin: str) -> bool:
    """
    Validates GSTIN format using regex.
    
    Format: 2 digits (state) + 10 chars (PAN) + 1 digit + 1 letter + 1 letter/digit
    Example: 27AABCU9603R1ZM
    """
    pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$"
    return bool(re.match(pattern, gstin.strip().upper()))

def extract_otp(message: str) -> Optional[str]:
    """
    Extracts OTP from a message using regex.
    Looks for 6-digit numbers.
    """
    otp_pattern = r"\b\d{6}\b"
    match = re.search(otp_pattern, message)
    
    if match:
        return match.group(0)
    return None

def validate_phone_number(phone: str) -> bool:
    """
    Validates Indian phone number format.
    """
    pattern = r"^[6-9]\d{9}$"
    return bool(re.match(pattern, phone.strip()))

def validate_period_format(period: str) -> bool:
    """
    Validates period format (e.g., "Jan 2026", "Q1 2026").
    """
    # TODO: Implement comprehensive period validation
    return len(period) > 0
