"""
app/services/gst_service.py

Purpose: GST system integration - Direct GST Portal Access

- Fetches captcha directly from GST portal
- Verifies GSTIN with captcha
- Fetches business details
- No separate service needed - all integrated
"""

import httpx
import base64
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.core.logging import get_logger

logger = get_logger(__name__)

# GST Portal URLs
GST_PORTAL_BASE = "https://services.gst.gov.in"
GST_CAPTCHA_URL = f"{GST_PORTAL_BASE}/services/captcha"
GST_SEARCH_URL = f"{GST_PORTAL_BASE}/services/api/search/taxpayerDetails"
GST_SEARCH_PAGE = f"{GST_PORTAL_BASE}/services/searchtp"


class GSTServiceError(Exception):
    """Custom exception for GST service errors."""
    pass


class GSTService:
    """
    Service class for directly interacting with GST Portal.
    Handles captcha fetching and GSTIN verification.
    """
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}  # User session storage
        self._captcha_images: Dict[str, bytes] = {}  # Store raw captcha images for serving
        self._timeout = 30.0
    
    async def get_captcha(self, user_id: str) -> Dict[str, str]:
        """
        Fetches captcha image directly from GST portal.
        
        Args:
            user_id: User ID for session tracking
        
        Returns:
            Dict with session_id and image_url (public URL to fetch image)
            
        Raises:
            GSTServiceError: If captcha fetch fails
        """
        try:
            logger.info(f"Fetching GST captcha for user {user_id}")
            
            # Create new session for this user
            session_id = str(uuid.uuid4())
            
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                # First, hit the search page to initialize cookies
                await client.get(GST_SEARCH_PAGE)
                
                # Then fetch the captcha
                captcha_response = await client.get(GST_CAPTCHA_URL)
                
                if captcha_response.status_code != 200:
                    logger.error(f"Captcha fetch failed: {captcha_response.status_code}")
                    raise GSTServiceError("Failed to fetch captcha from GST portal")
                
                # Store raw captcha bytes for serving via our API
                # Use phone number without + for URL safety
                safe_user_id = user_id.replace("+", "")
                self._captcha_images[safe_user_id] = captcha_response.content
                
                # Store cookies for this session
                self._sessions[user_id] = {
                    "session_id": session_id,
                    "cookies": dict(client.cookies),
                    "created_at": datetime.utcnow(),
                    "attempts": 0,
                    "safe_user_id": safe_user_id
                }
                
                logger.info(f"Captcha fetched successfully for {user_id}, session: {session_id[:8]}...")
                
                return {
                    "session_id": session_id,
                    "image": safe_user_id  # Return the user ID to construct URL
                }
                
        except httpx.TimeoutException:
            logger.error("GST portal timeout while fetching captcha")
            raise GSTServiceError("GST portal is taking too long to respond. Please try again.")
        except httpx.RequestError as e:
            logger.error(f"Network error fetching captcha: {e}")
            raise GSTServiceError("Unable to connect to GST portal. Please check your internet connection.")
        except GSTServiceError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching captcha: {e}", exc_info=True)
            raise GSTServiceError("An unexpected error occurred. Please try again.")
    
    async def verify_gstin(
        self,
        user_id: str,
        gstin: str,
        captcha: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verifies GSTIN with captcha using GST portal.
        
        Args:
            user_id: User ID for tracking
            gstin: GSTIN to verify
            captcha: Captcha code entered by user
            session_id: Optional session ID (uses cached if not provided)
        
        Returns:
            Dict with verification result and business details
            
        Raises:
            GSTServiceError: If verification fails
        """
        try:
            # Get user's session
            user_session = self._sessions.get(user_id)
            
            if not user_session:
                raise GSTServiceError("No active captcha session. Please request a new captcha.")
            
            # Check if session is expired (15 minutes)
            if datetime.utcnow() - user_session["created_at"] > timedelta(minutes=15):
                logger.warning(f"Session expired for {user_id}")
                del self._sessions[user_id]
                raise GSTServiceError("Captcha session expired. Please request a new captcha.")
            
            # Track attempts
            user_session["attempts"] += 1
            if user_session["attempts"] > 5:
                logger.warning(f"Too many attempts for {user_id}")
                del self._sessions[user_id]
                raise GSTServiceError("Too many failed attempts. Please request a new captcha.")
            
            logger.info(f"Verifying GSTIN {gstin} for {user_id}")
            
            # Prepare request
            payload = {
                "gstin": gstin.upper(),
                "captcha": captcha
            }
            
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                cookies=user_session.get("cookies", {})
            ) as client:
                # First hit search page to maintain session
                await client.get(GST_SEARCH_PAGE)
                
                # Then submit verification
                response = await client.post(GST_SEARCH_URL, json=payload)
                
                if response.status_code != 200:
                    logger.error(f"GST verification failed: {response.status_code}")
                    raise GSTServiceError("Failed to verify GSTIN. Please try again.")
                
                data = response.json()
                
                # Log the raw response for debugging
                logger.info(f"GST Portal Response: {data}")
                
                # Check for errors in response
                if "error" in data or data.get("sts") == "E" or data.get("errorcd") or data.get("errorMsg"):
                    error_msg = data.get("error", data.get("errorMsg", data.get("message", "Verification failed")))
                    logger.warning(f"GST portal error: {error_msg}")
                    
                    if "captcha" in str(error_msg).lower() or "Invalid Captcha" in str(error_msg):
                        raise GSTServiceError("Incorrect captcha. Please try again.")
                    elif "not found" in str(error_msg).lower() or "invalid gstin" in str(error_msg).lower():
                        raise GSTServiceError("GSTIN not found in GST records. Please check and try again.")
                    else:
                        raise GSTServiceError(f"Verification failed: {error_msg}")
                
                # Check if the response has any meaningful taxpayer data
                # If key fields like lgnm (legal name) or tradeNam are missing, 
                # the captcha/GSTIN verification likely failed silently
                if not data.get("tradeNam") and not data.get("lgnm"):
                    logger.warning(f"GST portal returned empty/invalid data for {gstin}: {data}")
                    raise GSTServiceError("Verification failed. The captcha may be incorrect. Please try again.")
                
                # Extract business details
                business_details = self._extract_business_details(gstin, data)
                
                # Clear session after successful verification
                del self._sessions[user_id]
                
                logger.info(f"GSTIN verified successfully: {business_details.get('trade_name')}")
                
                return {
                    "success": True,
                    "business_details": business_details,
                    "raw_data": data
                }
                
        except GSTServiceError:
            raise
        except httpx.TimeoutException:
            logger.error("GST portal timeout during verification")
            raise GSTServiceError("GST portal is taking too long. Please try again.")
        except httpx.RequestError as e:
            logger.error(f"Network error during verification: {e}")
            raise GSTServiceError("Unable to connect to GST portal.")
        except Exception as e:
            logger.error(f"Unexpected error during verification: {e}", exc_info=True)
            raise GSTServiceError("An unexpected error occurred. Please try again.")
    
    def _extract_business_details(self, gstin: str, data: Dict) -> Dict[str, Any]:
        """Extract business details from GST response."""
        
        # Handle address extraction - GST portal returns complex address structure
        address = "N/A"
        if isinstance(data.get("pradr"), dict):
            addr_data = data["pradr"].get("adr", "")
            # Sometimes adr is a string, sometimes it's nested
            if isinstance(addr_data, str):
                address = addr_data
            elif isinstance(addr_data, dict):
                # Build address from components
                parts = []
                for key in ['bno', 'bnm', 'st', 'loc', 'dst', 'stcd', 'pncd']:
                    if addr_data.get(key):
                        parts.append(str(addr_data[key]))
                address = ', '.join(parts) if parts else "N/A"
            # Fallback: try to get the address string directly
            if address == "N/A" and data["pradr"].get("addr"):
                address = data["pradr"]["addr"].get("adr", "N/A")
        
        return {
            "gstin": gstin.upper(),
            "trade_name": data.get("tradeNam", "N/A"),
            "legal_name": data.get("lgnm", "N/A"),
            "status": data.get("sts", "N/A"),
            "address": address,
            "registration_date": data.get("rgdt", "N/A"),
            "taxpayer_type": data.get("dty", "N/A"),
            "constitution": data.get("ctb", "N/A"),
        }
    
    async def get_cached_session_id(self, user_id: str) -> Optional[str]:
        """Get cached session ID for user if valid."""
        session = self._sessions.get(user_id)
        if not session:
            return None
        
        # Check expiry
        if datetime.utcnow() - session["created_at"] > timedelta(minutes=15):
            del self._sessions[user_id]
            return None
        
        return session["session_id"]
    
    def clear_session_cache(self, user_id: str):
        """Clear captcha session for user."""
        self._sessions.pop(user_id, None)
        # Also clear captcha image
        safe_user_id = user_id.replace("+", "")
        self._captcha_images.pop(safe_user_id, None)
        logger.debug(f"Cleared session cache for {user_id}")
    
    def get_captcha_image(self, user_id: str) -> Optional[bytes]:
        """
        Get stored captcha image bytes for serving via HTTP.
        
        Args:
            user_id: User ID (without + prefix)
        
        Returns:
            Raw image bytes or None if not found
        """
        return self._captcha_images.get(user_id)
    
    async def close(self):
        """Cleanup (for compatibility)."""
        self._sessions.clear()
        self._captcha_images.clear()


# Global GST service instance
_gst_service: Optional[GSTService] = None


def get_gst_service() -> GSTService:
    """Get or create the global GST service instance."""
    global _gst_service
    if _gst_service is None:
        _gst_service = GSTService()
    return _gst_service


async def close_gst_service():
    """Close GST service and cleanup resources."""
    global _gst_service
    if _gst_service:
        await _gst_service.close()
        _gst_service = None
