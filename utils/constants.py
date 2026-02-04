"""
utils/constants.py

Purpose: Centralized static content

- All user-facing messages (UX optimized for clarity and friendliness)
- Button labels
- Reusable enums and constants

(Prevents hardcoding across the codebase)
"""

# ============================================================
# WELCOME & ONBOARDING
# ============================================================

WELCOME_MESSAGE = """👋 *Welcome to GSTBuddy!*

I’ll help you file your NIL GST return using the official GST SMS method.

It’s *Quick* and *Simple*:
1️⃣ Verify your GSTIN
2️⃣ Choose return type & period
3️⃣ Tap and send a pre-filled SMS
That's it!

Let’s get started 😊

Please enter your *15-digit GSTIN*.
Example: 27ABCDE9603R1ZM"""

WELCOME_FIRST_TIME_MESSAGE = """👋 *Welcome to GSTBuddy!*

I’ll help you file your NIL GST return using the official GST SMS method.

It’s *Quick* and *Simple*:
1️⃣ Verify your GSTIN
2️⃣ Choose return type & period
3️⃣ Tap and send a pre-filled SMS
That's it!

Let’s get started 😊

Please enter your *15-digit GSTIN*.
Example: 27ABCDE9603R1ZM"""

HOW_IT_WORKS_MESSAGE = """📚 *How Nil Filing Works:*

*Step 1:* Share your GSTIN
*Step 2:* Verify with captcha
*Step 3:* Choose return type (GSTR-1/3B)
*Step 4:* Select filing period
*Step 5:* Send SMS to GST portal
*Step 6:* Confirm with OTP
*Step 7:* Done! Get ARN confirmation

🔐 *100% secure* - We never access your GST account
📱 *SMS-based* - Official government method
⏱️ *Quick* - 5-8 minutes total

Ready to file now?"""

START_BUTTON_TEXT = "🚀 Start Filing"
HOW_IT_WORKS_BUTTON = "ℹ️ How it Works"
FILE_AGAIN_BUTTON_TEXT = "📄 File Another Return"

# ============================================================
# GSTIN VERIFICATION FLOW
# ============================================================

ASK_GSTIN_MESSAGE = """*Step 1 of 8* 📍

Please enter your *15-digit GSTIN* number.

Example: 27AABCU9603R1ZM

💡 Make sure it's the GSTIN you want to file Nil return for."""

INVALID_GSTIN_MESSAGE = """❌ *Invalid GSTIN Format*

The GSTIN should be exactly *15 characters* with this format:
• First 2 digits: State code
• Next 10 characters: PAN
• Last 3 characters: Entity details

Example: 27AABCU9603R1ZM

Please try again."""

INVALID_GSTIN_RETRY_MESSAGE = """❌ *Still not quite right...*

GSTIN should be *15 alphanumeric characters*.

Need help? Type "help" or try again."""

GSTIN_SAVED_MESSAGE = """✅ *GSTIN Received*

Now fetching your business details from GST portal...

⏳ This will take just a moment."""

# ============================================================
# CAPTCHA & BUSINESS VERIFICATION
# ============================================================

CAPTCHA_REQUEST_MESSAGE = """*Step 2 of 8* 📍

To verify your GSTIN, please enter the *captcha code* shown in the image below.

💡 Tip: Look carefully - it's case-sensitive!"""

CAPTCHA_IMAGE_MESSAGE = "🔐 Please solve this captcha:"

CAPTCHA_INVALID_MESSAGE = """❌ *Incorrect Captcha*

No worries! Let's try again with a fresh captcha.

⏳ Loading new captcha..."""

VERIFICATION_IN_PROGRESS_MESSAGE = """⏳ *Verifying your GSTIN...*

Please wait while we fetch your business details from the GST portal.

This usually takes 5-10 seconds."""

VERIFICATION_FAILED_MESSAGE = """❌ *Verification Failed*

We couldn't verify your GSTIN. This could be because:
• Captcha was incorrect
• GSTIN not found in GST records
• Temporary GST portal issue

Would you like to try again?"""

BUSINESS_DETAILS_MESSAGE = """✅ *GSTIN Verified Successfully!*

📋 *Your Business Details:*
• *Trade Name:* {trade_name}
• *Legal Name:* {legal_name}
• *Status:* {status}
• *State:* {state}

Are these details correct?"""

BUSINESS_DETAILS_INCORRECT_MESSAGE = """No problem! Let's start over.

Please enter your GSTIN again."""

# ============================================================
# GST RETURN TYPE SELECTION
# ============================================================

SELECT_GST_TYPE_MESSAGE = """*Step 3 of 8* 📍

Which GST return do you want to file?

*GSTR-1:* Outward supplies (sales)
*GSTR-3B:* Summary return (monthly/quarterly)

💡 Most businesses file GSTR-3B regularly."""

