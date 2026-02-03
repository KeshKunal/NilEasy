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
    logger.info(f"📨 Dispatching message from {message.phone} via {platform}")
    logger.info(f"   Message text: {message.text}")
    
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
                logger.info(f"✅ Created new user: {message.phone}")
            except Exception as create_error:
                # User might have been created by another request, try to get again
                logger.warning(f"⚠️ Error creating user, attempting to retrieve: {create_error}")
                user = await get_user_by_phone(message.phone)
                if not user:
                    raise create_error
        
        # Get current conversation state
        current_state = user.get("current_state", ConversationState.WELCOME.value)
        logger.info(f"🔄 User state: {current_state}")
        
        # Check for restart commands
        lower_text = message.text.lower().strip()
        if lower_text in ["hi", "hello", "start", "restart", "reset", "hey"]:
            current_state = ConversationState.WELCOME.value
            logger.info("↩️ Restart command detected, going to WELCOME")
        
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
        logger.error(f"❌ Dispatcher error: {e}", exc_info=True)
        
        # Send error message to user
        error_msg = "❌ Something went wrong. Please type *Hi* to begin again."
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
    from app.flow.handlers.welcome import handle_welcome
    from app.flow.handlers.gstin import handle_gstin_input
    from app.flow.handlers.captcha import handle_captcha_input, handle_confirmation
    from app.flow.handlers.gst_type import handle_gst_type_selection
    from app.flow.handlers.duration import handle_duration_selection
    from app.flow.handlers.sms import handle_sms_generation
    from app.flow.handlers.otp import handle_otp_input
    from app.flow.handlers.completion import handle_completion
    
    logger.info(f"🚦 Routing: state={state}, message={message_text[:50] if message_text else 'None'}")
    
    # State to handler mapping
    handler = None
    
    if state == ConversationState.WELCOME.value:
        handler = handle_welcome
    elif state == ConversationState.AWAITING_GSTIN.value:
        handler = handle_gstin_input
    elif state == ConversationState.AWAITING_CAPTCHA.value:
        handler = handle_captcha_input
    elif state == ConversationState.AWAITING_CONFIRMATION.value:
        handler = handle_confirmation
    elif state == ConversationState.AWAITING_GST_TYPE.value:
        handler = handle_gst_type_selection
    elif state == ConversationState.AWAITING_DURATION.value:
        handler = handle_duration_selection
    elif state == ConversationState.AWAITING_OTP.value:
        handler = handle_otp_input
    elif state == ConversationState.COMPLETED.value:
        # User is at completed state - handle post-completion responses
        from app.flow.handlers.completion import handle_post_completion
        handler = handle_post_completion
    elif state == ConversationState.SMS_GENERATION.value:
        # This is a transitional state, handle like OTP
        handler = handle_otp_input
    else:
        # Unknown state - try welcome
        logger.warning(f"⚠️ Unknown state: {state}, defaulting to WELCOME")
        handler = handle_welcome
    
    # Call handler
    try:
        logger.info(f"📞 Calling handler: {handler.__name__}")
        
        response = await handler(
            user_id=user_id,
            message=message_text,
            button_id=button_id
        )
        
        logger.info(f"✅ Handler returned: {str(response)[:100]}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Handler error: {e}", exc_info=True)
        return {
            "message": f"❌ Error: {str(e)}\n\nPlease try again or type *Hi* to restart."
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
    media_url = response.get("media_url")  # For captcha images, etc.
    
    if not message_text:
        logger.warning("⚠️ Empty response message")
        return
    
    logger.info(f"📤 Sending response to {to_phone} via {platform}")
    logger.info(f"   Message preview: {message_text[:100]}...")
    if media_url:
        logger.info(f"   Media URL: {media_url[:50] if len(media_url) > 50 else media_url}...")
    
    if platform == "twilio":
        # Send via Twilio
        result = await twilio_service.send_message(
            to_phone=to_phone,
            message=message_text,
            media_url=media_url
        )
        
        if result["success"]:
            logger.info(f"✅ Message sent via Twilio: SID={result.get('message_sid', 'N/A')}")
        else:
            logger.error(f"❌ Failed to send Twilio message: {result.get('error')}")
            
    elif platform == "aisensy":
        # TODO: Implement AiSensy sending
        logger.info(f"📬 Would send via AiSensy to {to_phone}")
    
    else:
        logger.error(f"❌ Unknown platform: {platform}")
