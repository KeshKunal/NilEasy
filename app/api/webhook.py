"""
app/api/webhook.py

Purpose: Single WhatsApp webhook endpoint

- Receives incoming WhatsApp/AiSensy events
- Parses message payloads
- Passes control to the flow dispatcher
- Returns WhatsApp-compatible responses
"""
