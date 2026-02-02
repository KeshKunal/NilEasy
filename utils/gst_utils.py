"""
utils/gst_utils.py

Purpose: GST-specific utilities

- GSTIN formatting
- Period normalization (month/quarter to codes)
- GST return type helpers
"""

import re
from typing import Optional, Tuple
from datetime import datetime


def format_gstin(gstin: str) -> str:
    """
    Formats GSTIN for display (adds spaces for readability).
    
    Format: 27 AABCU 9603 R 1Z M
    
    Args:
        gstin: GSTIN string
    
    Returns:
        Formatted GSTIN with spaces
    """
    gstin = gstin.strip().upper()
    
    if len(gstin) != 15:
        return gstin
    
    # Format: XX XXXXX XXXX X XX X
    return f"{gstin[:2]} {gstin[2:7]} {gstin[7:11]} {gstin[11]} {gstin[12:14]} {gstin[14]}"


def normalize_period(period: str) -> str:
    """
    Normalizes period to MMYYYY format for GST portal.
    
    Accepts:
    - "Jan 2026" or "January 2026" → "012026"
    - "Q1 2026" → "032026" (Q1 = Jan-Mar, use March)
    - "012026" → "012026" (already normalized)
    
    Args:
        period: Period string
    
    Returns:
        Period in MMYYYY format
    """
    period = period.strip()
    
    # Already in MMYYYY format
    if re.match(r"^\d{6}$", period):
        return period
    
    # Handle "Jan 2026" or "January 2026" format
    month_year_match = re.match(r"^(\w+)\s+(\d{4})$", period, re.IGNORECASE)
    if month_year_match:
        month_name, year = month_year_match.groups()
        month_code = get_month_code(month_name)
        if month_code:
            return f"{month_code}{year}"
    
    # Handle "Q1 2026" format
    quarter_match = re.match(r"^Q([1-4])\s+(\d{4})$", period, re.IGNORECASE)
    if quarter_match:
        quarter, year = quarter_match.groups()
        # Use last month of quarter for filing
        quarter_end_months = {"1": "03", "2": "06", "3": "09", "4": "12"}
        month_code = quarter_end_months[quarter]
        return f"{month_code}{year}"
    
    # If we can't parse, return as-is (will fail validation later)
    return period


def get_month_code(month_name: str) -> Optional[str]:
    """
    Converts month name to 2-digit code.
    
    Args:
        month_name: Month name (e.g., "Jan", "January")
    
    Returns:
        2-digit month code ("01" to "12") or None
    """
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
    
    return month_map.get(month_name.lower())


def get_period_code(month: int, year: int) -> str:
    """
    Generates period code from month and year.
    
    Args:
        month: Month number (1-12)
        year: Year (e.g., 2026)
    
    Returns:
        Period code in MMYYYY format
    """
    return f"{month:02d}{year}"


def parse_period_code(period_code: str) -> Optional[Tuple[int, int]]:
    """
    Parses MMYYYY period code into month and year.
    
    Args:
        period_code: Period in MMYYYY format
    
    Returns:
        Tuple of (month, year) or None if invalid
    """
    if not re.match(r"^\d{6}$", period_code):
        return None
    
    try:
        month = int(period_code[:2])
        year = int(period_code[2:])
        
        if month < 1 or month > 12:
            return None
        
        return (month, year)
    except ValueError:
        return None


def format_period_for_display(period_code: str) -> str:
    """
    Formats period code for user-friendly display.
    
    Args:
        period_code: Period in MMYYYY format (e.g., "012026")
    
    Returns:
        Formatted string (e.g., "January 2026")
    """
    parsed = parse_period_code(period_code)
    if not parsed:
        return period_code
    
    month, year = parsed
    
    month_names = [
        "January", "February", "March", "April",
        "May", "June", "July", "August",
        "September", "October", "November", "December"
    ]
    
    return f"{month_names[month - 1]} {year}"


def get_gst_type_code(gst_type: str) -> str:
    """
    Converts GST type name to code used in SMS.
    
    Args:
        gst_type: GST type ("regular" or "composition")
    
    Returns:
        Type code ("R" or "C")
    """
    type_map = {
        "regular": "R",
        "composition": "C",
        "nil": "N"
    }
    
    return type_map.get(gst_type.lower(), "N")


def get_gst_type_display(gst_type: str) -> str:
    """
    Formats GST type for user display.
    
    Args:
        gst_type: GST type code or name
    
    Returns:
        User-friendly display name
    """
    display_map = {
        "r": "Regular Taxpayer",
        "regular": "Regular Taxpayer",
        "c": "Composition Taxpayer",
        "composition": "Composition Taxpayer",
        "n": "Nil Return",
        "nil": "Nil Return"
    }
    
    return display_map.get(gst_type.lower(), gst_type)


def calculate_filing_deadline(period_code: str, gst_type: str = "regular") -> Optional[str]:
    """
    Calculates the filing deadline for a given period.
    
    Args:
        period_code: Period in MMYYYY format
        gst_type: GST type ("regular" or "composition")
    
    Returns:
        Deadline date as string or None
    """
    parsed = parse_period_code(period_code)
    if not parsed:
        return None
    
    month, year = parsed
    
    # Regular taxpayers: 20th of next month
    # Composition taxpayers: 18th of next month
    deadline_day = 20 if gst_type.lower() == "regular" else 18
    
    # Calculate next month
    deadline_month = month + 1
    deadline_year = year
    if deadline_month > 12:
        deadline_month = 1
        deadline_year += 1
    
    try:
        deadline = datetime(deadline_year, deadline_month, deadline_day)
        return deadline.strftime("%d %B %Y")
    except ValueError:
        return None


def is_filing_overdue(period_code: str, gst_type: str = "regular") -> bool:
    """
    Checks if filing is overdue for the given period.
    
    Args:
        period_code: Period in MMYYYY format
        gst_type: GST type
    
    Returns:
        True if overdue
    """
    deadline_str = calculate_filing_deadline(period_code, gst_type)
    if not deadline_str:
        return False
    
    try:
        deadline = datetime.strptime(deadline_str, "%d %B %Y")
        return datetime.now() > deadline
    except ValueError:
        return False


def get_available_periods(count: int = 12) -> list:
    """
    Gets list of available periods for filing (last N months).
    
    Args:
        count: Number of past periods to return
    
    Returns:
        List of period codes in MMYYYY format
    """
    periods = []
    current = datetime.now()
    
    for i in range(count):
        # Go back i months
        month = current.month - i
        year = current.year
        
        while month <= 0:
            month += 12
            year -= 1
        
        periods.append(get_period_code(month, year))
    
    return periods
