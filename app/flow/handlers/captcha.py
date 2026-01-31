"""
app/flow/handlers/captcha.py

Handles: STEP 2 – Captcha & GST detail verification

- Calls GST services using GSTIN + captcha
- Displays extracted business details
- Handles user confirmation or rejection
- Rolls back to GSTIN step if rejected
"""
