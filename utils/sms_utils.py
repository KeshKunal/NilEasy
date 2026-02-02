"""
utils/sms_utils.py

Purpose: SMS message builders

- Formats SMS content for GST filing
- Generates deep links for mobile apps
- Handles URL encoding
"""

import urllib.parse
from typing import Dict, Optional


def build_gst_sms_content(
    gstin: str,
    gst_type: str,
    period: str,
    otp: Optional[str] = None
) -> str:
    """
    Builds SMS content in the format expected by GST portal.
    
    Format based on GST portal requirements:
    "NIL <GSTIN> <R/C/N> <MMYYYY>"
    
    Where:
    - NIL = Filing type
    - GSTIN = 15-digit GSTIN
    - R/C/N = Return type (R=Regular, C=Composition, N=Nil)
    - MMYYYY = Period in MMYYYY format
    
    Args:
        gstin: User's GSTIN
        gst_type: GST filing type ("regular" or "composition")
        period: Period in format "Jan 2026" or "012026"
        otp: Optional OTP to append
    
    Returns:
        Formatted SMS content
    """
    # Normalize GSTIN
    gstin = gstin.strip().upper()
    
    # Map filing type to code
    type_code_map = {
        "regular": "R",
        "composition": "C",
        "nil": "N"
    }
    type_code = type_code_map.get(gst_type.lower(), "N")
    
    # Normalize period to MMYYYY format
    from utils.gst_utils import normalize_period
    period_normalized = normalize_period(period)
    
    # Build base SMS
    sms_content = f"NIL {gstin} {type_code} {period_normalized}"
    
    # Append OTP if provided (after OTP is received)
    if otp:
        sms_content += f" {otp}"
    
    return sms_content


def create_sms_deep_link(
    phone_number: str,
    message: str
) -> str:
    """
    Creates a deep link that opens SMS app with pre-filled content.
    Works on both Android and iOS.
    
    Args:
        phone_number: Recipient phone number (GST portal number)
        message: Pre-filled SMS content
    
    Returns:
        SMS deep link URL
    """
    # URL encode the message
    encoded_message = urllib.parse.quote(message)
    
    # Format phone number (remove +91 if present)
    phone = phone_number.strip()
    if phone.startswith("+"):
        phone = phone[1:]
    
    # Create universal SMS link
    # This format works on both Android and iOS
    sms_link = f"sms:{phone}?&body={encoded_message}"
    
    return sms_link


def format_sms_instructions(
    gstin: str,
    gst_type: str,
    period: str,
    phone_number: str = "567678"
) -> Dict[str, str]:
    """
    Generates user-friendly SMS instructions with formatted content.
    
    Args:
        gstin: User's GSTIN
        gst_type: GST filing type
        period: Filing period
        phone_number: GST portal SMS number (default: 567678)
    
    Returns:
        Dict with 'sms_content', 'phone_number', and 'deep_link'
    """
    # Build SMS content
    sms_content = build_gst_sms_content(gstin, gst_type, period)
    
    # Create deep link
    deep_link = create_sms_deep_link(phone_number, sms_content)
    
    return {
        "sms_content": sms_content,
        "phone_number": phone_number,
        "deep_link": deep_link,
        "formatted_display": format_sms_display(sms_content, phone_number)
    }


def format_sms_display(sms_content: str, phone_number: str) -> str:
    """
    Formats SMS instructions for display to user.
    
    Args:
        sms_content: SMS content to send
        phone_number: Recipient number
    
    Returns:
        Formatted text for user display
    """
    return f"""📱 *Send this SMS:*

*To:* {phone_number}
*Message:*
```{sms_content}```

💡 _Tap the button below to auto-fill this message in your SMS app!_"""


def validate_sms_content(sms_content: str) -> bool:
    """
    Validates SMS content format before sending.
    
    Args:
        sms_content: SMS content to validate
    
    Returns:
        True if valid format
    """
    # Basic validation: check if it starts with NIL and has minimum fields
    parts = sms_content.strip().split()
    
    if len(parts) < 4:
        return False
    
    if parts[0].upper() != "NIL":
        return False
    
    # Validate GSTIN format (15 characters)
    if len(parts[1]) != 15:
        return False
    
    # Validate type code (R/C/N)
    if parts[2].upper() not in ["R", "C", "N"]:
        return False
    
    # Validate period format (MMYYYY - 6 digits)
    if len(parts[3]) != 6 or not parts[3].isdigit():
        return False
    
    return True


def get_gst_portal_number() -> str:
    """
    Returns the official GST portal SMS number.
    
    Returns:
        GST portal SMS number
    """
    # Official GST SMS number for NIL returns
    # Note: Verify this number with latest GST portal documentation
    return "567678"


def parse_gst_response_sms(sms_content: str) -> Optional[Dict[str, str]]:
    """
    Parses response SMS from GST portal to extract status and OTP.
    
    Args:
        sms_content: SMS content received from GST portal
    
    Returns:
        Dict with parsed information or None
    """
    # Extract OTP if present
    from utils.validation_utils import extract_otp
    otp = extract_otp(sms_content)
    
    # Check for success indicators
    success_keywords = ["success", "submitted", "filed", "acknowledged"]
    failure_keywords = ["failed", "error", "invalid", "rejected"]
    
    content_lower = sms_content.lower()
    
    status = "unknown"
    if any(keyword in content_lower for keyword in success_keywords):
        status = "success"
    elif any(keyword in content_lower for keyword in failure_keywords):
        status = "failure"
    
    return {
        "status": status,
        "otp": otp,
        "raw_content": sms_content
    }
