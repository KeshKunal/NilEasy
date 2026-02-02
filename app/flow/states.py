"""
app/flow/states.py

Purpose: Defines all conversation states

- Enum or constants for each step in the flow
  (WELCOME, ASK_GSTIN, GST_VERIFIED, OTP_RECEIVED, COMPLETED, etc.)
- Single source of truth for flow stages
- State transition validation
- Metadata for each state (timeout, retries, etc.)
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass


class ConversationState(str, Enum):
    """
    Defines all possible states in the GST filing conversation flow.
    Each state represents a specific step in the user journey.
    """
    
    # Initial states
    WELCOME = "WELCOME"
    
    # GSTIN verification flow
    ASK_GSTIN = "ASK_GSTIN"
    CAPTCHA_VERIFICATION = "CAPTCHA_VERIFICATION"
    GST_VERIFIED = "GST_VERIFIED"
    
    # Filing details collection
    SELECT_GST_TYPE = "SELECT_GST_TYPE"
    SELECT_DURATION = "SELECT_DURATION"
    
    # SMS workflow
    SMS_GENERATION = "SMS_GENERATION"
    SMS_SENT_CONFIRMATION = "SMS_SENT_CONFIRMATION"
    
    # OTP workflow
    AWAIT_OTP = "AWAIT_OTP"
    OTP_RECEIVED = "OTP_RECEIVED"
    AWAIT_CONFIRMATION_SMS = "AWAIT_CONFIRMATION_SMS"
    
    # Completion
    COMPLETED = "COMPLETED"
    
    # Error/Reset states
    ERROR = "ERROR"
    SESSION_EXPIRED = "SESSION_EXPIRED"


@dataclass
class StateMetadata:
    """
    Metadata associated with each conversation state.
    Helps in managing state-specific behavior.
    """
    name: ConversationState
    display_name: str
    step_number: Optional[int] = None  # For progress tracking
    total_steps: int = 8  # Total steps in happy path
    timeout_minutes: int = 30  # State-specific timeout
    max_retries: int = 3  # Maximum retry attempts
    requires_user_input: bool = True  # Whether state waits for user input
    can_go_back: bool = False  # Whether user can navigate back
    description: str = ""  # Internal description


# State metadata configuration
STATE_METADATA: Dict[ConversationState, StateMetadata] = {
    ConversationState.WELCOME: StateMetadata(
        name=ConversationState.WELCOME,
        display_name="Welcome",
        step_number=0,
        timeout_minutes=60,
        max_retries=1,
        description="Entry point - welcome message and start button"
    ),
    ConversationState.ASK_GSTIN: StateMetadata(
        name=ConversationState.ASK_GSTIN,
        display_name="Enter GSTIN",
        step_number=1,
        timeout_minutes=15,
        max_retries=5,
        description="Collect and validate GSTIN"
    ),
    ConversationState.CAPTCHA_VERIFICATION: StateMetadata(
        name=ConversationState.CAPTCHA_VERIFICATION,
        display_name="Verify Captcha",
        step_number=2,
        timeout_minutes=10,
        max_retries=5,
        description="Captcha verification and business details confirmation"
    ),
    ConversationState.GST_VERIFIED: StateMetadata(
        name=ConversationState.GST_VERIFIED,
        display_name="GSTIN Verified",
        step_number=2,
        timeout_minutes=30,
        max_retries=1,
        requires_user_input=False,
        description="GSTIN successfully verified"
    ),
    ConversationState.SELECT_GST_TYPE: StateMetadata(
        name=ConversationState.SELECT_GST_TYPE,
        display_name="Select Return Type",
        step_number=3,
        timeout_minutes=15,
        max_retries=3,
        can_go_back=True,
        description="Select GST return type (GSTR-1 or GSTR-3B)"
    ),
    ConversationState.SELECT_DURATION: StateMetadata(
        name=ConversationState.SELECT_DURATION,
        display_name="Select Period",
        step_number=4,
        timeout_minutes=15,
        max_retries=3,
        can_go_back=True,
        description="Select filing period (monthly/quarterly)"
    ),
    ConversationState.SMS_GENERATION: StateMetadata(
        name=ConversationState.SMS_GENERATION,
        display_name="Generate SMS",
        step_number=5,
        timeout_minutes=20,
        max_retries=5,
        description="Generate and display SMS for GST portal"
    ),
    ConversationState.SMS_SENT_CONFIRMATION: StateMetadata(
        name=ConversationState.SMS_SENT_CONFIRMATION,
        display_name="Confirm SMS Sent",
        step_number=5,
        timeout_minutes=10,
        max_retries=5,
        description="User confirms SMS was sent"
    ),
    ConversationState.AWAIT_OTP: StateMetadata(
        name=ConversationState.AWAIT_OTP,
        display_name="Waiting for OTP",
        step_number=6,
        timeout_minutes=5,
        max_retries=5,
        description="Wait for user to receive and share OTP"
    ),
    ConversationState.OTP_RECEIVED: StateMetadata(
        name=ConversationState.OTP_RECEIVED,
        display_name="OTP Received",
        step_number=6,
        timeout_minutes=5,
        max_retries=1,
        requires_user_input=False,
        description="OTP received from user"
    ),
    ConversationState.AWAIT_CONFIRMATION_SMS: StateMetadata(
        name=ConversationState.AWAIT_CONFIRMATION_SMS,
        display_name="Send Confirmation",
        step_number=7,
        timeout_minutes=5,
        max_retries=5,
        description="User sends confirmation SMS with OTP"
    ),
    ConversationState.COMPLETED: StateMetadata(
        name=ConversationState.COMPLETED,
        display_name="Completed",
        step_number=8,
        timeout_minutes=60,
        max_retries=1,
        description="Filing successfully completed"
    ),
    ConversationState.ERROR: StateMetadata(
        name=ConversationState.ERROR,
        display_name="Error",
        timeout_minutes=30,
        max_retries=3,
        description="Error state for recovery"
    ),
    ConversationState.SESSION_EXPIRED: StateMetadata(
        name=ConversationState.SESSION_EXPIRED,
        display_name="Session Expired",
        timeout_minutes=5,
        max_retries=1,
        description="Session timeout - restart flow"
    ),
}


# Valid state transitions - prevents users from skipping steps
STATE_TRANSITIONS: Dict[ConversationState, List[ConversationState]] = {
    ConversationState.WELCOME: [
        ConversationState.ASK_GSTIN,
        ConversationState.SESSION_EXPIRED
    ],
    ConversationState.ASK_GSTIN: [
        ConversationState.CAPTCHA_VERIFICATION,
        ConversationState.ASK_GSTIN,  # Retry on invalid input
        ConversationState.ERROR,
        ConversationState.SESSION_EXPIRED
    ],
    ConversationState.CAPTCHA_VERIFICATION: [
        ConversationState.GST_VERIFIED,
        ConversationState.SELECT_GST_TYPE,  # Direct transition if auto-confirmed
        ConversationState.ASK_GSTIN,  # Go back if details incorrect
        ConversationState.CAPTCHA_VERIFICATION,  # Retry captcha
        ConversationState.ERROR,
        ConversationState.SESSION_EXPIRED
    ],
    ConversationState.GST_VERIFIED: [
        ConversationState.SELECT_GST_TYPE,
        ConversationState.SESSION_EXPIRED
    ],
    ConversationState.SELECT_GST_TYPE: [
        ConversationState.SELECT_DURATION,
        ConversationState.SELECT_GST_TYPE,  # Retry/change selection
        ConversationState.ERROR,
        ConversationState.SESSION_EXPIRED
    ],
    ConversationState.SELECT_DURATION: [
        ConversationState.SMS_GENERATION,
        ConversationState.SELECT_GST_TYPE,  # Go back
        ConversationState.SELECT_DURATION,  # Retry
        ConversationState.ERROR,
        ConversationState.SESSION_EXPIRED
    ],
    ConversationState.SMS_GENERATION: [
        ConversationState.SMS_SENT_CONFIRMATION,
        ConversationState.AWAIT_OTP,  # Direct if user confirms
        ConversationState.SMS_GENERATION,  # Regenerate SMS
        ConversationState.ERROR,
        ConversationState.SESSION_EXPIRED
    ],
    ConversationState.SMS_SENT_CONFIRMATION: [
        ConversationState.AWAIT_OTP,
        ConversationState.SMS_GENERATION,  # Go back to regenerate
        ConversationState.ERROR,
        ConversationState.SESSION_EXPIRED
    ],
    ConversationState.AWAIT_OTP: [
        ConversationState.OTP_RECEIVED,
        ConversationState.AWAIT_CONFIRMATION_SMS,  # Direct if OTP provided
        ConversationState.SMS_GENERATION,  # Regenerate if OTP not received
        ConversationState.AWAIT_OTP,  # Retry
        ConversationState.ERROR,
        ConversationState.SESSION_EXPIRED
    ],
    ConversationState.OTP_RECEIVED: [
        ConversationState.AWAIT_CONFIRMATION_SMS,
        ConversationState.SESSION_EXPIRED
    ],
    ConversationState.AWAIT_CONFIRMATION_SMS: [
        ConversationState.COMPLETED,
        ConversationState.AWAIT_OTP,  # Go back if issues
        ConversationState.ERROR,
        ConversationState.SESSION_EXPIRED
    ],
    ConversationState.COMPLETED: [
        ConversationState.WELCOME,  # Start new filing
        ConversationState.COMPLETED,  # Stay in completed
    ],
    ConversationState.ERROR: [
        ConversationState.WELCOME,  # Restart
        ConversationState.ASK_GSTIN,  # Resume from specific point
        ConversationState.ERROR,  # Stay in error for retry
    ],
    ConversationState.SESSION_EXPIRED: [
        ConversationState.WELCOME,  # Restart
    ],
}


def is_valid_transition(from_state: ConversationState, to_state: ConversationState) -> bool:
    """
    Checks if a state transition is valid.
    
    Args:
        from_state: Current state
        to_state: Target state
    
    Returns:
        True if transition is allowed, False otherwise
    """
    allowed_transitions = STATE_TRANSITIONS.get(from_state, [])
    return to_state in allowed_transitions


def get_state_metadata(state: ConversationState) -> StateMetadata:
    """
    Retrieves metadata for a given state.
    
    Args:
        state: Conversation state
    
    Returns:
        StateMetadata for the state
    """
    return STATE_METADATA.get(state, StateMetadata(
        name=state,
        display_name=state.value,
        description="Unknown state"
    ))


def get_progress_message(state: ConversationState) -> str:
    """
    Generates a progress message for the current state.
    
    Args:
        state: Current conversation state
    
    Returns:
        Progress message (e.g., "Step 3 of 8")
    """
    metadata = get_state_metadata(state)
    if metadata.step_number and metadata.step_number > 0:
        return f"📍 Step {metadata.step_number} of {metadata.total_steps}"
    return ""
