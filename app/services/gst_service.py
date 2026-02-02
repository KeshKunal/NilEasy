"""
app/services/gst_service.py

Purpose: GST system integration

- Handles GSTIN verification
- Captcha handling
- Fetches business details from GST APIs
- Abstracts GST logic from flow handlers
- Integrates with your existing GST verification service
"""

import httpx
from typing import Optional, Dict, Any
from app.core.config import settings
from app.core.logging import get_logger, LogContext
from datetime import datetime, timedelta
import asyncio

logger = get_logger(__name__)


class GSTServiceError(Exception):
    """Custom exception for GST service errors."""
    pass


class GSTService:
    """
    Service class for interacting with the GST verification API.
    Wraps your existing FastAPI GST tool.
    """
    
    def __init__(self):
        self.base_url = settings.GST_SERVICE_URL
        self.timeout = settings.GST_SERVICE_TIMEOUT
        self._client: Optional[httpx.AsyncClient] = None
        self._captcha_cache: Dict[str, Dict] = {}  # Session-based cache
    
    async def get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True
            )
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def get_captcha(self, user_id: str) -> Dict[str, str]:
        """
        Fetches captcha image from GST service.
        
        Args:
            user_id: User ID for session tracking
        
        Returns:
            Dict with sessionId and image (base64)
            
        Raises:
            GSTServiceError: If captcha fetch fails
        """
        with LogContext(user_id=user_id):
            try:
                logger.info("Fetching GST captcha", extra={"user_id": user_id})
                
                client = await self.get_client()
                response = await client.get(f"{self.base_url}/api/v1/getCaptcha")
                
                if response.status_code != 200:
                    logger.error(
                        f"Captcha fetch failed with status {response.status_code}",
                        extra={"response": response.text}
                    )
                    raise GSTServiceError("Failed to fetch captcha from GST portal")
                
                data = response.json()
                session_id = data.get("sessionId")
                image_data = data.get("image")
                
                if not session_id or not image_data:
                    raise GSTServiceError("Invalid captcha response format")
                
                # Cache the session for this user
                self._captcha_cache[user_id] = {
                    "session_id": session_id,
                    "created_at": datetime.utcnow(),
                    "attempts": 0
                }
                
                logger.info(
                    "Captcha fetched successfully",
                    extra={"user_id": user_id, "session_id": session_id}
                )
                
                return {
                    "session_id": session_id,
                    "image": image_data
                }
                
            except httpx.TimeoutException:
                logger.error("GST service timeout while fetching captcha")
                raise GSTServiceError("GST portal is taking too long to respond. Please try again.")
            except httpx.RequestError as e:
                logger.error(f"Network error while fetching captcha: {str(e)}")
                raise GSTServiceError("Unable to connect to GST portal. Please check your internet connection.")
            except Exception as e:
                logger.error(f"Unexpected error fetching captcha: {str(e)}", exc_info=True)
                raise GSTServiceError("An unexpected error occurred. Please try again.")
    
    async def verify_gstin(
        self,
        user_id: str,
        gstin: str,
        captcha: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verifies GSTIN with captcha using GST service.
        
        Args:
            user_id: User ID for tracking
            gstin: GSTIN to verify
            captcha: Captcha code entered by user
            session_id: Optional session ID (retrieved from cache if not provided)
        
        Returns:
            Dict with verification result and business details
            
        Raises:
            GSTServiceError: If verification fails
        """
        with LogContext(user_id=user_id, gstin=gstin):
            try:
                # Get session ID from cache if not provided
                if not session_id:
                    cached_session = self._captcha_cache.get(user_id)
                    if not cached_session:
                        raise GSTServiceError("No active captcha session. Please request a new captcha.")
                    
                    session_id = cached_session["session_id"]
                    
                    # Check if session is too old (15 minutes)
                    if datetime.utcnow() - cached_session["created_at"] > timedelta(minutes=15):
                        logger.warning("Captcha session expired", extra={"user_id": user_id})
                        del self._captcha_cache[user_id]
                        raise GSTServiceError("Captcha session expired. Please request a new captcha.")
                    
                    # Track attempts
                    cached_session["attempts"] += 1
                    if cached_session["attempts"] > 5:
                        logger.warning("Too many captcha attempts", extra={"user_id": user_id})
                        del self._captcha_cache[user_id]
                        raise GSTServiceError("Too many failed attempts. Please request a new captcha.")
                
                logger.info(
                    "Verifying GSTIN with captcha",
                    extra={"user_id": user_id, "gstin": gstin, "session_id": session_id}
                )
                
                client = await self.get_client()
                payload = {
                    "sessionId": session_id,
                    "GSTIN": gstin.upper(),
                    "captcha": captcha
                }
                
                response = await client.post(
                    f"{self.base_url}/api/v1/getGSTDetails",
                    json=payload
                )
                
                if response.status_code == 400:
                    error_detail = response.json().get("detail", "Invalid request")
                    logger.warning(
                        f"GSTIN verification failed: {error_detail}",
                        extra={"user_id": user_id, "gstin": gstin}
                    )
                    
                    if "Invalid session" in error_detail:
                        # Clear cache for this user
                        self._captcha_cache.pop(user_id, None)
                        raise GSTServiceError("Session expired. Please request a new captcha.")
                    
                    raise GSTServiceError(f"Verification failed: {error_detail}")
                
                if response.status_code != 200:
                    logger.error(
                        f"GST verification failed with status {response.status_code}",
                        extra={"response": response.text}
                    )
                    raise GSTServiceError("Failed to verify GSTIN. Please try again.")
                
                data = response.json()
                
                # Check if GST portal returned an error
                if "error" in data or data.get("sts") == "E":
                    error_msg = data.get("error", data.get("errorMsg", "Verification failed"))
                    logger.warning(
                        f"GST portal error: {error_msg}",
                        extra={"user_id": user_id, "gstin": gstin}
                    )
                    
                    if "Invalid Captcha" in error_msg or "captcha" in error_msg.lower():
                        raise GSTServiceError("Incorrect captcha. Please try again.")
                    elif "not found" in error_msg.lower() or "invalid gstin" in error_msg.lower():
                        raise GSTServiceError("GSTIN not found in GST records. Please check and try again.")
                    else:
                        raise GSTServiceError(f"Verification failed: {error_msg}")
                
                # Successful verification - extract business details
                taxpayer_info = data.get("pradr", {}) or data.get("tradeNam", {})
                
                business_details = {
                    "gstin": gstin.upper(),
                    "trade_name": data.get("tradeNam", "N/A"),
                    "legal_name": data.get("lgnm", "N/A"),
                    "status": data.get("sts", "N/A"),
                    "state": data.get("pradr", {}).get("addr", {}).get("stcd", "N/A") if isinstance(data.get("pradr"), dict) else "N/A",
                    "registration_date": data.get("rgdt", "N/A"),
                    "taxpayer_type": data.get("dty", "N/A"),
                    "constitution": data.get("ctb", "N/A"),
                }
                
                # Clear cache after successful verification
                self._captcha_cache.pop(user_id, None)
                
                logger.info(
                    "GSTIN verified successfully",
                    extra={
                        "user_id": user_id,
                        "gstin": gstin,
                        "trade_name": business_details["trade_name"]
                    }
                )
                
                return {
                    "success": True,
                    "business_details": business_details,
                    "raw_data": data  # Store raw data for debugging
                }
                
            except GSTServiceError:
                raise
            except httpx.TimeoutException:
                logger.error("GST service timeout during verification")
                raise GSTServiceError("GST portal is taking too long to respond. Please try again.")
            except httpx.RequestError as e:
                logger.error(f"Network error during verification: {str(e)}")
                raise GSTServiceError("Unable to connect to GST portal. Please check your internet connection.")
            except Exception as e:
                logger.error(f"Unexpected error during GSTIN verification: {str(e)}", exc_info=True)
                raise GSTServiceError("An unexpected error occurred. Please try again.")
    
    async def get_cached_session_id(self, user_id: str) -> Optional[str]:
        """
        Retrieves cached session ID for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Session ID if available and valid, None otherwise
        """
        cached = self._captcha_cache.get(user_id)
        if not cached:
            return None
        
        # Check if expired
        if datetime.utcnow() - cached["created_at"] > timedelta(minutes=15):
            del self._captcha_cache[user_id]
            return None
        
        return cached["session_id"]
    
    def clear_session_cache(self, user_id: str):
        """Clears captcha session cache for a user."""
        self._captcha_cache.pop(user_id, None)
        logger.debug(f"Cleared captcha cache for user {user_id}")


# Global GST service instance
_gst_service: Optional[GSTService] = None


def get_gst_service() -> GSTService:
    """
    Get or create the global GST service instance.
    
    Returns:
        GSTService instance
    """
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
