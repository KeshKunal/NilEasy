"""
app/flow/handlers/otp.py

Handles: STEP 6 & 7 – OTP Guidance and Confirmation

Flow:
1. User sends SMS to 14409
2. GST portal sends OTP to user's registered mobile
3. User needs to send confirmation SMS: CNF <type> <OTP>
4. GST portal sends ARN confirmation

We guide the user through this process.
"""

from typing import Dict, Any
from datetime import datetime
from urllib.parse import quote

from app.flow.states import ConversationState
from app.db.mongo import get_users_collection
from app.services.sms_link_service import sms_link_service
from app.core.logging import get_logger

logger = get_logger(__name__)

GST_SMS_NUMBER = "14409"


def generate_confirmation_sms_text(gst_type: str, otp: str) -> str:
    """
    Generate confirmation SMS text.
    
    Format: CNF <Return Type> <OTP>
    
    Args:
        gst_type: "gstr1" or "gstr3b"
        otp: 6-digit OTP code
    
    Returns:
        SMS text like "CNF 3B 107543"
    """
    return_code = "R1" if gst_type == "gstr1" else "3B"
    return f"CNF {return_code} {otp}"


async def handle_otp_input(user_id: str, message: str, **kwargs) -> Dict[str, Any]:
    """
    Handles OTP flow - guides user through OTP receipt and confirmation.
    
    States:
    - User confirms SMS sent → Wait for OTP
    - User received OTP → Guide to send confirmation SMS
    - User sent confirmation → Ask about ARN
    - User received ARN → Complete
    
    Args:
        user_id: User's phone number
        message: User's response
        **kwargs: Additional parameters
    
    Returns:
        Response dict
    """
    logger.info(f"Processing OTP flow for {user_id}: {message}")
    
    try:
        users = get_users_collection()
        user = await users.find_one({"phone": user_id})
        
        if not user:
            return {
                "message": "❌ Session expired. Please type *Hi* to start over."
            }
        
        session_data = user.get("session_data", {})
        gst_type = session_data.get("gst_type", "gstr3b")
        gstin = user.get("gstin") or session_data.get("gstin")
        otp_stage = session_data.get("otp_stage", "sms_pending")
        
        response = message.strip().lower()
        
        # Handle based on current OTP stage
        if otp_stage == "sms_pending":
            # User hasn't confirmed SMS sent yet
            if response in ["1", "sent", "yes", "done"]:
                # User sent SMS - wait for OTP
                await users.update_one(
                    {"phone": user_id},
                    {
                        "$set": {
                            "session_data.sms_sent_at": datetime.utcnow(),
                            "session_data.otp_stage": "waiting_otp",
                            "last_active": datetime.utcnow()
                        }
                    }
                )
                
                return {
                    "message": """✅ *SMS Sent!*

⏳ You should receive an *OTP from GST* within 30-120 seconds.

The message will look like:
_"107543 is the CODE for Nil filing of GSTR3B for 07AQDPP8277H8Z6..."_

━━━━━━━━━━━━━━━━━━━━━

Once you receive the OTP, reply:
*1* - ✅ I received the OTP
*2* - ❌ Didn't receive OTP (wait 2 minutes first)"""
                }
            
            elif response in ["2", "help", "issue", "problem"]:
                # User needs help
                return {
                    "message": """❓ *Need Help?*

Common issues:

1️⃣ *SMS not sending?*
   • Make sure you're using your GST-registered mobile
   • Check your SMS app for the pre-filled message
   • Send to number: 14409

2️⃣ *Link not working?*
   • Copy this message manually and send to 14409:
   `{sms_text}`

3️⃣ *Wrong GSTIN/Period?*
   • Type *Hi* to start over

Reply *1* when you've sent the SMS.""".format(
                        sms_text=session_data.get("sms_text", "NIL 3B <GSTIN> <PERIOD>")
                    )
                }
            
            else:
                return {
                    "message": """⚠️ Please reply with:
*1* - ✅ SMS Sent
*2* - ❌ I need help"""
                }
        
        elif otp_stage == "waiting_otp":
            # User is waiting for OTP
            if response in ["1", "received", "got", "yes"]:
                # User received OTP - guide to send confirmation
                await users.update_one(
                    {"phone": user_id},
                    {
                        "$set": {
                            "session_data.otp_stage": "sending_confirmation",
                            "last_active": datetime.utcnow()
                        }
                    }
                )
                
                return_code = "R1" if gst_type == "gstr1" else "3B"
                
                return {
                    "message": f"""✅ *Great! You received the OTP!*

Now you need to *confirm the filing* by sending another SMS.

📱 *Send this to 14409:*

```
CNF {return_code} <YOUR_OTP>
```

Replace `<YOUR_OTP>` with the 6-digit code you received.

*Example:* If your OTP is 107543, send:
```
CNF {return_code} 107543
```

━━━━━━━━━━━━━━━━━━━━━

After sending the confirmation SMS, reply:
*1* - ✅ Confirmation SMS Sent
*2* - ❌ I need help"""
                }
            
            elif response in ["2", "no", "not received", "didnt"]:
                # User didn't receive OTP
                return {
                    "message": """⏳ *OTP Not Received?*

Please wait for 2-3 minutes. The GST portal can be slow sometimes.

*Troubleshooting:*
1️⃣ Check if SMS was sent from your *GST-registered mobile*
2️⃣ Verify the message format was correct
3️⃣ Check your SMS inbox for messages from VD-GSTIND

*Want to try again?*
Reply *retry* to get a fresh SMS link

*Still having issues?*
Reply *Hi* to start over"""
                }
            
            elif response == "retry":
                # Regenerate SMS link
                from app.flow.handlers.sms import handle_sms_generation
                await users.update_one(
                    {"phone": user_id},
                    {"$set": {"session_data.otp_stage": "sms_pending"}}
                )
                return await handle_sms_generation(user_id)
            
            else:
                return {
                    "message": """⚠️ Please reply with:
*1* - ✅ I received the OTP
*2* - ❌ Didn't receive OTP"""
                }
        
        elif otp_stage == "sending_confirmation":
            # User is sending confirmation SMS
            if response in ["1", "sent", "done", "yes"]:
                # User sent confirmation - wait for ARN
                await users.update_one(
                    {"phone": user_id},
                    {
                        "$set": {
                            "session_data.otp_stage": "waiting_arn",
                            "session_data.confirmation_sent_at": datetime.utcnow(),
                            "last_active": datetime.utcnow()
                        }
                    }
                )
                
                return {
                    "message": """✅ *Confirmation SMS Sent!*

⏳ You should receive the *ARN (Acknowledgment Reference Number)* shortly.

The success message will look like:
_"Your, 07AQDPP8277H8Z6, GSTR3B for tax period 022019 is filed successfully and ARN is AA..."_

━━━━━━━━━━━━━━━━━━━━━

Reply:
*1* - ✅ I received the ARN (Filing Complete!)
*2* - ❌ Didn't receive confirmation"""
                }
            
            elif response in ["2", "help", "issue"]:
                return_code = "R1" if gst_type == "gstr1" else "3B"
                
                return {
                    "message": f"""❓ *Help with Confirmation SMS*

Make sure you send:
```
CNF {return_code} <6-digit OTP>
```

to number *14409*

⚠️ *Important:*
• Use the exact OTP from the GST message
• OTP is valid for *30 minutes* only
• Send from your GST-registered mobile

Reply *1* when you've sent the confirmation."""
                }
            
            else:
                return {
                    "message": """⚠️ Please reply with:
*1* - ✅ Confirmation SMS Sent
*2* - ❌ I need help"""
                }
        
        elif otp_stage == "waiting_arn":
            # User is waiting for ARN
            if response in ["1", "received", "got", "yes", "done"]:
                # Filing complete!
                from app.flow.handlers.completion import handle_completion
                return await handle_completion(user_id)
            
            elif response in ["2", "no", "not received"]:
                return {
                    "message": """⏳ *ARN Not Received?*

The ARN confirmation usually arrives within seconds. If not received:

1️⃣ *Check your SMS inbox* for messages from VD-GSTIND
2️⃣ *Verify the confirmation SMS* was sent correctly
3️⃣ *Check if OTP was valid* (30-minute expiry)

If you received an error message, please share it here.

*To retry the entire process:*
Reply *Hi* to start over"""
                }
            
            else:
                return {
                    "message": """⚠️ Please reply with:
*1* - ✅ I received the ARN
*2* - ❌ Didn't receive confirmation"""
                }
        
        else:
            # Unknown stage - reset
            return {
                "message": "❌ Something went wrong. Please type *Hi* to start over."
            }
        
    except Exception as e:
        logger.error(f"Error in OTP handler: {str(e)}", exc_info=True)
        return {
            "message": f"❌ Error: {str(e)}\n\nPlease type *Hi* to restart."
        }
