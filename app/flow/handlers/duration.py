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
from app.services.session_service import update_user_state, save_session_data, get_session_data
from app.services.user_service import check_duplicate_filing
from utils.constants import (
    ASK_DURATION_MESSAGE,
    WARNING_DUPLICATE_FILING,
    BUTTON_SELECT_PERIOD
)
from utils.whatsapp_utils import create_list_message, create_text_message
from utils.gst_utils import get_available_periods, format_period_for_display, normalize_period
from utils.validation_utils import validate_period_format
from app.core.logging import get_logger, LogContext

logger = get_logger(__name__)


async def handle_duration_request(user_id: str) -> Dict[str, Any]:
    """
    Sends duration/period selection list.
    
    Args:
        user_id: User ID
    
    Returns:
        Response dict with period selection
    """
    with LogContext(user_id=user_id, state="ASK_DURATION"):
        logger.info("Requesting filing period selection")
        
        # Update state
        await update_user_state(
            user_id,
            ConversationState.ASK_DURATION,
            validate_transition=True
        )
        
        # Get available periods (last 12 months)
        available_periods = get_available_periods(12)
        
        # Create rows for list
        rows = []
        for period_code in available_periods[:6]:  # Show last 6 months
            display_text = format_period_for_display(period_code)
            rows.append({
                "id": f"period_{period_code}",
                "title": display_text,
                "description": f"File for {display_text}"
            })
        
        sections = [
            {
                "title": "Select Filing Period",
                "rows": rows
            }
        ]
        
        return {
            "status": "success",
            "message": create_list_message(
                text=ASK_DURATION_MESSAGE,
                button_text=BUTTON_SELECT_PERIOD,
                sections=sections,
                footer="📅 Select the month you want to file for"
            ),
            "next_state": ConversationState.ASK_DURATION.value
        }


async def handle_duration_selection(user_id: str, selection: str) -> Dict[str, Any]:
    """
    Handles period selection from user.
    
    Args:
        user_id: User ID
        selection: Selected period (e.g., "period_012026" or text like "Jan 2026")
    
    Returns:
        Response dict
    """
    with LogContext(user_id=user_id, state="ASK_DURATION"):
        logger.info(f"Processing period selection: {selection}")
        
        try:
            # Parse selection
            if selection.startswith("period_"):
                period_code = selection.replace("period_", "")
            else:
                # User typed period manually
                period_code = normalize_period(selection)
            
            # Validate period format
            if not validate_period_format(period_code) and not validate_period_format(selection):
                logger.warning(f"Invalid period format: {selection}")
                return {
                    "status": "error",
                    "message": create_text_message(
                        "⚠️ Invalid period format. Please select from the list or enter in format 'Jan 2026'."
                    ),
                    "retry": True
                }
            
            # Normalize to MMYYYY format
            period_normalized = normalize_period(period_code if validate_period_format(period_code) else selection)
            
            # Get session data for duplicate check
            session_data = await get_session_data(user_id)
            gstin = session_data.get("gstin")
            gst_type = session_data.get("gst_type")
            
            # Check for duplicate filing
            if gstin:
                is_duplicate = await check_duplicate_filing(
                    user_id=user_id,
                    gstin=gstin,
                    gst_type=gst_type,
                    period=period_normalized
                )
                
                if is_duplicate:
                    logger.warning(f"Duplicate filing detected for period {period_normalized}")
                    yield {
                        "status": "warning",
                        "message": create_text_message(WARNING_DUPLICATE_FILING)
                    }
            
            # Save period to session
            await save_session_data(user_id, {"period": period_normalized})
            
            logger.info(f"Period saved: {period_normalized}")
            
            # Move to SMS generation
            from app.flow.handlers.sms import handle_sms_generation
            return await handle_sms_generation(user_id)
            
        except Exception as e:
            logger.error(f"Error processing period selection: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": create_text_message(
                    f"❌ Error processing period: {str(e)}\n\nPlease try again."
                ),
                "error": str(e)
            }
