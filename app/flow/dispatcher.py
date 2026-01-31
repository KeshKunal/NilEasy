"""
app/flow/dispatcher.py

Purpose: Central flow router

- Reads the user's current_state
- Dispatches incoming input to the correct handler
- Prevents invalid state transitions
- Ensures users cannot skip steps
"""
