"""
app/flow/handlers/sms.py

Handles: STEP 5 – SMS generation & confirmation

- Generates exact GST SMS content
- Creates deep link to messaging app
- Displays warnings not to edit SMS
- Tracks user confirmation of SMS sent
"""

from typing import Dict, Any

from app.flow.states import ConversationState
from app.services.session_service import update_user_state, get_session_data
from app.services.filing_service import get_filing_service, create_filing_attempt, update_filing_status
from utils.constants import (
    MESSAGE_SMS_INSTRUCTIONS,
    WARNING_SMS_EDIT,
    ASK_SMS_SENT_CONFIRMATION,
    BUTTON_SMS_SENT,
    BUTTON_SMS_HELP
)
from utils.whatsapp_utils import create_text_message, create_button_message
from utils.sms_utils import format_sms_instructions, get_gst_portal_number
from app.core.logging import get_logger, LogContext

logger = get_logger(__name__)


async def handle_sms_generation(user_id: str) -> Dict[str, Any]:
    """
    Generates SMS content and deep link for user.
    
    Args:
        user_id: User ID
    
    Returns:
        Response dict with SMS instructions
    """
    with LogContext(user_id=user_id, state="SMS_GENERATION"):
        logger.info("Generating SMS for filing")
        
        try:
            # Get session data
            session_data = await get_session_data(user_id)
            gstin = session_data.get("gstin")
            gst_type = session_data.get("gst_type")
            period = session_data.get("period")
            
            if not all([gstin, gst_type, period]):
                logger.error("Missing required data for SMS generation")
                return {
                    "status": "error",
                    "message": create_text_message(
                        "❌ Session data incomplete. Please restart."
                    ),
                    "should_reset": True
                }
            
            # Create filing attempt record
            filing_service = get_filing_service()
            attempt_id = await filing_service.create_filing_attempt(
                user_id=user_id,
                gstin=gstin,
                gst_type=gst_type,
                period=period
            )
            
            # Generate SMS instructions
            sms_data = format_sms_instructions(
                gstin=gstin,
                gst_type=gst_type,
                period=period,
                phone_number=get_gst_portal_number()
            )
            
            # Update state
            await update_user_state(
                user_id,
                ConversationState.SMS_GENERATION,
                validate_transition=True
            )
            
            # Send instructions
            yield {
                "status": "success",
                "message": create_text_message(MESSAGE_SMS_INSTRUCTIONS)
            }
            
            # Send formatted SMS with deep link
            sms_message = f"""📱 *Send this SMS to {sms_data['phone_number']}:*

```{sms_data['sms_content']}```

👇 Tap the button below to open your SMS app with this message pre-filled."""
            
            yield {
                "status": "success",
                "message": create_button_message(
                    text=sms_message,
                    buttons=[
                        {
                            "id": "open_sms",
                            "title": "📲 Open SMS App",
                            "url": sms_data["deep_link"]
                        }
                    ]
                )
            }
            
            # Send warning
            yield {
                "status": "success",
                "message": create_text_message(WARNING_SMS_EDIT)
            }
            
            # Update state to awaiting SMS confirmation
            await update_user_state(
                user_id,
                ConversationState.AWAITING_SMS_SENT,
                validate_transition=True
            )
            
            # Ask for confirmation
            yield {
                "status": "success",
                "message": create_button_message(
                    text=ASK_SMS_SENT_CONFIRMATION,
                    buttons=[
                        {"id": "sms_sent_yes", "title": BUTTON_SMS_SENT},
                        {"id": "sms_help", "title": BUTTON_SMS_HELP}
                    ]
                ),
                "next_state": ConversationState.AWAITING_SMS_SENT.value
            }
            
            logger.info("SMS instructions sent successfully")
            
        except Exception as e:
            logger.error(f"Error generating SMS: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": create_text_message(
                    f"❌ Error generating SMS: {str(e)}\n\nPlease try again."
                ),
                "error": str(e)
            }


async def handle_sms_confirmation(user_id: str, sent: bool) -> Dict[str, Any]:
    """
    Handles SMS sent confirmation.
    
    Args:
        user_id: User ID
        sent: True if user confirms SMS was sent
    
    Returns:
        Response dict
    """
    with LogContext(user_id=user_id, state="AWAITING_SMS_SENT"):
        logger.info(f"SMS confirmation: {sent}")
        
        if sent:
            # Update filing status
            filing_service = get_filing_service()
            await filing_service.update_filing_status(
                user_id=user_id,
                status="sms_sent"
            )
            
            # Move to OTP waiting
            from app.flow.handlers.otp import handle_otp_request
            return await handle_otp_request(user_id)
        else:
            # Show help/troubleshooting
            from utils.constants import MESSAGE_SMS_HELP
            return {
                "status": "info",
                "message": create_text_message(MESSAGE_SMS_HELP),
                "retry": True
            }
