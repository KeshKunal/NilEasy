"""
utils/sms_utils.py

Purpose: SMS formatting helpers

- Builds exact GST-compliant SMS text
- Generates deep links to messaging apps
"""

import urllib.parse

def build_gst_sms_content(gstin: str, gst_type: str, period: str) -> str:
    """
    Builds the exact SMS content for GST filing.
    Format must match GST portal requirements.
    """
    # TODO: Implement actual GST SMS format
    sms_template = f"NIL {gst_type} {period} {gstin}"
    return sms_template

def create_sms_deep_link(sms_content: str, phone_number: str = "9880692636") -> str:
    """
    Creates a deep link to open messaging app with pre-filled SMS.
    
    Args:
        sms_content: The SMS text content
        phone_number: GST helpline number
    """
    encoded_message = urllib.parse.quote(sms_content)
    deep_link = f"sms:{phone_number}?body={encoded_message}"
    
    return f"📱 [Click here to send SMS]({deep_link})"

def validate_sms_format(sms_content: str) -> bool:
    """
    Validates that SMS matches GST requirements.
    """
    # TODO: Implement validation logic
    return True