GST_TYPE_INFO_MESSAGE = """📚 *Understanding GST Returns:*

*GSTR-1:*
• Details of outward supplies (sales)
• Filed monthly or quarterly
• Shows invoice-level data

*GSTR-3B:*
• Summary return of supplies
• Self-declaration of taxes
• Most common for Nil returns

Which one do you need to file?"""

GST_TYPE_OPTIONS = [
    {"id": "gstr1", "title": "GSTR-1", "description": "Outward supplies"},
    {"id": "gstr3b", "title": "GSTR-3B", "description": "Summary return"}
]

GST_TYPE_SAVED_MESSAGE = """✅ *{gst_type} selected*

Great! Now let's select the filing period."""

# ============================================================
# FILING PERIOD SELECTION
# ============================================================

SELECT_DURATION_MESSAGE = """*Step 4 of 8* 📍

For which period do you want to file Nil return?

Select the month or quarter below."""

DURATION_MONTHLY_MESSAGE = "*Select Month:*"
DURATION_QUARTERLY_MESSAGE = "*Select Quarter:*"

DURATION_OPTIONS = [
    {"id": "jan_2026", "title": "January 2026", "value": "012026"},
    {"id": "feb_2026", "title": "February 2026", "value": "022026"},
    {"id": "q4_2026", "title": "Q4 (Jan-Mar) 2026", "value": "Q42026"}
]

DURATION_SAVED_MESSAGE = """✅ *Period Selected: {period}*

Perfect! Now we're ready to generate your SMS."""

# ============================================================
# SMS GENERATION & SENDING
# ============================================================

SMS_INSTRUCTIONS_MESSAGE = """*Step 5 of 8* 📍

*📱 Time to send SMS to GST Portal*

I've prepared the exact SMS format for you.

⚠️ *IMPORTANT:*
• Send from your GST-registered mobile number
• Don't edit the SMS content
• Send exactly as shown

Click the button below to open your messaging app."""

SMS_CONTENT_PREFIX = "📩 *SMS Content (Copy this):*\n\n"

SMS_DEEP_LINK_MESSAGE = "👇 *Tap here to send SMS automatically*"

DO_NOT_EDIT_WARNING = """⚠️ *CRITICAL:* Do NOT edit the SMS!

Send it exactly as shown. Any changes will cause rejection."""

SMS_SENT_CONFIRMATION_MESSAGE = """Have you sent the SMS?

Wait for the SMS to be delivered before clicking 'Yes'."""

SMS_SENT_CONFIRMED_MESSAGE = """✅ *SMS Sent*

Great! You should receive an OTP within 30-120 seconds.

⏳ Please wait for the OTP message..."""

SMS_NOT_SENT_MESSAGE = """No worries! Take your time.

*Tips:*
• Make sure you have network coverage
• Check if SMS service is active
• Send from the number registered with GST

Try again when ready."""

SMS_HELP_MESSAGE = """📚 *Need Help with SMS?*

*Common Issues:*
❓ SMS not going through?
  → Check network coverage
  → Verify mobile balance

❓ Wrong mobile number?
  → Use GST-registered number only

❓ SMS got edited?
  → Regenerate and send fresh

Still stuck? Type 'help' for support."""

# ============================================================
# OTP WORKFLOW
# ============================================================

OTP_WAIT_MESSAGE = """*Step 6 of 8* 📍

⏳ *Waiting for OTP...*

You'll receive an OTP SMS from GST portal within *30-120 seconds*.

Once you receive it:
• Simply paste the entire message here
• Or type just the 6-digit OTP
• Or click "OTP Received" button"""

OTP_RECEIVED_MESSAGE = """✅ *OTP Confirmed!*

Perfect! Now we need to send the confirmation SMS."""

OTP_NOT_RECEIVED_MESSAGE = """😕 *OTP not received yet?*

Don't worry, this happens sometimes.

*Try these steps:*
1️⃣ Wait 2-3 more minutes
2️⃣ Check your SMS inbox
3️⃣ Verify you used the correct mobile number
4️⃣ Make sure the first SMS was delivered

💡 OTPs can take up to 5 minutes in some cases."""

OTP_EXPIRED_MESSAGE = """⏱️ *OTP Expired*

OTPs are valid for only 10 minutes.

Would you like to:
• Regenerate SMS and try again
• Get help from support"""

TROUBLESHOOTING_TIPS = """🔧 *Troubleshooting Tips:*

*OTP not received?*
✓ Wait 2-3 minutes
✓ Check registered mobile number
✓ Ensure first SMS was sent correctly
✓ Check if SMS inbox is full

*SMS failed?*
✓ Don't edit the SMS content
✓ Send from registered number only
✓ Check network connectivity

*Still having issues?*
Type 'support' to connect with our team."""

# ============================================================
# CONFIRMATION SMS
# ============================================================

CONFIRMATION_SMS_MESSAGE = """*Step 7 of 8* 📍

*📱 Send Confirmation SMS*

Now you need to send another SMS with the OTP.

Format: `NIL {gst_type} OTP`

I'll generate the exact SMS for you..."""

