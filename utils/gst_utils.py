"""
utils/gst_utils.py

Purpose: GST-specific helpers

- GSTIN formatting and normalization
- Period formatting utilities
"""

import re

def format_gstin(gstin: str) -> str:
    """
    Formats GSTIN to standard uppercase format.
    """
    return gstin.strip().upper()

def normalize_period(period_input: str) -> str:
    """
    Normalizes period input to GST-accepted format.
    
    Examples:
        "January 2026" -> "Jan 2026"
        "Q1 2026" -> "Jan-Mar 2026"
    """
    # TODO: Implement period normalization logic
    return period_input.strip()

def parse_month_year(period: str) -> tuple:
    """
    Parses period string into (month, year) tuple.
    """
    # TODO: Implement parsing logic
    return ("Jan", "2026")

def get_period_code(month: str, year: str) -> str:
    """
    Converts month/year to GST period code.
    """
    month_codes = {
        "January": "01", "February": "02", "March": "03",
        "April": "04", "May": "05", "June": "06",
        "July": "07", "August": "08", "September": "09",
        "October": "10", "November": "11", "December": "12"
    }
    
    return f"{month_codes.get(month, '01')}{year}"
