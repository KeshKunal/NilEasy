"""
app/flow/handlers/captcha.py

Handles: STEP 2 – Captcha & GST detail verification

- Verifies captcha with GST portal
- Fetches and displays business details
- Handles user confirmation
- Moves to GST type selection
"""

from typing import Dict, Any
from datetime import datetime

from app.flow.states import ConversationState
from app.db.mongo import get_users_collection
from app.services.gst_service import get_gst_service, GSTServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)

MAX_CAPTCHA_RETRIES = 3


async def handle_captcha_input(user_id: str, message: str, **kwargs) -> Dict[str, Any]:
    """
    Handles captcha input and verifies GSTIN with GST portal.
    
    Flow:
    1. Get stored GSTIN and session ID
    2. Call GST portal with captcha
    3. On success: Show business details, ask for confirmation
    4. On failure: Retry with new captcha
    
    Args:
        user_id: User's phone number
        message: Captcha text entered by user
        **kwargs: Additional parameters
    
    Returns:
        Response dict with business details or error
    """
    logger.info(f"Processing captcha input from {user_id}")
    
    try:
        users = get_users_collection()
        user = await users.find_one({"phone": user_id})
        
        if not user:
            return {
                "message": "❌ Session expired. Please type *Hi* to start over."
            }
        
        captcha = message.strip()
        
        # Basic validation
        if not captcha or len(captcha) < 3:
            return {
                "message": """⚠️ *Invalid Captcha*

Please enter the text exactly as shown in the captcha image.

👉 Reply with the captcha text."""
            }
        
        # Get session data
        session_data = user.get("session_data", {})
        gstin = user.get("gstin") or session_data.get("gstin")
        session_id = session_data.get("captcha_session_id")
        retry_count = session_data.get("captcha_retries", 0)
        
        if not gstin:
            return {
                "message": "❌ GSTIN not found. Please type *Hi* to start over."
            }
        
        if not session_id:
            return {
                "message": "❌ Captcha session expired. Please type *Hi* to start over."
            }
        
        # Verify with GST portal
        try:
            gst_service = get_gst_service()
            result = await gst_service.verify_gstin(
                user_id=user_id,
                gstin=gstin,
                captcha=captcha,
                session_id=session_id
            )
            
            if result.get("success"):
                # Verification successful - save business details
                business = result.get("business_details", {})
                
                await users.update_one(
                    {"phone": user_id},
                    {
                        "$set": {
                            "current_state": ConversationState.AWAITING_CONFIRMATION.value,
                            "session_data.business_details": business,
                            "session_data.captcha_verified": True,
                            "session_data.captcha_retries": 0,
                            "business_name": business.get("trade_name"),
                            "legal_name": business.get("legal_name"),
                            "state": business.get("state"),
                            "last_active": datetime.utcnow()
                        }
                    }
                )
                
                logger.info(f"GSTIN verified for {user_id}: {business.get('trade_name')}")
                
                # Show business details for confirmation
                trade_name = business.get("trade_name", "N/A")
                legal_name = business.get("legal_name", "N/A")
                status = business.get("status", "N/A")
                state = business.get("state", "N/A")
                
                return {
                    "message": f"""✅ *GSTIN Verified Successfully!*

🏢 *Business Details:*
━━━━━━━━━━━━━━━━━━━━━
📋 *Trade Name:* {trade_name}
📝 *Legal Name:* {legal_name}
🏛️ *Status:* {status}
📍 *State:* {state}
━━━━━━━━━━━━━━━━━━━━━

Please confirm these details are correct:

Reply:
*1* - ✅ Details are correct
*2* - ❌ Details are wrong (re-enter GSTIN)"""
                }
            else:
                raise GSTServiceError("Verification failed")
                
        except GSTServiceError as e:
            # Captcha verification failed
            retry_count += 1
            error_msg = str(e)
            
            if retry_count >= MAX_CAPTCHA_RETRIES:
                # Too many failed attempts - reset to GSTIN step
                await users.update_one(
                    {"phone": user_id},
                    {
                        "$set": {
                            "current_state": ConversationState.AWAITING_GSTIN.value,
                            "session_data.captcha_retries": 0,
                            "last_active": datetime.utcnow()
                        }
                    }
                )
                return {
                    "message": """❌ *Too many failed attempts*

Please enter your GSTIN again to get a new captcha."""
                }
            
            # Get new captcha for retry
            try:
                new_captcha_data = await gst_service.get_captcha(user_id)
                
                await users.update_one(
                    {"phone": user_id},
                    {
                        "$set": {
                            "session_data.captcha_session_id": new_captcha_data["session_id"],
                            "session_data.captcha_retries": retry_count,
                            "last_active": datetime.utcnow()
                        }
                    }
                )
                
                remaining = MAX_CAPTCHA_RETRIES - retry_count
                
                return {
                    "message": f"""❌ *{error_msg}*

🔄 Here's a new captcha. Please try again.

({remaining} attempts remaining)

👉 Reply with the text shown in the image.""",
                    "media_url": new_captcha_data["image"],
                    "media_type": "image"
                }
                
            except Exception as captcha_error:
                logger.error(f"Failed to get new captcha: {captcha_error}")
                return {
                    "message": f"""❌ *{error_msg}*

⚠️ Unable to generate new captcha. Please type *Hi* to start over."""
                }
        
    except Exception as e:
        logger.error(f"Error processing captcha: {str(e)}", exc_info=True)
        return {
            "message": f"❌ Error: {str(e)}\n\nPlease type *Hi* to restart."
        }


