"""
app/flow/handlers/gst_type.py

Handles: STEP 3 – GST Return Type selection

- Displays GST type options
- Saves selected return type
"""

from typing import Dict, Any
from datetime import datetime

from app.flow.states import ConversationState
from app.db.mongo import get_users_collection
from app.core.logging import get_logger

logger = get_logger(__name__)


async def handle_gst_type_selection(user_id: str, message: str, **kwargs) -> Dict[str, Any]:
    """
    Handles GST type selection from user.
    
    Args:
        user_id: User's phone number
        message: User's message (1 or 2)
        **kwargs: Additional parameters
    
    Returns:
        Response dict
    """
    logger.info(f"Processing GST type selection for {user_id}: {message}")
    
    try:
        users = get_users_collection()
        selection = message.strip().lower()
        
        # Map selection to GST type
        gst_type = None
        gst_type_display = None
        
        if selection in ["1", "gstr-1", "gstr1"]:
            gst_type = "gstr1"
            gst_type_display = "GSTR-1"
        elif selection in ["2", "gstr-3b", "gstr3b", "3b"]:
            gst_type = "gstr3b"
            gst_type_display = "GSTR-3B"
        
        if not gst_type:
            logger.warning(f"Invalid GST type selection: {selection}")
            return {
                "message": """⚠️ *Invalid selection*

Please reply with:
*1* - GSTR-1 (Outward supplies)
*2* - GSTR-3B (Summary return)"""
            }
        
        # Save GST type to session and update state
        await users.update_one(
            {"phone": user_id},
            {
                "$set": {
                    "gst_type": gst_type,
                    "current_state": ConversationState.AWAITING_DURATION.value,
                    "session_data.gst_type": gst_type,
                    "last_active": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"GST type saved: {gst_type}")
        
        # Move to duration/period selection
        return {
            "message": f"""✅ *{gst_type_display} selected*

Now, for which period do you want to file the Nil return?

Reply with the month number:
*1* - January 2026
*2* - February 2026
*3* - December 2025
*4* - November 2025

Or type the month and year (e.g., *Jan 2026*)"""
        }
        
    except Exception as e:
        logger.error(f"Error processing GST type selection: {str(e)}", exc_info=True)
        
        return {
            "message": f"❌ Error: {str(e)}\n\nPlease try again."
        }