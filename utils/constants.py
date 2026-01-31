"""
utils/constants.py

Purpose: Centralized static content

- All user-facing messages
- Button labels
- Reusable enums and constants

(Prevents hardcoding across the codebase)
"""

# Welcome Messages
WELCOME_MESSAGE = """
👋 Welcome to NilEasy!

I'll help you file your GST Nil returns in just a few minutes through WhatsApp.

Let's get started! 🚀
"""

START_BUTTON_TEXT = "Start Filing"

# GSTIN Flow
ASK_GSTIN_MESSAGE = "Please share your 15-digit GSTIN number."
INVALID_GSTIN_MESSAGE = "❌ Invalid GSTIN format. Please enter a valid 15-character GSTIN."
GSTIN_SAVED_MESSAGE = "✅ GSTIN saved! Now please enter the captcha code."

# Captcha & Verification
CAPTCHA_REQUEST_MESSAGE = "Please enter the captcha code to verify your GSTIN."
VERIFICATION_FAILED_MESSAGE = "❌ Verification failed. Please try again."
BUSINESS_DETAILS_MESSAGE = """
✅ GSTIN Verified!

📋 Business Details:
• Trade Name: {trade_name}
• Legal Name: {legal_name}
• Status: {status}

Are these details correct?
"""

# GST Type Selection
SELECT_GST_TYPE_MESSAGE = "Please select the type of GST return you want to file:"
GST_TYPE_OPTIONS = [
    {"id": "gstr1", "title": "GSTR-1", "description": "Outward supplies"},
    {"id": "gstr3b", "title": "GSTR-3B", "description": "Summary return"}
]
GST_TYPE_SAVED_MESSAGE = "✅ {gst_type} selected."

# Duration Selection
SELECT_DURATION_MESSAGE = "Please select the filing period:"
DURATION_OPTIONS = [
    {"id": "jan", "title": "January 2026"},
    {"id": "feb", "title": "February 2026"},
    {"id": "q4", "title": "Q4 (Jan-Mar) 2026"}
]
DURATION_SAVED_MESSAGE = "✅ Period selected: {period}"

# SMS Flow
SMS_INSTRUCTIONS_MESSAGE = """
📱 Step 1: Send SMS to GST Portal

I've prepared the exact SMS format for you.
Click the link below to open your messaging app.
"""

DO_NOT_EDIT_WARNING = """
⚠️ IMPORTANT: Do NOT edit the SMS content!
Send it exactly as shown below.
"""

SMS_SENT_CONFIRMATION_MESSAGE = "Have you sent the SMS?"

# OTP Flow
OTP_RECEIVED_MESSAGE = "✅ Great! OTP received."
OTP_NOT_RECEIVED_MESSAGE = "😕 OTP not received yet?"
TROUBLESHOOTING_TIPS = """
💡 Troubleshooting Tips:
• Wait 2-3 minutes for OTP delivery
• Check your registered mobile number
• Ensure SMS was sent correctly
"""

CONFIRMATION_SMS_MESSAGE = """
📱 Step 2: Send Confirmation SMS

Now send the confirmation SMS with the OTP you received.
Format: CONFIRM <OTP>
"""

# Completion
SUCCESS_MESSAGE = """
🎉 Congratulations!

Your GST Nil return has been filed successfully!
ARN will be generated shortly.
"""

ASPIRE_PROMOTION_MESSAGE = """
💼 Grow your business with Aspire!

Get access to:
• Business loans
• Credit cards
• Financial management tools

Learn more: www.aspireapp.com
"""

FILE_AGAIN_BUTTON_TEXT = "📄 File Another Return"

# Error Messages
SESSION_EXPIRED_MESSAGE = "⏱️ Your session has expired. Please start again."
GENERIC_ERROR_MESSAGE = "❌ Something went wrong. Please try again."
