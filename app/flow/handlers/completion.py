"""
app/flow/handlers/completion.py

Handles: STEP 8 – Success & Promotion

- Confirms successful filing (ARN received)
- Sends success message with celebration
- Promotes Aspire products
- Ends or resets the session
"""

from typing import Dict, Any
from datetime import datetime

from app.flow.states import ConversationState
from app.db.mongo import get_users_collection
from app.core.logging import get_logger

logger = get_logger(__name__)


async def handle_completion(user_id: str, **kwargs) -> Dict[str, Any]:
    """
    Handles successful filing completion.
    
    Args:
        user_id: User's phone number
        **kwargs: Additional parameters
    
    Returns:
        Response dict with success message and promotion
    """
    logger.info(f"Processing completion for {user_id}")
    
    try:
        users = get_users_collection()
        user = await users.find_one({"phone": user_id})
        
        if not user:
            return {
                "message": "❌ Session expired. Please type *Hi* to start over."
            }
        
        # Get filing details for summary
        session_data = user.get("session_data", {})
        gstin = user.get("gstin") or session_data.get("gstin")
        gst_type = session_data.get("gst_type", "gstr3b")
        period_display = session_data.get("period_display", session_data.get("period"))
        business_name = user.get("business_name") or session_data.get("business_details", {}).get("trade_name", "")
        
        gst_type_display = "GSTR-1" if gst_type == "gstr1" else "GSTR-3B"
        
        # Create filing record for history
        filing_record = {
            "gstin": gstin,
            "gst_type": gst_type,
            "gst_type_display": gst_type_display,
            "period": session_data.get("period"),
            "period_display": period_display,
            "completed_at": datetime.utcnow(),
            "status": "success"
        }
        
        # Update to completed state
        await users.update_one(
            {"phone": user_id},
            {
                "$set": {
                    "current_state": ConversationState.COMPLETED.value,
                    "last_active": datetime.utcnow(),
                    "last_filing_at": datetime.utcnow()
                },
                "$push": {
                    "filing_history": filing_record
                },
                "$inc": {
                    "total_filings": 1
                }
            }
        )
        
        logger.info(f"Filing completed successfully for {user_id}")
        
        # Build success message with promotion
        business_line = f"\n🏢 *Business:* {business_name}" if business_name else ""
        
        return {
            "message": f"""🎉 *Congratulations!*

Your Nil Return has been filed successfully!

━━━━━━━━━━━━━━━━━━━━━
📋 *Filing Summary*
━━━━━━━━━━━━━━━━━━━━━
📄 *Return Type:* {gst_type_display}
📅 *Period:* {period_display}
🔢 *GSTIN:* `{gstin}`{business_line}
✅ *Status:* Filed Successfully
━━━━━━━━━━━━━━━━━━━━━

📌 *Save the ARN* from your SMS for future reference.

━━━━━━━━━━━━━━━━━━━━━

💡 *Need help with compliance, loans, or business growth?*

Check out *ASPIRE* - Financial solutions designed for small businesses like yours:

✅ Quick Business Loans
✅ GST Filing Services  
✅ Accounting & Compliance
✅ Business Growth Tools

🔗 Visit: aspire.io/small-business

━━━━━━━━━━━━━━━━━━━━━

Reply:
*1* - 🚀 Explore Aspire
*2* - 📋 File another return
*3* - 🏁 Done for now

Thank you for using *NilEasy*! 🙏"""
        }
        
    except Exception as e:
        logger.error(f"Error processing completion: {str(e)}", exc_info=True)
        return {
            "message": f"❌ Error: {str(e)}\n\nPlease type *Hi* to restart."
        }


async def handle_post_completion(user_id: str, message: str, **kwargs) -> Dict[str, Any]:
    """
    Handles user responses after completion.
    
    Args:
        user_id: User's phone number
        message: User's choice
        **kwargs: Additional parameters
    
    Returns:
        Response dict
    """
    response = message.strip().lower()
    
    if response in ["1", "aspire", "explore"]:
        return {
            "message": """🚀 *Explore ASPIRE*

ASPIRE offers comprehensive solutions for small businesses:

💰 *Business Loans*
Quick approvals, competitive rates

📊 *GST Services*
Filing, compliance, returns

📈 *Growth Solutions*
Marketing, analytics, expansion

🔗 *Visit:* aspire.io/small-business

To file another return, type *Hi*"""
        }
    
    elif response in ["2", "file", "another"]:
        # Start new filing
        from app.flow.handlers.welcome import handle_welcome
        return await handle_welcome(user_id, "hi")
    
    elif response in ["3", "done", "exit", "bye"]:
        return {
            "message": """👋 *Thank you for using NilEasy!*

Your filing is complete. Have a great day!

Type *Hi* anytime to file another return. 🙏"""
        }
    
    else:
        return {
            "message": """Please reply with:
*1* - 🚀 Explore Aspire
*2* - 📋 File another return
*3* - 🏁 Done for now

Or type *Hi* to start a new filing."""
        }
