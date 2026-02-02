"""
app/flow/handlers/completion.py

Handles: STEP 8 – Success & promotion

- Confirms successful filing (ARN received)
- Sends success message
- Promotes Aspire products
- Ends or resets the session
"""

from typing import Dict, Any
from datetime import datetime

from app.flow.states import ConversationState
from app.services.session_service import update_user_state, reset_session
from app.services.user_service import add_to_filing_history
from utils.constants import (
    MESSAGE_SUCCESS,
    MESSAGE_ASPIRE_PROMO,
    BUTTON_FILE_ANOTHER,
    BUTTON_DONE
)
from utils.whatsapp_utils import create_text_message, create_button_message
from app.core.logging import get_logger, LogContext

logger = get_logger(__name__)


async def handle_completion(user_id: str) -> Dict[str, Any]:
    """
    Handles successful filing completion.
    
    Args:
        user_id: User ID
    
    Returns:
        Response dict with success message
    """
    with LogContext(user_id=user_id, state="COMPLETION"):
        logger.info("Processing filing completion")
        
        try:
            # Update state to completion
            await update_user_state(
                user_id,
                ConversationState.COMPLETION,
                validate_transition=True
            )
            
            # Add to filing history
            await add_to_filing_history(
                user_id=user_id,
                filing_data={
                    "completed_at": datetime.utcnow(),
                    "status": "success"
                }
            )
            
            # Send success message
            yield {
                "status": "success",
                "message": create_text_message(MESSAGE_SUCCESS)
            }
            
            # Send promotion message
            yield {
                "status": "success",
                "message": create_text_message(MESSAGE_ASPIRE_PROMO)
            }
            
            # Ask if user wants to file another return
            yield {
                "status": "success",
                "message": create_button_message(
                    text="👋 What would you like to do next?",
                    buttons=[
                        {"id": "file_another", "title": BUTTON_FILE_ANOTHER},
                        {"id": "done", "title": BUTTON_DONE}
                    ]
                ),
                "next_state": ConversationState.COMPLETION.value
            }
            
            logger.info("Completion message sent successfully")
            
        except Exception as e:
            logger.error(f"Error in completion handler: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": create_text_message(
                    f"❌ Error completing process: {str(e)}"
                ),
                "error": str(e)
            }


async def handle_post_completion(user_id: str, action: str) -> Dict[str, Any]:
    """
    Handles post-completion actions.
    
    Args:
        user_id: User ID
        action: User's choice (file_another or done)
    
    Returns:
        Response dict
    """
    with LogContext(user_id=user_id, state="COMPLETION"):
        logger.info(f"Post-completion action: {action}")
        
        if action == "file_another":
            # Reset session and start over
            await reset_session(user_id, "Starting new filing")
            
            from app.flow.handlers.welcome import handle_welcome
            return await handle_welcome(user_id, "restart")
        else:
            # End session
            await reset_session(user_id, "User finished")
            
            return {
                "status": "success",
                "message": create_text_message(
                    "✅ Thank you for using NilEasy!\n\n"
                    "Type 'Hi' anytime to file another Nil return.\n\n"
                    "🚀 Have a great day!"
                ),
                "session_ended": True
            }
