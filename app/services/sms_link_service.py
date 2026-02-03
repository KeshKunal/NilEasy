"""
app/services/sms_link_service.py

Purpose: SMS Short Link generation and analytics tracking
Uses https://sm-snacc.vercel.app/ API to create clickable links for OTP delivery

Why: WhatsApp doesn't support SMS:// protocol links, so we create HTTP links
that users can click to see their OTP and continue the filing process.
"""

import httpx
from typing import Dict, Any, Optional
from datetime import datetime
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SMSLinkService:
    """Service for generating shortened links for OTP delivery"""
    
    def __init__(self):
        self.api_url = settings.SMS_SHORTLINK_API_URL
        self.app_url = settings.APP_URL  # Your FastAPI base URL
        
    async def create_otp_link(
        self,
        phone: str,
        otp: str,
        gstin: str,
        gst_type: str,
        period: str,
        expiry_minutes: int = 10
    ) -> Dict[str, Any]:
        """
        Creates a shortened link for OTP delivery
        
        The link redirects to your app's callback endpoint which:
        1. Shows the OTP to the user
        2. Instructs them to return to WhatsApp
        3. Tracks the click
        
        Args:
            phone: User's phone number (+919876543210)
            otp: The OTP code from GST portal
            gstin: User's GSTIN
            gst_type: GSTR1 or GSTR3B
            period: Filing period (MMYYYY)
            expiry_minutes: Link expiry (default 10 minutes)
            
        Returns:
            {
                "success": True/False,
                "short_url": "https://sm-snacc.vercel.app/abc123",
                "short_code": "abc123",
                "expires_at": "ISO timestamp",
                "display_message": "Pre-formatted message to send in WhatsApp",
                "error": "Optional error message"
            }
        """
        try:
            # Create callback URL that will display the OTP
            # Format: https://yourapp.com/otp-callback?p=phone&o=otp&g=gstin&t=type&pr=period
            callback_url = (
                f"{self.app_url}/otp-callback"
                f"?p={phone}"
                f"&o={otp}"
                f"&g={gstin}"
                f"&t={gst_type}"
                f"&pr={period}"
            )
            
            logger.info(f"Creating OTP link for {phone}, GSTIN: {gstin}")
            
            # Call SMS Short Link API to shorten the callback URL
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.api_url}/api/create-link",
                    json={
                        "originalUrl": callback_url,
                        "expiryMinutes": expiry_minutes
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    short_url = data["shortUrl"]
                    
                    logger.info(f"✅ SMS link created: {short_url}")
                    
                    # Create user-friendly message
                    display_message = self._format_link_message(
                        gst_type=gst_type,
                        period=period,
                        short_url=short_url,
                        expiry_minutes=expiry_minutes
                    )
                    
                    return {
                        "success": True,
                        "short_url": short_url,
                        "short_code": data["shortCode"],
                        "expires_at": data["expiresAt"],
                        "display_message": display_message
                    }
                else:
                    error_text = response.text
                    logger.error(f"SMS link API error: {response.status_code} - {error_text}")
                    return {
                        "success": False,
                        "error": f"API returned status {response.status_code}"
                    }
                    
        except httpx.TimeoutException:
            logger.error("SMS link API timeout")
            return {
                "success": False,
                "error": "Link generation service timeout"
            }
        except httpx.RequestError as e:
            logger.error(f"Network error creating SMS link: {e}")
            return {
                "success": False,
                "error": "Network error connecting to link service"
            }
        except Exception as e:
            logger.error(f"Unexpected error creating SMS link: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_link_message(
        self,
        gst_type: str,
        period: str,
        short_url: str,
        expiry_minutes: int
    ) -> str:
        """
        Formats the WhatsApp message with the clickable link
        
        Returns:
            Pre-formatted message to send in WhatsApp
        """
        # Convert period to readable format
        month = period[:2]
        year = period[2:]
        month_names = {
            "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
            "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
            "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"
        }
        readable_period = f"{month_names.get(month, month)} {year}"
        
        message = f"""📱 *OTP Link Generated*

Filing: {gst_type}
Period: {readable_period}

🔗 Click this link to view your OTP:
{short_url}

⏱️ Link expires in {expiry_minutes} minutes

⚠️ *Important Instructions:*
1. Click the link above
2. Copy the OTP shown
3. Return to WhatsApp
4. Send me the OTP to continue

*Do not share this link with anyone!*"""
        
        return message
    
    async def get_link_analytics(self, short_code: str) -> Optional[Dict[str, Any]]:
        """
        Fetches click analytics for a specific short link
        
        Args:
            short_code: The short code (e.g., "abc123")
            
        Returns:
            {
                "success": True,
                "clicks": 3,
                "isExpired": False,
                ...
            } or None if failed
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.api_url}/api/analytics/{short_code}"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Link analytics for {short_code}: {data.get('clicks', 0)} clicks")
                    return data
                else:
                    logger.warning(f"Failed to get analytics for {short_code}: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching link analytics: {e}")
            return None
    
    async def check_link_clicked(self, short_code: str) -> bool:
        """
        Quick check if link has been clicked at least once
        
        Args:
            short_code: The short code to check
            
        Returns:
            True if clicked, False otherwise
        """
        analytics = await self.get_link_analytics(short_code)
        if analytics and analytics.get("success"):
            return analytics.get("clicks", 0) > 0
        return False


    async def create_sms_deep_link(
        self,
        sms_text: str,
        phone_number: str,
        user_phone: str
    ) -> Dict[str, Any]:
        """
        Creates a shortened link that redirects to SMS app with pre-filled message.
        
        Uses the SMS Shortlink Generator API at sm-snacc.vercel.app which creates
        a beautiful redirect page that opens the SMS app.
        
        Args:
            sms_text: The SMS body to pre-fill (e.g., "NIL 3B 29AACCF0683K1ZD 012026")
            phone_number: Destination SMS number (e.g., "14409")
            user_phone: User's phone for logging
            
        Returns:
            {
                "success": True/False,
                "short_url": "clickable URL like https://sm-snacc.vercel.app/s/abc123",
                "error": "optional error"
            }
        """
        try:
            logger.info(f"Creating SMS shortlink for {user_phone} to {phone_number}")
            
            # Call SMS Shortlink Generator API
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.api_url}/api/v1/shortlinks",
                    json={
                        "phone_number": phone_number,
                        "message": sms_text
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    short_url = data.get("short_url")
                    short_code = data.get("short_code")
                    
                    logger.info(f"✅ SMS shortlink created: {short_url} (code: {short_code})")
                    
                    return {
                        "success": True,
                        "short_url": short_url,
                        "short_code": short_code
                    }
                else:
                    error_msg = f"API returned status {response.status_code}"
                    logger.error(f"SMS shortlink API error: {error_msg}")
                    logger.error(f"Response: {response.text}")
                    
                    # Fallback to direct SMS URI
                    from urllib.parse import quote
                    sms_uri = f"sms:{phone_number}?body={quote(sms_text)}"
                    return {
                        "success": True,
                        "short_url": sms_uri,
                        "error": error_msg
                    }
                    
        except httpx.TimeoutException:
            logger.error("SMS shortlink API timeout")
            from urllib.parse import quote
            sms_uri = f"sms:{phone_number}?body={quote(sms_text)}"
            return {
                "success": True,
                "short_url": sms_uri,
                "error": "API timeout, using direct link"
            }
        except Exception as e:
            logger.error(f"Error creating SMS shortlink: {e}", exc_info=True)
            # Return direct SMS URI as fallback
            from urllib.parse import quote
            sms_uri = f"sms:{phone_number}?body={quote(sms_text)}"
            return {
                "success": True,
                "short_url": sms_uri,
                "error": str(e)
            }


# Singleton instance
sms_link_service = SMSLinkService()
