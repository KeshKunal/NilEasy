"""
app/services/twilio_service.py

Purpose: Twilio WhatsApp message sending

- Sends WhatsApp messages via Twilio API
- Supports text messages and media
- Used for testing before AiSensy production deployment
"""

import httpx
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class TwilioService:
    """Service for sending WhatsApp messages via Twilio"""
    
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.whatsapp_number = settings.TWILIO_WHATSAPP_NUMBER  # whatsapp:+14155238886
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}"
        
    async def send_message(
        self,
        to_phone: str,
        message: str,
        media_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends a WhatsApp message via Twilio
        
        Args:
            to_phone: Recipient phone (+919876543210)
            message: Message text
            media_url: Optional media URL for images/files
            
        Returns:
            {
                "success": True/False,
                "message_sid": "SMxxx...",
                "error": "Optional error message"
            }
        """
        try:
            # Ensure phone has whatsapp: prefix
            if not to_phone.startswith("whatsapp:"):
                to_phone = f"whatsapp:{to_phone}"
            
            # Prepare request
            url = f"{self.base_url}/Messages.json"
            
            data = {
                "From": self.whatsapp_number,
                "To": to_phone,
                "Body": message
            }
            
            if media_url:
                data["MediaUrl"] = media_url
            
            logger.info(f"📤 Sending Twilio message to {to_phone}")
            
            # Send via Twilio API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    data=data,
                    auth=(self.account_sid, self.auth_token),
                    timeout=10.0
                )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    logger.info(f"✅ Message sent: SID={result.get('sid')}")
                    
                    return {
                        "success": True,
                        "message_sid": result.get("sid"),
                        "status": result.get("status")
                    }
                else:
                    error_text = response.text
                    logger.error(f"❌ Twilio API error: {response.status_code} - {error_text}")
                    
                    return {
                        "success": False,
                        "error": f"Twilio API error: {response.status_code}"
                    }
                    
        except httpx.TimeoutException:
            logger.error("Twilio API timeout")
            return {
                "success": False,
                "error": "Twilio API timeout"
            }
        except Exception as e:
            logger.error(f"Error sending Twilio message: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_template_message(
        self,
        to_phone: str,
        template_name: str,
        variables: List[str]
    ) -> Dict[str, Any]:
        """
        Sends a WhatsApp template message (for approved templates)
        
        Note: Templates must be pre-approved by WhatsApp
        """
        # Template format: Your OTP is {{1}}
        # Variables: ["123456"]
        
        # Build message from template
        message = f"Template: {template_name}"
        for i, var in enumerate(variables, 1):
            message = message.replace(f"{{{{{i}}}}}", var)
        
        return await self.send_message(to_phone, message)
    
    def is_configured(self) -> bool:
        """Check if Twilio is properly configured"""
        return bool(
            self.account_sid 
            and self.auth_token 
            and self.whatsapp_number
            and self.account_sid != "your_twilio_sid"
        )


# Singleton instance
twilio_service = TwilioService()
