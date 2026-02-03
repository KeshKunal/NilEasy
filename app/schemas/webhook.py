"""
app/schemas/webhook.py

Purpose: WhatsApp webhook payload schemas and parsers

- Validates incoming messages from Twilio and AiSensy
- Normalizes different formats into UnifiedMessage
- Ensures predictable request handling
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class UnifiedMessage(BaseModel):
    """
    Normalized message format for internal processing
    Works with both Twilio and AiSensy
    """
    phone: str = Field(..., description="User's phone number in E.164 format")
    name: str = Field(..., description="User's display name")
    text: str = Field(..., description="Message text content")
    message_id: str = Field(..., description="Unique message identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    platform: Literal["twilio", "aisensy"] = Field(..., description="Source platform")
    
    # Optional fields for buttons/replies
    button_id: Optional[str] = None
    button_text: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "phone": "+919876543210",
                "name": "John Doe",
                "text": "Hi",
                "message_id": "wamid.abc123",
                "platform": "twilio"
            }
        }


def parse_twilio_message(
    from_number: str,
    body: str,
    profile_name: Optional[str] = None,
    message_sid: Optional[str] = None
) -> UnifiedMessage:
    """
    Parses Twilio WhatsApp webhook payload
    
    Twilio format (form data):
    - From: whatsapp:+919876543210
    - Body: message text
    - ProfileName: User's name
    - MessageSid: wamid.abc123
    """
    # Remove 'whatsapp:' prefix if present
    phone = from_number.replace("whatsapp:", "")
    
    return UnifiedMessage(
        phone=phone,
        name=profile_name or phone,  # Fallback to phone if name not provided
        text=body,
        message_id=message_sid or f"twilio_{datetime.utcnow().timestamp()}",
        platform="twilio"
    )


def parse_aisensy_message(payload: dict) -> UnifiedMessage:
    """
    Parses AiSensy webhook payload
    
    AiSensy format (JSON):
    {
        "event": "message:in:new",
        "data": {
            "contact": {
                "phone": "919876543210",
                "name": "John Doe"
            },
            "message": {
                "text": "Hi",
                "id": "wamid.abc123"
            }
        }
    }
    """
    data = payload.get("data", {})
    contact = data.get("contact", {})
    message = data.get("message", {})
    
    phone = contact.get("phone", "")
    # Ensure E.164 format
    if not phone.startswith("+"):
        phone = f"+{phone}"
    
    return UnifiedMessage(
        phone=phone,
        name=contact.get("name", phone),
        text=message.get("text", ""),
        message_id=message.get("id", f"aisensy_{datetime.utcnow().timestamp()}"),
        platform="aisensy",
        button_id=message.get("button", {}).get("id"),
        button_text=message.get("button", {}).get("text")
    )


def detect_platform(request_data: dict) -> Literal["twilio", "aisensy"]:
    """
    Detects webhook platform based on payload structure
    
    Twilio: Has 'From', 'Body' fields (form data)
    AiSensy: Has 'event', 'data' fields (JSON)
    """
    if "From" in request_data or "Body" in request_data:
        return "twilio"
    elif "event" in request_data and "data" in request_data:
        return "aisensy"
    else:
        raise ValueError("Unknown webhook format")
