"""
app/flow/handlers/welcome.py

Handles: STEP 0 – Entry / Welcome

- Processes "Hi" / CTA entry
- Sends welcome message and start options
- Initializes session state
"""

from typing import Dict, Any

from app.flow.states import ConversationState
from app.services.session_service import update_user_state, reset_session
from app.services.user_service import get_or_create_user
from utils.constants import WELCOME_MESSAGE, BUTTON_START_FILING, BUTTON_HELP
from utils.whatsapp_utils import create_button_message
from app.core.logging import get_logger, LogContext

logger = get_logger(__name__)


async def handle_welcome(user_id: str, message: str) -> Dict[str, Any]:
    """
    Handles welcome message and initializes user session.
    
    Args:
        user_id: WhatsApp user ID
        message: User's message (typically "Hi" or button click)
    
    Returns:
        Response dict with message payload
    """
    with LogContext(user_id=user_id, state="WELCOME"):
        logger.info("Processing welcome interaction")
        
        try:
            # Get or create user
            user = await get_or_create_user(user_id)
            
            # Reset any existing session
            await reset_session(user_id, "Starting new filing session")
            
            # Update state to WELCOME
            await update_user_state(
                user_id,
                ConversationState.WELCOME,
                validate_transition=False  # Entry point, no validation needed
            )
            
            # Create response with buttons
            response = create_button_message(
                text=WELCOME_MESSAGE,
                buttons=[
                    {"id": "start_filing", "title": BUTTON_START_FILING},
                    {"id": "help", "title": BUTTON_HELP}
                ]
            )
            
            logger.info("Welcome message sent successfully")
            
            return {
                "status": "success",
                "message": response,
                "next_state": ConversationState.ASK_GSTIN.value
            }
            
        except Exception as e:
            logger.error(f"Error in welcome handler: {str(e)}", exc_info=True)
            
            return {
                "status": "error",
                "message": {
                    "type": "text",
                    "text": "❌ Oops! Something went wrong. Please type 'Hi' to restart."
                },
                "error": str(e)
            }