async def handle_confirmation(user_id: str, message: str, **kwargs) -> Dict[str, Any]:
    """
    Handles user confirmation of business details.
    
    Args:
        user_id: User's phone number
        message: User's response (1=confirm, 2=reject)
        **kwargs: Additional parameters
    
    Returns:
        Response dict
    """
    logger.info(f"Processing confirmation from {user_id}")
    
    try:
        users = get_users_collection()
        user = await users.find_one({"phone": user_id})
        
        if not user:
            return {
                "message": "❌ Session expired. Please type *Hi* to start over."
            }
        
        response = message.strip().lower()
        
        # Check for confirmation
        if response in ["1", "yes", "confirm", "correct", "ok"]:
            # Confirmed - move to GST type selection
            await users.update_one(
                {"phone": user_id},
                {
                    "$set": {
                        "current_state": ConversationState.AWAITING_GST_TYPE.value,
                        "session_data.details_confirmed": True,
                        "last_active": datetime.utcnow()
                    }
                }
            )
            
            return {
                "message": """✅ *Details Confirmed!*

Now, which GST return do you want to file?

Reply with:
*1* - GSTR-1 (Outward supplies)
*2* - GSTR-3B (Summary return)

💡 Most businesses file *GSTR-3B* for Nil returns."""
            }
        
        elif response in ["2", "no", "wrong", "incorrect", "reject"]:
            # Rejected - go back to GSTIN input
            await users.update_one(
                {"phone": user_id},
                {
                    "$set": {
                        "current_state": ConversationState.AWAITING_GSTIN.value,
                        "session_data": {},  # Clear session data
                        "last_active": datetime.utcnow()
                    }
                }
            )
            
            return {
                "message": """🔄 *No problem!*

Please enter your correct 15-digit GSTIN.

Example: 27AABCU9603R1ZM"""
            }
        
        else:
            return {
                "message": """⚠️ *Invalid response*

Please reply with:
*1* - ✅ Details are correct
*2* - ❌ Details are wrong"""
            }
        
    except Exception as e:
        logger.error(f"Error processing confirmation: {str(e)}", exc_info=True)
        return {
            "message": f"❌ Error: {str(e)}\n\nPlease type *Hi* to restart."
        }
