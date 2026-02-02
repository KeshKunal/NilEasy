"""
app/flow/handlers/sms.py

Handles: STEP 5 – OTP Link generation & delivery

- Generates short HTTP link for OTP viewing
- Sends clickable link in WhatsApp
- Displays instructions to click link and return
- Tracks link click analytics
"""

from typing import Dict, Any

from app.flow.states import ConversationState
from app.services.session_service import update_user_state, get_session_data
from app.services.filing_service import get_filing_service, create_filing_attempt, update_filing_status
from app.services.sms_link_service import sms_link_service
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
    Generates OTP link and sends it to user via WhatsApp.
    
    Args:
        user_id: User ID (phone number)
    
    Returns:
        Response dict with link message
    """
    with LogContext(user_id=user_id, state="SMS_GENERATION"):
        logger.info("Generating OTP link for filing")
        
        try:
            # Get session data
            session_data = await get_session_data(user_id)
            gstin = session_data.get("gstin")
            gst_type = session_data.get("gst_type")
            period = session_data.get("period")
            phone = user_id  # User ID is the phone number
            
            if not all([gstin, gst_type, period]):
                logger.error("Missing required data for OTP link generation")
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
            
            # TODO: Call your GST service to initiate filing and get OTP
            # For now, using placeholder OTP
            # In production, call: otp = await gst_service.initiate_filing(gstin, gst_type, period)
            otp = "123456"  # Replace with actual OTP from GST service
            
            # Generate short link for OTP viewing
            link_result = await sms_link_service.create_otp_link(
                phone=phone,
                otp=otp,
                gstin=gstin,
                gst_type=gst_type,
                period=period,
                expiry_minutes=10
            )
            
            if not link_result["success"]:
                logger.error(f"Failed to create OTP link: {link_result.get('error')}")
                return {
                    "status": "error",
                    "message": create_text_message(
                        "❌ Failed to generate OTP link. Please try again."
                    ),
                    "error": link_result.get("error")
                }
            
            # Save link data to session
            await update_user_state(
                user_id,
                ConversationState.SMS_GENERATION,
                validate_transition=True,
                extra_data={
                    "otp_link": link_result["short_url"],
                    "otp_short_code": link_result["short_code"],
                    "otp_expires_at": link_result["expires_at"],
                    "otp_value": otp  # Store for verification
                }
            )
            
            # Send the link message (pre-formatted from service)
            yield {
                "status": "success",
                "message": create_text_message(link_result["display_message"])
            }
            
            # Update state to awaiting OTP
            await update_user_state(
                user_id,
                ConversationState.AWAITING_OTP,
                validate_transition=True
            )
            
            # Ask for OTP after user clicks link
            yield {
                "status": "success",
                "message": create_button_message(
                    text="After clicking the link and viewing your OTP, send it back to me here:",
                    buttons=[
                        {"id": "saw_otp_yes", "title": "✅ I saw the OTP"},
                        {"id": "link_issue", "title": "❌ Link not working"}
                    ]
                ),
                "next_state": ConversationState.AWAITING_OTP.value
            }
            
            logger.info(f"OTP link sent successfully: {link_result['short_url']}")
            
        except Exception as e:
            logger.error(f"Error generating OTP link: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": create_text_message(
                    f"❌ Error generating OTP link: {str(e)}\n\nPlease try again."
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