CONFIRMATION_SMS_CONTENT = """📩 *Confirmation SMS:*

Send this exact SMS:"""

CONFIRMATION_SENT_MESSAGE = """✅ *Confirmation Sent!*

Excellent! Your filing is being processed.

⏳ Please wait while GST portal generates your ARN..."""

# ============================================================
# COMPLETION & SUCCESS
# ============================================================

SUCCESS_MESSAGE = """🎉 *Congratulations!*

Your GST Nil return has been filed successfully!

✅ *ARN:* {arn} *(if available)*
✅ *Return:* {gst_type}
✅ *Period:* {period}
✅ *Filed On:* {timestamp}

📧 You'll receive a confirmation email from GST portal shortly."""

SUCCESS_WITHOUT_ARN_MESSAGE = """✅ *Filing Completed!*

Your Nil return has been filed successfully!

📋 *Details:*
• *Return:* {gst_type}
• *Period:* {period}
• *Status:* Submitted

📧 You'll receive ARN via email within 24 hours."""

# ============================================================
# ASPIRE PROMOTION
# ============================================================

ASPIRE_PROMOTION_MESSAGE = """💼 *Grow Your Business with Aspire!*

Since you're managing your GST, you might be interested in:

💰 *Business Loans* - Quick approval
💳 *Credit Cards* - For business expenses
📊 *Financial Tools* - Track & manage better

Want to learn more?"""

ASPIRE_PROMO_LEARN_MORE = "📱 Learn About Aspire"
ASPIRE_PROMO_NO_THANKS = "No Thanks"

# ============================================================
# ERROR HANDLING & SESSION
# ============================================================

SESSION_EXPIRED_MESSAGE = """⏱️ *Session Expired*

Your session timed out due to inactivity.

No worries! Your data is safe. Would you like to continue filing?"""

SESSION_RESUME_MESSAGE = """👋 *Welcome Back!*

I see you have an incomplete filing:
• *GSTIN:* {gstin}
• *Last Step:* {last_step}

Would you like to:
• Continue from where you left off
• Start fresh"""

GENERIC_ERROR_MESSAGE = """❌ *Something went wrong*

We encountered an unexpected error.

Don't worry - your progress is saved. Please try again in a moment.

If this persists, type 'support' for help."""

RATE_LIMIT_MESSAGE = """⏸️ *Please Slow Down*

You're sending messages too quickly!

Please wait a moment before trying again.

⏳ You can continue in {seconds} seconds."""

MAX_RETRIES_EXCEEDED_MESSAGE = """🛑 *Too Many Attempts*

You've tried this step multiple times.

Would you like to:
• Start over from beginning
• Get help from support team

We're here to help! 😊"""

# ============================================================
# HELP & SUPPORT
# ============================================================

HELP_MESSAGE = """💡 *Need Help?*

*Common Questions:*

❓ *What is Nil filing?*
When you have no GST transactions to report.

❓ *Is this official?*
Yes! We use the official GST SMS method.

❓ *Is my data safe?*
Absolutely. We never access your GST account.

❓ *How long does it take?*
Usually 5-8 minutes for the complete process.

*Still need help?*
Type 'support' to chat with our team."""

SUPPORT_CONTACT_MESSAGE = """📞 *Contact Support*

Our team is here to help!

*Options:*
📧 Email: support@nileasy.com
💬 Live Chat: Type 'agent'
📱 WhatsApp: +91-XXXXXXXXXX

*Working Hours:*
Monday-Saturday: 9 AM - 7 PM IST

We'll respond within 2-4 hours."""

CANCEL_CONFIRMATION_MESSAGE = """Are you sure you want to cancel?

Your progress will be lost.

• *Yes, cancel* - Start over later
• *No, continue* - Resume filing"""

# ============================================================
# BUTTON LABELS
# ============================================================

BUTTON_CONFIRM = "✅ Confirm"
BUTTON_CANCEL = "❌ Cancel"
BUTTON_YES = "Yes"
BUTTON_NO = "No"
BUTTON_CONTINUE = "Continue"
BUTTON_START_OVER = "Start Over"
BUTTON_RETRY = "Try Again"
BUTTON_HELP = "Get Help"
BUTTON_SMS_SENT = "✅ SMS Sent"
BUTTON_OTP_RECEIVED = "✅ OTP Received"
BUTTON_DETAILS_CORRECT = "✅ Correct, Continue"
BUTTON_DETAILS_INCORRECT = "❌ Incorrect Details"
BUTTON_REGENERATE = "🔄 Regenerate"

# ============================================================
# SYSTEM MESSAGES (Internal, less user-facing)
# ============================================================

PROCESSING_MESSAGE = "⏳ Processing..."
PLEASE_WAIT_MESSAGE = "Please wait a moment..."
LOADING_MESSAGE = "Loading..."

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
