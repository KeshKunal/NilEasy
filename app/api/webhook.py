"""
app/api/webhook.py

Purpose: Unified WhatsApp webhook endpoint

- Receives incoming messages from Twilio (testing) or AiSensy (production)
- Auto-detects platform based on request format
- Parses message payloads and normalizes them
- Passes control to the flow dispatcher
- Returns platform-compatible responses
"""

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import Response
from typing import Optional
import json

from app.core.logging import get_logger
from app.flow.dispatcher import dispatch_message
from app.schemas.webhook import UnifiedMessage, detect_platform, parse_twilio_message, parse_aisensy_message

logger = get_logger(__name__)
router = APIRouter()


@router.post("/webhook")
async def webhook_handler(
    request: Request,
    # Twilio sends form data
    From: Optional[str] = Form(None),
    Body: Optional[str] = Form(None),
    ProfileName: Optional[str] = Form(None),
    MessageSid: Optional[str] = Form(None),
):
    """
    Unified webhook endpoint for WhatsApp messages
    
    Supports:
    - Twilio WhatsApp (form data)
    - AiSensy (JSON payload)
    
    Automatically detects platform and routes accordingly.
    """
    try:
        # Check if it's Twilio (form data present) or AiSensy (JSON)
        if From is not None and Body is not None:
            # Twilio format (form data)
            logger.info(f"📱 Twilio webhook received from {From}")
            
            message = parse_twilio_message(
                from_number=From,
                body=Body,
                profile_name=ProfileName,
                message_sid=MessageSid
            )
            platform = "twilio"
            
        else:
            # AiSensy format (JSON)
            try:
                payload = await request.json()
                logger.info(f"📱 AiSensy webhook received: {payload}")
                
                message = parse_aisensy_message(payload)
                platform = "aisensy"
                
            except Exception as e:
                logger.error(f"Failed to parse JSON payload: {e}")
                raise HTTPException(status_code=400, detail="Invalid webhook payload")
        
        # Log normalized message
        logger.info(
            f"Normalized message - Platform: {platform}, "
            f"From: {message.phone}, Message: {message.text[:50]}"
        )
        
        # Dispatch to flow handler
        response = await dispatch_message(message, platform)
        
        # Return platform-specific response
        if platform == "twilio":
            # Twilio expects TwiML response (we'll send via API instead)
            return Response(content="<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response></Response>", media_type="application/xml")
        else:
            # AiSensy expects JSON
            return {"status": "success", "message": "Message processed"}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        
        # Return appropriate error response
        if From is not None:
            # Twilio
            return Response(content="<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response></Response>", media_type="application/xml")
        else:
            # AiSensy
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhook")
async def webhook_verification(request: Request):
    """
    Webhook verification endpoint (for platforms that require GET verification)
    """
    return {"status": "ok", "message": "Webhook endpoint is active"}
