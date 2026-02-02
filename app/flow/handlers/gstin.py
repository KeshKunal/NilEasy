"""
app/flow/handlers/gstin.py

Handles: STEP 1 – Ask GSTIN

- Accepts GSTIN input
- Validates format (via utils)
- Handles retry on invalid GSTIN
- Stores GSTIN in temporary session data
"""

from typing import Dict, Any

from app.flow.states import ConversationState
from app.services.session_service import (
    update_user_state,
    save_session_data,
    increment_retry_count,
    reset_retry_count
)
from app.services.gst_service import get_gst_service
from utils.validation_utils import validate_gstin, sanitize_input
from utils.constants import (
    ASK_GSTIN_MESSAGE,
    ERROR_INVALID_GSTIN,
    ERROR_MAX_RETRIES,
    MESSAGE_FETCHING_CAPTCHA
)
from utils.whatsapp_utils import create_text_message, create_image_message
from app.core.logging import get_logger, LogContext

logger = get_logger(__name__)

MAX_GSTIN_RETRIES = 3


async def handle_gstin_request(user_id: str) -> Dict[str, Any]:
    """
    Sends GSTIN request message.
    
    Args:
        user_id: User ID
    
    Returns:
        Response dict
    """
    with LogContext(user_id=user_id, state="ASK_GSTIN"):
        logger.info("Requesting GSTIN from user")
        
        # Update state
        await update_user_state(
            user_id,
            ConversationState.ASK_GSTIN,
            validate_transition=True
        )
        
        return {
            "status": "success",
            "message": create_text_message(ASK_GSTIN_MESSAGE),
            "next_state": ConversationState.ASK_GSTIN.value
        }


async def handle_gstin_input(user_id: str, gstin: str) -> Dict[str, Any]:
    """
    Handles GSTIN input from user.
    
    Args:
        user_id: User ID
        gstin: GSTIN provided by user
    
    Returns:
        Response dict with captcha image or error
    """
    with LogContext(user_id=user_id, state="ASK_GSTIN"):
        logger.info(f"Processing GSTIN input")
        
        try:
            # Sanitize input
            gstin = sanitize_input(gstin).strip().upper()
            
            # Validate GSTIN format
            if not validate_gstin(gstin):
                logger.warning(f"Invalid GSTIN format provided")
                
                # Increment retry count
                retry_count = await increment_retry_count(user_id)
                
                if retry_count >= MAX_GSTIN_RETRIES:
                    logger.error("Max GSTIN retries exceeded")
                    return {
                        "status": "error",
                        "message": create_text_message(ERROR_MAX_RETRIES),
                        "should_reset": True
                    }
                
                return {
                    "status": "error",
                    "message": create_text_message(
                        ERROR_INVALID_GSTIN.format(
                            remaining=MAX_GSTIN_RETRIES - retry_count
                        )
                    ),
                    "retry": True
                }
            
            # Reset retry count on success
            await reset_retry_count(user_id)
            
            # Save GSTIN to session
            await save_session_data(user_id, {"gstin": gstin})
            
            # Fetch captcha from GST service
            logger.info("Fetching captcha from GST portal")
            
            # Send "fetching" message
            yield {
                "status": "processing",
                "message": create_text_message(MESSAGE_FETCHING_CAPTCHA)
            }
            
            gst_service = get_gst_service()
            captcha_data = await gst_service.get_captcha(user_id)
            
            # Save session ID for verification
            await save_session_data(user_id, {
                "gst_session_id": captcha_data["session_id"]
            })
            
            # Update state to captcha verification
            await update_user_state(
                user_id,
                ConversationState.CAPTCHA_VERIFICATION,
                validate_transition=True
            )
            
            # Send captcha image
            logger.info("Captcha fetched successfully")
            
            from utils.constants import ASK_CAPTCHA_MESSAGE
            
            # First send the captcha image
            yield {
                "status": "success",
                "message": create_image_message(
                    image_url=captcha_data["captcha_image"],
                    caption="🔒 Please enter the captcha shown above"
                )
            }
            
            # Then send instructions
            yield {
                "status": "success",
                "message": create_text_message(ASK_CAPTCHA_MESSAGE),
                "next_state": ConversationState.CAPTCHA_VERIFICATION.value
            }
            
        except Exception as e:
            logger.error(f"Error processing GSTIN: {str(e)}", exc_info=True)
            
            return {
                "status": "error",
                "message": create_text_message(
                    f"❌ Error fetching captcha: {str(e)}\n\n"
                    "Please try again or type 'restart' to start over."
                ),
                "error": str(e)
            }
