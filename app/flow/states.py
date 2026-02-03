"""
app/flow/states.py

Purpose: Defines all conversation states

- Enum for each step in the flow
- Single source of truth for flow stages
"""

from enum import Enum


class ConversationState(str, Enum):
    """
    Defines all possible states in the GST filing conversation flow.
    Each state represents a specific step in the user journey.
    """
    
    # Step 0: Welcome/Start
    WELCOME = "WELCOME"
    
    # Step 1: GSTIN Input
    AWAITING_GSTIN = "AWAITING_GSTIN"
    
    # Step 2: Captcha Verification (optional)
    AWAITING_CAPTCHA = "AWAITING_CAPTCHA"
    
    # Step 2b: Confirm Business Details (optional)
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    
    # Step 3: GST Return Type Selection
    AWAITING_GST_TYPE = "AWAITING_GST_TYPE"
    
    # Step 4: Filing Period Selection
    AWAITING_DURATION = "AWAITING_DURATION"
    
    # Step 5: OTP Link Generation
    SMS_GENERATION = "SMS_GENERATION"
    
    # Step 6: OTP Entry
    AWAITING_OTP = "AWAITING_OTP"
    
    # Step 7: Filing Completed
    COMPLETED = "COMPLETED"
    
    # Error/Special states
    ERROR = "ERROR"
    SESSION_EXPIRED = "SESSION_EXPIRED"


# Valid state transitions
VALID_TRANSITIONS = {
    ConversationState.WELCOME: [
        ConversationState.AWAITING_GSTIN
    ],
    ConversationState.AWAITING_GSTIN: [
        ConversationState.AWAITING_CAPTCHA,
        ConversationState.AWAITING_GST_TYPE,  # Skip captcha in testing
        ConversationState.WELCOME  # Go back
    ],
    ConversationState.AWAITING_CAPTCHA: [
        ConversationState.AWAITING_CONFIRMATION,
        ConversationState.AWAITING_GST_TYPE,
        ConversationState.AWAITING_GSTIN  # Retry GSTIN
    ],
    ConversationState.AWAITING_CONFIRMATION: [
        ConversationState.AWAITING_GST_TYPE,
        ConversationState.AWAITING_GSTIN  # Go back
    ],
    ConversationState.AWAITING_GST_TYPE: [
        ConversationState.AWAITING_DURATION,
        ConversationState.AWAITING_GSTIN  # Go back
    ],
    ConversationState.AWAITING_DURATION: [
        ConversationState.SMS_GENERATION,
        ConversationState.AWAITING_OTP,  # Direct to OTP
        ConversationState.AWAITING_GST_TYPE  # Go back
    ],
    ConversationState.SMS_GENERATION: [
        ConversationState.AWAITING_OTP
    ],
    ConversationState.AWAITING_OTP: [
        ConversationState.COMPLETED,
        ConversationState.SMS_GENERATION  # Resend
    ],
    ConversationState.COMPLETED: [
        ConversationState.WELCOME  # Start over
    ],
    ConversationState.ERROR: [
        ConversationState.WELCOME
    ],
    ConversationState.SESSION_EXPIRED: [
        ConversationState.WELCOME
    ]
}


def is_valid_transition(from_state: ConversationState, to_state: ConversationState) -> bool:
    """Check if state transition is valid."""
    valid_next = VALID_TRANSITIONS.get(from_state, [])
    return to_state in valid_next


def get_step_number(state: ConversationState) -> int:
    """Get step number for progress display."""
    step_map = {
        ConversationState.WELCOME: 0,
        ConversationState.AWAITING_GSTIN: 1,
        ConversationState.AWAITING_CAPTCHA: 2,
        ConversationState.AWAITING_CONFIRMATION: 2,
        ConversationState.AWAITING_GST_TYPE: 3,
        ConversationState.AWAITING_DURATION: 4,
        ConversationState.SMS_GENERATION: 5,
        ConversationState.AWAITING_OTP: 6,
        ConversationState.COMPLETED: 7
    }
    return step_map.get(state, 0)
