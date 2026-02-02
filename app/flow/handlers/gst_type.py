"""
app/flow/handlers/gst_type.py

Handles: STEP 3 – GST Return Type selection

- Displays WhatsApp list (GSTR-1, GSTR-3B)
- Handles info/help option
- Saves selected return type
"""

from typing import Dict, Any

from app.flow.states import ConversationState
from app.services.session_service import update_user_state, save_session_data
from utils.constants import (
    ASK_GST_TYPE_MESSAGE,
    MESSAGE_GST_TYPE_INFO,
    BUTTON_SELECT_GST_TYPE
)
from utils.whatsapp_utils import create_list_message, create_text_message
from app.core.logging import get_logger, LogContext

logger = get_logger(__name__)


async def handle_gst_type_request(user_id: str) -> Dict[str, Any]:
    """
    Sends GST type selection list.
    
    Args:
        user_id: User ID
    
    Returns:
        Response dict with list message
    """
    with LogContext(user_id=user_id, state="ASK_GST_TYPE"):
        logger.info("Requesting GST type selection")
        
        # Update state
        await update_user_state(
            user_id,
            ConversationState.ASK_GST_TYPE,
            validate_transition=True
        )
        
        # Create list message with GST types
        sections = [
            {
                "title": "Select Your GST Type",
                "rows": [
                    {
                        "id": "gst_regular",
                        "title": "Regular Taxpayer",
                        "description": "For normal GST registered businesses"
                    },
                    {
                        "id": "gst_composition",
                        "title": "Composition Scheme",
                        "description": "For composition taxpayers"
                    }
                ]
            },
            {
                "title": "Need Help?",
                "rows": [
                    {
                        "id": "gst_help",
                        "title": "What's the difference?",
                        "description": "Learn about GST types"
                    }
                ]
            }
        ]
        
        return {
            "status": "success",
            "message": create_list_message(
                text=ASK_GST_TYPE_MESSAGE,
                button_text=BUTTON_SELECT_GST_TYPE,
                sections=sections
            ),
            "next_state": ConversationState.ASK_GST_TYPE.value
        }


async def handle_gst_type_selection(user_id: str, selection: str) -> Dict[str, Any]:
    """
    Handles GST type selection from user.
    
    Args:
        user_id: User ID
        selection: Selected option ID
    
    Returns:
        Response dict
    """
    with LogContext(user_id=user_id, state="ASK_GST_TYPE"):
        logger.info(f"Processing GST type selection: {selection}")
        
        # Handle help request
        if selection == "gst_help":
            return {
                "status": "info",
                "message": create_text_message(MESSAGE_GST_TYPE_INFO),
                "retry": True  # Ask again after showing info
            }
        
        # Map selection to GST type
        gst_type_map = {
            "gst_regular": "regular",
            "gst_composition": "composition"
        }
        
        gst_type = gst_type_map.get(selection)
        
        if not gst_type:
            logger.warning(f"Invalid GST type selection: {selection}")
            return {
                "status": "error",
                "message": create_text_message(
                    "⚠️ Invalid selection. Please select a valid GST type."
                ),
                "retry": True
            }
        
        # Save GST type to session
        await save_session_data(user_id, {"gst_type": gst_type})
        
        logger.info(f"GST type saved: {gst_type}")
        
        # Move to duration/period selection
        from app.flow.handlers.duration import handle_duration_request
        return await handle_duration_request(user_id)