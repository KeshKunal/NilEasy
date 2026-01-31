"""
utils/time_utils.py

Purpose: Time and expiry helpers

- Session TTL calculations
- OTP expiry checks
- Timestamp utilities
"""

from datetime import datetime, timedelta
from typing import Optional

def is_session_expired(last_interaction: datetime, timeout_minutes: int = 30) -> bool:
    """
    Checks if a session has expired based on last interaction time.
    """
    if not last_interaction:
        return True
    
    expiry_time = last_interaction + timedelta(minutes=timeout_minutes)
    return datetime.utcnow() > expiry_time

def calculate_otp_expiry(otp_time: datetime, validity_minutes: int = 10) -> datetime:
    """
    Calculates OTP expiry timestamp.
    """
    return otp_time + timedelta(minutes=validity_minutes)

def is_otp_expired(otp_time: datetime, validity_minutes: int = 10) -> bool:
    """
    Checks if an OTP has expired.
    """
    expiry_time = calculate_otp_expiry(otp_time, validity_minutes)
    return datetime.utcnow() > expiry_time

def format_timestamp(dt: Optional[datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Formats a datetime object to string.
    """
    if not dt:
        return "N/A"
    return dt.strftime(format_str)

def get_current_month_year() -> tuple:
    """
    Returns current month and year.
    """
    now = datetime.utcnow()
    return (now.strftime("%B"), str(now.year))
