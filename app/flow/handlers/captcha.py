"""
app/flow/handlers/captcha.py

Handles: STEP 2 – Captcha & GST detail verification

- Calls GST services using GSTIN + captcha
- Displays extracted business details
- Handles user confirmation or rejection
- Rolls back to GSTIN step if rejected
"""

from typing import Dict, Any

from app.flow.states import ConversationState
from app.services.session_service import (
    update_user_state,
    get_session_data,
    save_session_data,
    increment_retry_count,
    reset_retry_count
)
from app.services.user_service import update_user_gstin, update_business_details
from app.services.gst_service import get_gst_service
from utils.validation_utils import validate_captcha, sanitize_input
from utils.constants import (
    MESSAGE_VERIFYING_GSTIN,
    MESSAGE_GSTIN_VERIFIED,
    ASK_CONFIRM_DETAILS,
    ERROR_INVALID_CAPTCHA,
    ERROR_MAX_RETRIES,
    BUTTON_CONFIRM,
    BUTTON_RETRY
)
from utils.whatsapp_utils import create_text_message, create_button_message
from app.core.logging import get_logger, LogContext

logger = get_logger(__name__)

MAX_CAPTCHA_RETRIES = 5


async def handle_captcha_input(user_id: str, captcha: str) -> Dict[str, Any]:
    """
    Handles captcha input and verifies GSTIN details.
    
    Args:
        user_id: User ID
        captcha: Captcha text entered by user
    
    Returns:
        Response dict with business details or error
    """
    with LogContext(user_id=user_id, state="CAPTCHA_VERIFICATION"):
        logger.info("Processing captcha input")
        
        try:
            # Sanitize and validate captcha
            captcha = sanitize_input(captcha).strip()
            
            if not validate_captcha(captcha):
                logger.warning("Invalid captcha format")
                return {
                    "status": "error",
                    "message": create_text_message(
                        "⚠️ Invalid captcha format. Please enter the text as shown in the image."
                    ),
                    "retry": True
                }
            
            # Get GSTIN and session ID from session
            session_data = await get_session_data(user_id)
            gstin = session_data.get("gstin")
            gst_session_id = session_data.get("gst_session_id")
            
            if not gstin or not gst_session_id:
                logger.error("Missing GSTIN or session ID")
                return {
                    "status": "error",
                    "message": create_text_message(
                        "❌ Session expired. Please restart by typing 'Hi'."
                    ),
                    "should_reset": True
                }
            
            # Send verifying message
            yield {
                "status": "processing",
                "message": create_text_message(MESSAGE_VERIFYING_GSTIN)
            }
            
            # Verify GSTIN with GST portal
            gst_service = get_gst_service()
            
            try:
                details = await gst_service.verify_gstin(
                    user_id=user_id,
                    gstin=gstin,
                    captcha=captcha,
                    session_id=gst_session_id
                )
                
                # Reset retry count on success
                await reset_retry_count(user_id)
                
                # Save business details
                await update_user_gstin(user_id, gstin)
                await update_business_details(user_id, details)
                await save_session_data(user_id, {"business_details": details})
                
                # Format details for display
                details_text = MESSAGE_GSTIN_VERIFIED.format(
                    business_name=details.get("legal_name", "N/A"),
                    gstin=gstin,
                    status=details.get("status", "N/A"),
                    type=details.get("taxpayer_type", "N/A")
                )
                
                # Send details with confirmation buttons
                yield {
                    "status": "success",
                    "message": create_text_message(details_text)
                }
                
                # Update state to awaiting confirmation
                await update_user_state(
                    user_id,
                    ConversationState.AWAITING_CONFIRMATION,
                    validate_transition=True
                )
                
                yield {
                    "status": "success",
                    "message": create_button_message(
                        text=ASK_CONFIRM_DETAILS,
                        buttons=[
                            {"id": "confirm_yes", "title": BUTTON_CONFIRM},
                            {"id": "confirm_no", "title": BUTTON_RETRY}
                        ]
                    ),
                    "next_state": ConversationState.AWAITING_CONFIRMATION.value
                }
                
            except Exception as gst_error:
                # Handle GST service errors (invalid captcha, etc.)
                logger.warning(f"GST verification failed: {str(gst_error)}")
                
                retry_count = await increment_retry_count(user_id)
                
                if retry_count >= MAX_CAPTCHA_RETRIES:
                    logger.error("Max captcha retries exceeded")
                    yield {
                        "status": "error",
                        "message": create_text_message(ERROR_MAX_RETRIES),
                        "should_reset": True
                    }
                else:
                    # Fetch new captcha
                    captcha_data = await gst_service.get_captcha(user_id)
                    await save_session_data(user_id, {
                        "gst_session_id": captcha_data["session_id"]
                    })
                    
                    from utils.whatsapp_utils import create_image_message
                    
                    yield {
                        "status": "error",
                        "message": create_image_message(
                            image_url=captcha_data["captcha_image"],
                            caption=ERROR_INVALID_CAPTCHA.format(
                                remaining=MAX_CAPTCHA_RETRIES - retry_count
                            )
                        ),
                        "retry": True
                    }
                    
        except Exception as e:
            logger.error(f"Error in captcha handler: {str(e)}", exc_info=True)
            
            return {
                "status": "error",
                "message": create_text_message(
                    f"❌ Error verifying details: {str(e)}\n\n"
                    "Please type 'restart' to try again."
                ),
                "error": str(e)
            }


async def handle_confirmation(user_id: str, confirmed: bool) -> Dict[str, Any]:
    """
    Handles user confirmation of business details.
    
    Args:
        user_id: User ID
        confirmed: True if user confirmed, False to retry
    
    Returns:
        Response dict
    """
    with LogContext(user_id=user_id, state="AWAITING_CONFIRMATION"):
        logger.info(f"User {'confirmed' if confirmed else 'rejected'} details")
        
        if confirmed:
            # Move to next step - GST type selection
            from app.flow.handlers.gst_type import handle_gst_type_request
            return await handle_gst_type_request(user_id)
        else:
            # Go back to GSTIN input
            from app.flow.handlers.gstin import handle_gstin_request
            
            await update_user_state(
                user_id,
                ConversationState.ASK_GSTIN,
                validate_transition=False
            )
            
            return await handle_gstin_request(user_id)
