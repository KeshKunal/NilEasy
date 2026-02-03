"""
app/flow/handlers/welcome.py

Handles: STEP 0 – Entry / Welcome

- Processes "Hi" / CTA entry
- Sends welcome message and start options
- Initializes session state
"""

from typing import Dict, Any
from datetime import datetime

from app.flow.states import ConversationState
from app.db.mongo import get_users_collection
from app.core.logging import get_logger

logger = get_logger(__name__)


async def handle_welcome(user_id: str, message: str) -> Dict[str, Any]:
    """
    Handles welcome message and initializes user session.
    
    Args:
        user_id: User's phone number
        message: User's message (typically "Hi" or button click)
    
    Returns:
        Response dict with message payload
    """
    logger.info(f"Processing welcome interaction for {user_id}")
    
    try:
        # Update user state to ASK_GSTIN (next step)
        users = get_users_collection()
        await users.update_one(
            {"phone": user_id},
            {
                "$set": {
                    "current_state": ConversationState.ASK_GSTIN.value,
                    "last_active": datetime.utcnow(),
                    "session_data": {}  # Reset session
                }
            }
        )
        
        # Send welcome message
        welcome_text = """👋 Welcome to NilEasy!

I'll help you file NIL returns for your GST registration quickly and easily.

The process takes just 2-3 minutes:
1️⃣ Verify your GSTIN
2️⃣ Solve a simple captcha
3️⃣ Select GST type & period
4️⃣ Get OTP link
5️⃣ Submit OTP
6️⃣ Done! ✅

Let's get started! Please enter your 15-digit GSTIN."""
        
        logger.info("Welcome message sent successfully")
        
        return {
            "message": welcome_text
        }
        
    except Exception as e:
        logger.error(f"Error in welcome handler: {str(e)}", exc_info=True)
        
        return {
            "message": "❌ Oops! Something went wrong. Please type 'Hi' to restart."
        }
