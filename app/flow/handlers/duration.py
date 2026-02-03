"""
app/flow/handlers/duration.py

Handles: STEP 4 – Filing duration selection

- Monthly / Quarterly selection
- Month or quarter mapping
- Normalizes period into GST-accepted format
- Stores duration in session data
"""

from typing import Dict, Any
from datetime import datetime

from app.flow.states import ConversationState
from app.db.mongo import get_users_collection
from utils.gst_utils import normalize_period
from app.core.logging import get_logger

logger = get_logger(__name__)


async def handle_duration_selection(user_id: str, message: str, **kwargs) -> Dict[str, Any]:
    """
    Handles period selection from user.
    
    Args:
        user_id: User's phone number
        message: Selected period (e.g., "1", "Jan 2026", etc.)
        **kwargs: Additional parameters
    
    Returns:
        Response dict
    """
    logger.info(f"Processing period selection for {user_id}: {message}")
    
    try:
        users = get_users_collection()
        selection = message.strip()
        
        # Map common selections to periods
        period_map = {
            "1": "012026",  # January 2026
            "2": "022026",  # February 2026
            "3": "122025",  # December 2025
            "4": "112025",  # November 2025
        }
        
        # Check if it's a number selection
        if selection in period_map:
            period_code = period_map[selection]
        else:
            # Try to parse as month/year
            period_code = normalize_period(selection)
        
        # Validate period format (MMYYYY)
        if not period_code or len(period_code) != 6 or not period_code.isdigit():
            logger.warning(f"Invalid period format: {selection}")
            return {
                "message": """⚠️ *Invalid period format*

Please reply with a number (1-4) or type the month and year.

*1* - January 2026
*2* - February 2026
*3* - December 2025
*4* - November 2025

Or type like: *Jan 2026*"""
            }
        
        # Get user's GSTIN and GST type for display
        user = await users.find_one({"phone": user_id})
        gstin = user.get("gstin", "N/A")
        gst_type = user.get("session_data", {}).get("gst_type", "gstr3b")
        
        # Format period for display
        month = int(period_code[:2])
        year = period_code[2:]
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        period_display = f"{month_names[month-1]} {year}"
        
        # Save period to session and update state
        await users.update_one(
            {"phone": user_id},
            {
                "$set": {
                    "current_state": ConversationState.SMS_GENERATION.value,
                    "session_data.period": period_code,
                    "session_data.period_display": period_display,
                    "last_active": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Period saved: {period_code} ({period_display})")
        
        # Generate OTP link and show summary
        from app.flow.handlers.sms import handle_sms_generation
        return await handle_sms_generation(user_id)
        
    except Exception as e:
        logger.error(f"Error processing period selection: {str(e)}", exc_info=True)
        
        return {
            "message": f"❌ Error: {str(e)}\n\nPlease try again."
        }
