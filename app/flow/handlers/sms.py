"""
app/flow/handlers/sms.py

Handles: STEP 5 – SMS Deep Link Generation

- Generates the NIL filing SMS text
- Creates clickable deep link for SMS app
- Format: NIL <R1/3B> <GSTIN> <PERIOD>
- Target number: 14409
"""

from typing import Dict, Any
from datetime import datetime
from urllib.parse import quote

from app.flow.states import ConversationState
from app.db.mongo import get_users_collection
from app.services.sms_link_service import sms_link_service
from app.core.logging import get_logger

logger = get_logger(__name__)

# GST SMS destination number
GST_SMS_NUMBER = "14409"


def generate_nil_sms_text(gst_type: str, gstin: str, period: str) -> str:
    """
    Generate the exact SMS text for GST Nil filing.
    
    Format: NIL <Return Type> <GSTIN> <Period>
    
    Args:
        gst_type: "gstr1" or "gstr3b"
        gstin: 15-digit GSTIN
        period: Period in MMYYYY format
    
    Returns:
        SMS text like "NIL R1 07AQDPP8277H8Z6 042020"
    """
    # Convert return type to SMS format
    return_code = "R1" if gst_type == "gstr1" else "3B"
    
    # Format: NIL <type> <GSTIN> <period>
    return f"NIL {return_code} {gstin} {period}"


def generate_sms_deep_link(sms_text: str, phone_number: str = GST_SMS_NUMBER) -> str:
    """
    Generate SMS deep link.
    
    Args:
        sms_text: Pre-filled SMS body
        phone_number: Destination phone number
    
    Returns:
        sms: URI format link
    """
    # URL encode the SMS body
    encoded_body = quote(sms_text)
    return f"sms:{phone_number}?body={encoded_body}"


async def handle_sms_generation(user_id: str, **kwargs) -> Dict[str, Any]:
    """
    Generates SMS deep link for GST Nil filing and sends to user.
    
    This creates a clickable link that opens the SMS app with:
    - Pre-filled destination: 14409
    - Pre-filled message: NIL <type> <GSTIN> <period>
    
    Args:
        user_id: User's phone number
        **kwargs: Additional parameters
    
    Returns:
        Response dict with SMS link
    """
    logger.info(f"Generating SMS link for {user_id}")
    
    try:
        users = get_users_collection()
        user = await users.find_one({"phone": user_id})
        
        if not user:
            return {
                "message": "❌ Session expired. Please type *Hi* to start over."
            }
        
        # Get filing details from session
        session_data = user.get("session_data", {})
        gstin = user.get("gstin") or session_data.get("gstin")
        gst_type = session_data.get("gst_type", "gstr3b")
        period = session_data.get("period")
        period_display = session_data.get("period_display", period)
        
        if not all([gstin, gst_type, period]):
            logger.error("Missing required data for SMS generation")
            return {
                "message": "❌ Session data incomplete. Please type *Hi* to start over."
            }
        
        # Generate SMS text
        sms_text = generate_nil_sms_text(gst_type, gstin, period)
        
        # Generate SMS deep link
        sms_deep_link = generate_sms_deep_link(sms_text)
        
        # Try to create short link using service (for WhatsApp compatibility)
        try:
            link_result = await sms_link_service.create_sms_deep_link(
                sms_text=sms_text,
                phone_number=GST_SMS_NUMBER,
                user_phone=user_id
            )
            
            if link_result.get("success"):
                short_url = link_result.get("short_url")
                logger.info(f"Short link created: {short_url}")
            else:
                # Fallback to direct SMS link
                short_url = sms_deep_link
                logger.warning("Could not create short link, using direct SMS URI")
        except Exception as e:
            logger.warning(f"Short link service error: {e}, using direct SMS URI")
            short_url = sms_deep_link
        
        # Update state to AWAITING_OTP
        await users.update_one(
            {"phone": user_id},
            {
                "$set": {
                    "current_state": ConversationState.AWAITING_OTP.value,
                    "session_data.sms_text": sms_text,
                    "session_data.sms_link": short_url,
                    "session_data.sms_sent_at": None,  # Will be updated when user confirms
                    "last_active": datetime.utcnow()
                }
            }
        )
        
        # Format display
        gst_type_display = "GSTR-1" if gst_type == "gstr1" else "GSTR-3B"
        return_code = "R1" if gst_type == "gstr1" else "3B"
        
        return {
            "message": f"""📋 *Nil Filing SMS Ready!*

*GSTIN:* `{gstin}`
*Return Type:* {gst_type_display}
*Period:* {period_display}

━━━━━━━━━━━━━━━━━━━━━

📱 *Send this SMS to 14409:*

```
{sms_text}
```

👆 *Click the link below to open your SMS app with the message pre-filled:*

🔗 {short_url}

━━━━━━━━━━━━━━━━━━━━━

⚠️ *IMPORTANT:*
• Send from your *GST-registered mobile number* only
• Do *NOT* modify the message
• After sending, you'll receive an OTP from GST

━━━━━━━━━━━━━━━━━━━━━

After sending the SMS, reply:
*1* - ✅ SMS Sent, waiting for OTP
*2* - ❌ I need help"""
        }
        
    except Exception as e:
        logger.error(f"Error generating SMS link: {str(e)}", exc_info=True)
        return {
            "message": f"❌ Error generating SMS: {str(e)}\n\nPlease type *Hi* to restart."
        }
