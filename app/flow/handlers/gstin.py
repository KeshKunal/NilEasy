"""
app/flow/handlers/gstin.py

Handles: STEP 1 – Ask GSTIN

- Accepts GSTIN input
- Validates format (via utils)
- Fetches captcha from GST portal
- Sends captcha image to user
"""

from typing import Dict, Any
from datetime import datetime

from app.flow.states import ConversationState
from app.db.mongo import get_users_collection
from app.services.gst_service import get_gst_service, GSTServiceError
from utils.validation_utils import validate_gstin
from app.core.logging import get_logger

logger = get_logger(__name__)

MAX_GSTIN_RETRIES = 3


async def handle_gstin_input(user_id: str, message: str, **kwargs) -> Dict[str, Any]:
    """
    Handles GSTIN input from user.
    
    Flow:
    1. Validate GSTIN format
    2. Fetch captcha from GST portal
    3. Send captcha image to user
    4. Update state to AWAITING_CAPTCHA
    
    Args:
        user_id: User's phone number
        message: GSTIN provided by user
        **kwargs: Additional parameters
    
    Returns:
        Response dict with captcha or error
    """
    logger.info(f"Processing GSTIN input for {user_id}")
    
    try:
        users = get_users_collection()
        
        # Sanitize input
        gstin = message.strip().upper()
        
        # Validate GSTIN format
        if not validate_gstin(gstin):
            logger.warning(f"Invalid GSTIN format provided: {gstin}")
            
            # Get current retry count
            user = await users.find_one({"phone": user_id})
            retry_count = user.get("session_data", {}).get("gstin_retries", 0) + 1
            
            # Update retry count
            await users.update_one(
                {"phone": user_id},
                {
                    "$set": {
                        "session_data.gstin_retries": retry_count,
                        "last_active": datetime.utcnow()
                    }
                }
            )
            
            if retry_count >= MAX_GSTIN_RETRIES:
                logger.error("Max GSTIN retries exceeded")
                return {
                    "message": """❌ *Too many invalid attempts*

You've exceeded the maximum retry limit.

Please type *Hi* to start over."""
                }
            
            remaining = MAX_GSTIN_RETRIES - retry_count
            return {
                "message": f"""❌ *Invalid GSTIN Format*

The GSTIN should be exactly *15 characters* with this format:
• First 2 digits: State code (01-37)
• Next 10 characters: PAN
• Last 3 characters: Entity details

Example: 27AABCU9603R1ZM

Please try again. ({remaining} attempts remaining)"""
            }
        
        # GSTIN is valid - fetch captcha from GST portal
        try:
            gst_service = get_gst_service()
            captcha_data = await gst_service.get_captcha(user_id)
            
            # Save GSTIN and captcha session to DB
            await users.update_one(
                {"phone": user_id},
                {
                    "$set": {
                        "gstin": gstin,
                        "current_state": ConversationState.AWAITING_CAPTCHA.value,
                        "session_data.gstin": gstin,
                        "session_data.gstin_retries": 0,
                        "session_data.captcha_session_id": captcha_data["session_id"],
                        "session_data.captcha_retries": 0,
                        "last_active": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"GSTIN saved, captcha fetched for {user_id}")
            
            # Construct public URL for captcha image
            from app.core.config import settings
            captcha_url = f"{settings.APP_URL}/api/v1/captcha/{captcha_data['image']}"
            
            # Return captcha image and instructions
            return {
                "message": f"""✅ *GSTIN Format Valid:* `{gstin}`

🔐 *Please solve the captcha below to verify your GSTIN.*

👉 Reply with the text shown in the image.""",
                "media_url": captcha_url,
                "media_type": "image"
            }
            
        except GSTServiceError as e:
            logger.error(f"GST service error: {e}")
            return {
                "message": f"""⚠️ *Unable to fetch captcha*

{str(e)}

Please try entering your GSTIN again."""
            }
        
    except Exception as e:
        logger.error(f"Error processing GSTIN: {str(e)}", exc_info=True)
        return {
            "message": f"❌ Error processing GSTIN: {str(e)}\n\nPlease try again or type *Hi* to restart."
        }
