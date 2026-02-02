"""
app/flow/handlers/otp.py

Handles: STEP 6 & 7 – OTP and confirmation

- Handles OTP received / not received flows
- Extracts OTP from pasted messages (optional)
- Generates confirmation SMS format
- Handles retries and troubleshooting paths
"""

from typing import Dict, Any

from app.flow.states import ConversationState
from app.services.session_service import update_user_state, get_session_data, save_session_data
from app.services.filing_service import get_filing_service
from utils.constants import (
    ASK_OTP_MESSAGE,
    MESSAGE_OTP_NOT_RECEIVED,
    ERROR_INVALID_OTP,
    BUTTON_OTP_RECEIVED,
    BUTTON_OTP_NOT_RECEIVED
)
from utils.whatsapp_utils import create_text_message, create_button_message
from utils.validation_utils import extract_otp, validate_otp_format
from utils.sms_utils import build_gst_sms_content
from app.core.logging import get_logger, LogContext

logger = get_logger(__name__)


async def handle_otp_request(user_id: str) -> Dict[str, Any]:
    """
    Asks user if they received OTP.
    
    Args:
        user_id: User ID
    
    Returns:
        Response dict
    """
    with LogContext(user_id=user_id, state="AWAITING_OTP"):
        logger.info("Asking for OTP confirmation")
        
        # Update state
        await update_user_state(
            user_id,
            ConversationState.AWAITING_OTP,
            validate_transition=True
        )
        
        return {
            "status": "success",
            "message": create_button_message(
                text=ASK_OTP_MESSAGE,
                buttons=[
                    {"id": "otp_received", "title": BUTTON_OTP_RECEIVED},
                    {"id": "otp_not_received", "title": BUTTON_OTP_NOT_RECEIVED}
                ]
            ),
            "next_state": ConversationState.AWAITING_OTP.value
        }


async def handle_otp_response(user_id: str, received: bool) -> Dict[str, Any]:
    """
    Handles OTP received/not received response.
    
    Args:
        user_id: User ID
        received: True if OTP was received
    
    Returns:
        Response dict
    """
    with LogContext(user_id=user_id, state="AWAITING_OTP"):
        logger.info(f"OTP status: {'received' if received else 'not received'}")
        
        if received:
            # Update filing status
            filing_service = get_filing_service()
            await filing_service.update_filing_status(
                user_id=user_id,
                status="otp_received"
            )
            
            # Ask user to paste OTP
            await update_user_state(
                user_id,
                ConversationState.OTP_ENTRY,
                validate_transition=True
            )
            
            return {
                "status": "success",
                "message": create_text_message(
                    "🔑 *Please enter the 6-digit OTP*\n\n"
                    "You can paste the entire SMS message - I'll extract the OTP automatically!\n\n"
                    "👉 Just paste your SMS here and send."
                ),
                "next_state": ConversationState.OTP_ENTRY.value
            }
        else:
            # Show troubleshooting message
            return {
                "status": "info",
                "message": create_text_message(MESSAGE_OTP_NOT_RECEIVED),
                "retry": True
            }


async def handle_otp_input(user_id: str, otp_message: str) -> Dict[str, Any]:
    """
    Handles OTP input from user.
    
    Args:
        user_id: User ID
        otp_message: Message containing OTP
    
    Returns:
        Response dict with final SMS instructions
    """
    with LogContext(user_id=user_id, state="OTP_ENTRY"):
        logger.info("Processing OTP input")
        
        try:
            # Extract OTP from message
            otp = extract_otp(otp_message)
            
            if not otp or not validate_otp_format(otp):
                logger.warning("Invalid OTP format")
                return {
                    "status": "error",
                    "message": create_text_message(ERROR_INVALID_OTP),
                    "retry": True
                }
            
            # Save OTP to session
            await save_session_data(user_id, {"otp": otp})
            
            # Get session data for final SMS
            session_data = await get_session_data(user_id)
            gstin = session_data.get("gstin")
            gst_type = session_data.get("gst_type")
            period = session_data.get("period")
            
            # Generate final confirmation SMS
            final_sms = build_gst_sms_content(
                gstin=gstin,
                gst_type=gst_type,
                period=period,
                otp=otp
            )
            
            # Update state to final confirmation
            await update_user_state(
                user_id,
                ConversationState.FINAL_SMS_CONFIRMATION,
                validate_transition=True
            )
            
            from utils.sms_utils import create_sms_deep_link, get_gst_portal_number
            deep_link = create_sms_deep_link(get_gst_portal_number(), final_sms)
            
            # Send final SMS instructions
            yield {
                "status": "success",
                "message": create_text_message(
                    f"""✅ *OTP Received: {otp}*

📱 Now send this FINAL confirmation SMS:

```{final_sms}```

👇 Tap below to open SMS app:"""
                )
            }
            
            yield {
                "status": "success",
                "message": create_button_message(
                    text="🚨 *IMPORTANT:* Send this SMS exactly as shown. Do not edit!",
                    buttons=[
                        {
                            "id": "open_final_sms",
                            "title": "📲 Open SMS App",
                            "url": deep_link
                        }
                    ]
                )
            }
            
            # Ask for final confirmation
            from utils.constants import ASK_FINAL_CONFIRMATION, BUTTON_FILED_CONFIRM
            
            yield {
                "status": "success",
                "message": create_button_message(
                    text=ASK_FINAL_CONFIRMATION,
                    buttons=[
                        {"id": "filing_complete", "title": BUTTON_FILED_CONFIRM}
                    ]
                ),
                "next_state": ConversationState.FINAL_SMS_CONFIRMATION.value
            }
            
            logger.info("OTP processed, awaiting final confirmation")
            
        except Exception as e:
            logger.error(f"Error processing OTP: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": create_text_message(
                    f"❌ Error processing OTP: {str(e)}\n\nPlease try again."
                ),
                "error": str(e)
            }


async def handle_final_confirmation(user_id: str) -> Dict[str, Any]:
    """
    Handles final filing confirmation.
    
    Args:
        user_id: User ID
    
    Returns:
        Response dict with completion message
    """
    with LogContext(user_id=user_id, state="FINAL_SMS_CONFIRMATION"):
        logger.info("Processing final filing confirmation")
        
        # Update filing status to completed
        filing_service = get_filing_service()
        await filing_service.update_filing_status(
            user_id=user_id,
            status="completed"
        )
        
        # Move to completion
        from app.flow.handlers.completion import handle_completion
        return await handle_completion(user_id)
