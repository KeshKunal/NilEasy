"""
app/flow/dispatcher.py

Purpose: Central message dispatcher

- Receives normalized messages from webhook
- Routes to appropriate flow handler based on user state
- Sends responses via Twilio or AiSensy
- Manages conversation state transitions
"""

from typing import Dict, Any, Optional
from app.schemas.webhook import UnifiedMessage
from app.services.user_service import get_user_by_phone, create_user
from app.services.twilio_service import twilio_service
from app.flow.states import ConversationState
from app.core.logging import get_logger

logger = get_logger(__name__)


async def dispatch_message(message: UnifiedMessage, platform: str) -> Dict[str, Any]:
    """
    Main dispatcher for incoming WhatsApp messages
    
    Args:
        message: Normalized message object
        platform: "twilio" or "aisensy"
        
    Returns:
        Response dict
    """
    logger.info(f"Dispatching message from {message.phone} via {platform}")
    
    try:
        # Get or create user
        user = await get_user_by_phone(message.phone)
        
        if not user:
            # New user - create profile
            try:
                user = await create_user(
                    phone=message.phone,
                    name=message.name
                )
                logger.info(f"Created new user: {message.phone}")
            except Exception as create_error:
                # User might have been created by another request, try to get again
                logger.warning(f"Error creating user, attempting to retrieve: {create_error}")
                user = await get_user_by_phone(message.phone)
                if not user:
                    raise create_error
        
        # Get current conversation state
        current_state = user.get("current_state", ConversationState.WELCOME.value)
        logger.info(f"User state: {current_state}")
        
        # Route to appropriate handler based on state
        response = await route_to_handler(
            user_id=user["phone"],
            state=current_state,
            message_text=message.text,
            button_id=message.button_id
        )
        
        # Send response via appropriate platform
        await send_response(
            to_phone=message.phone,
            response=response,
            platform=platform
        )
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Dispatcher error: {e}", exc_info=True)
        
        # Send error message to user
        error_msg = "❌ Something went wrong. Please type 'start' to begin again."
        await send_response(
            to_phone=message.phone,
            response={"message": error_msg},
            platform=platform
        )
        
        return {"status": "error", "error": str(e)}


async def route_to_handler(
    user_id: str,
    state: str,
    message_text: str,
    button_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Routes message to appropriate handler based on conversation state
    
    Args:
        user_id: User's phone number
        state: Current conversation state
        message_text: User's message
        button_id: Optional button ID if user clicked a button
        
    Returns:
        Handler response
    """
    from app.flow.handlers import (
        welcome,
        gstin,
        captcha,
        gst_type,
        duration,
        sms,
        otp,
        completion
    )
    
    # Map states to handlers
    handlers = {
        ConversationState.WELCOME.value: welcome.handle_welcome,
        ConversationState.ASK_GSTIN.value: gstin.handle_gstin_input,
        ConversationState.ASK_CAPTCHA.value: captcha.handle_captcha,
        ConversationState.VERIFY_DETAILS.value: captcha.handle_details_confirmation,
        ConversationState.ASK_GST_TYPE.value: gst_type.handle_gst_type_selection,
        ConversationState.ASK_DURATION.value: duration.handle_duration_selection,
        ConversationState.SMS_GENERATION.value: sms.handle_sms_generation,
        ConversationState.AWAITING_OTP.value: otp.handle_otp_input,
        ConversationState.COMPLETED.value: completion.handle_completion,
    }
    
    handler = handlers.get(state)
    
    if not handler:
        logger.warning(f"No handler found for state: {state}")
        return {
            "message": "I'm not sure what to do here. Type 'start' to begin."
        }
    
    # Call handler
    try:
        # Pass button_id if available
        if button_id:
            response = await handler(user_id, message_text, button_id=button_id)
        else:
            response = await handler(user_id, message_text)
        
        return response
        
    except Exception as e:
        logger.error(f"Handler error: {e}", exc_info=True)
        return {
            "message": f"❌ Error: {str(e)}\n\nPlease try again or type 'start' to restart."
        }


async def send_response(
    to_phone: str,
    response: Dict[str, Any],
    platform: str
):
    """
    Sends response via appropriate platform
    
    Args:
        to_phone: Recipient phone
        response: Handler response dict
        platform: "twilio" or "aisensy"
    """
    message_text = response.get("message", "")
    
    if not message_text:
        logger.warning("Empty response message")
        return
    
    if platform == "twilio":
        # Send via Twilio
        result = await twilio_service.send_message(
            to_phone=to_phone,
            message=message_text
        )
        
        if not result["success"]:
            logger.error(f"Failed to send Twilio message: {result.get('error')}")
            
    elif platform == "aisensy":
        # TODO: Implement AiSensy sending
        # For now, just log
        logger.info(f"Would send via AiSensy to {to_phone}: {message_text[:50]}")
    
    else:
        logger.error(f"Unknown platform: {platform}")
