"""
app/services/session_service.py

Purpose: Session and state management

- Updates current_state
- Tracks last interaction time
- Handles session expiry and reset logic
- Enforces valid state transitions
- Rate limiting and abuse prevention
"""

from app.db.mongo import get_users_collection, get_sessions_collection
from app.flow.states import ConversationState, is_valid_transition, get_state_metadata
from app.core.config import settings
from app.core.logging import get_logger, LogContext
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = get_logger(__name__)


async def update_user_state(
    user_id: str,
    new_state: ConversationState,
    validate_transition: bool = True
) -> bool:
    """
    Updates the user's conversation state with validation.
    
    Args:
        user_id: User ID
        new_state: Target state
        validate_transition: Whether to enforce state transition rules
    
    Returns:
        True if successful
        
    Raises:
        ValueError: If transition is invalid
    """
    with LogContext(user_id=user_id, state=new_state.value):
        users = get_users_collection()
        
        # Get current state
        user = await users.find_one({"user_id": user_id})
        if not user:
            logger.error(f"User not found", extra={"user_id": user_id})
            return False
        
        current_state = ConversationState(user.get("current_state", ConversationState.WELCOME))
        
        # Validate transition
        if validate_transition and not is_valid_transition(current_state, new_state):
            logger.warning(
                f"Invalid state transition attempted: {current_state} -> {new_state}",
                extra={"user_id": user_id}
            )
            raise ValueError(f"Invalid state transition: {current_state} -> {new_state}")
        
        # Update state
        result = await users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "current_state": new_state.value,
                    "last_interaction": datetime.utcnow(),
                    "state_updated_at": datetime.utcnow()
                },
                "$push": {
                    "state_history": {
                        "from": current_state.value,
                        "to": new_state.value,
                        "timestamp": datetime.utcnow()
                    }
                }
            }
        )
        
        success = result.modified_count > 0
        if success:
            logger.info(
                f"State updated: {current_state} -> {new_state}",
                extra={"user_id": user_id}
            )
        else:
            logger.warning(
                f"State update failed",
                extra={"user_id": user_id, "new_state": new_state}
            )
        
        return success


async def save_session_data(user_id: str, data: Dict[str, Any], merge: bool = True) -> bool:
    """
    Saves temporary session data for the user.
    
    Args:
        user_id: User ID
        data: Data to save
        merge: If True, merges with existing data; if False, replaces it
    
    Returns:
        True if successful
    """
    with LogContext(user_id=user_id):
        users = get_users_collection()
        
        if merge:
            # Merge with existing session data
            user = await users.find_one({"user_id": user_id})
            if user:
                existing_data = user.get("session_data", {})
                data = {**existing_data, **data}
        
        result = await users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "session_data": data,
                    "last_interaction": datetime.utcnow()
                }
            }
        )
        
        success = result.modified_count > 0
        if success:
            logger.debug(
                f"Session data saved",
                extra={"user_id": user_id, "keys": list(data.keys())}
            )
        
        return success


async def get_session_data(user_id: str) -> Dict[str, Any]:
    """
    Retrieves session data for a user.
    
    Args:
        user_id: User ID
    
    Returns:
        Session data dict
    """
    users = get_users_collection()
    user = await users.find_one({"user_id": user_id})
    
    if not user:
        return {}
    
    return user.get("session_data", {})


async def clear_session_data(user_id: str) -> bool:
    """
    Clears session data for a user.
    
    Args:
        user_id: User ID
    
    Returns:
        True if successful
    """
    users = get_users_collection()
    
    result = await users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "session_data": {},
                "last_interaction": datetime.utcnow()
            }
        }
    )
    
    success = result.modified_count > 0
    if success:
        logger.debug(f"Session data cleared", extra={"user_id": user_id})
    
    return success


async def reset_session(user_id: str, reason: str = "manual") -> bool:
    """
    Resets the user's session to start fresh.
    
    Args:
        user_id: User ID
        reason: Reason for reset (for logging)
    
    Returns:
        True if successful
    """
    with LogContext(user_id=user_id):
        users = get_users_collection()
        
        result = await users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "current_state": ConversationState.WELCOME.value,
                    "session_data": {},
                    "retry_count": 0,
                    "last_interaction": datetime.utcnow(),
                    "session_reset_at": datetime.utcnow(),
                    "session_reset_reason": reason
                }
            }
        )
        
        success = result.modified_count > 0
        if success:
            logger.info(
                f"Session reset successfully",
                extra={"user_id": user_id, "reason": reason}
            )
        
        return success


async def check_session_expiry(user_id: str) -> Dict[str, Any]:
    """
    Checks if the user's session has expired.
    
    Args:
        user_id: User ID
    
    Returns:
        Dict with expired (bool), remaining_time (timedelta), and should_warn (bool)
    """
    users = get_users_collection()
    user = await users.find_one({"user_id": user_id})
    
    if not user:
        return {
            "expired": True,
            "remaining_time": timedelta(0),
            "should_warn": False
        }
    
    last_interaction = user.get("last_interaction")
    if not last_interaction:
        return {
            "expired": True,
            "remaining_time": timedelta(0),
            "should_warn": False
        }
    
    # Get state-specific timeout
    current_state = ConversationState(user.get("current_state", ConversationState.WELCOME))
    state_metadata = get_state_metadata(current_state)
    timeout_minutes = state_metadata.timeout_minutes
    
    expiry_time = last_interaction + timedelta(minutes=timeout_minutes)
    now = datetime.utcnow()
    
    expired = now > expiry_time
    remaining_time = expiry_time - now if not expired else timedelta(0)
    
    # Warn if less than 5 minutes remaining
    should_warn = not expired and remaining_time < timedelta(minutes=5)
    
    if expired:
        logger.info(
            f"Session expired",
            extra={
                "user_id": user_id,
                "last_interaction": last_interaction.isoformat(),
                "timeout_minutes": timeout_minutes
            }
        )
    
    return {
        "expired": expired,
        "remaining_time": remaining_time,
        "should_warn": should_warn,
        "timeout_minutes": timeout_minutes
    }


async def handle_session_expiry(user_id: str) -> bool:
    """
    Handles an expired session by resetting state.
    
    Args:
        user_id: User ID
    
    Returns:
        True if handled successfully
    """
    # Mark state as expired
    await update_user_state(user_id, ConversationState.SESSION_EXPIRED, validate_transition=False)
    
    # Clear session data
    await clear_session_data(user_id)
    
    logger.info(f"Session expiry handled", extra={"user_id": user_id})
    
    return True


async def check_rate_limit(user_id: str, limit_type: str = "messages") -> Dict[str, Any]:
    """
    Checks if user has exceeded rate limits.
    
    Args:
        user_id: User ID
        limit_type: Type of rate limit ('messages', 'gstin_lookups')
    
    Returns:
        Dict with allowed (bool), remaining (int), reset_at (datetime)
    """
    sessions = get_sessions_collection()
    
    # Define limits based on type
    limits = {
        "messages": {
            "max": settings.RATE_LIMIT_MESSAGES_PER_MINUTE,
            "window_seconds": 60
        },
        "gstin_lookups": {
            "max": settings.RATE_LIMIT_GSTIN_LOOKUPS_PER_HOUR,
            "window_seconds": 3600
        }
    }
    
    limit_config = limits.get(limit_type, limits["messages"])
    max_requests = limit_config["max"]
    window_seconds = limit_config["window_seconds"]
    
    now = datetime.utcnow()
    window_start = now - timedelta(seconds=window_seconds)
    
    # Get recent requests
    session_key = f"{user_id}:{limit_type}"
    session = await sessions.find_one({"session_id": session_key})
    
    if not session:
        # Create new session
        await sessions.insert_one({
            "session_id": session_key,
            "user_id": user_id,
            "limit_type": limit_type,
            "requests": [now],
            "created_at": now,
            "expires_at": now + timedelta(seconds=window_seconds)
        })
        
        return {
            "allowed": True,
            "remaining": max_requests - 1,
            "reset_at": now + timedelta(seconds=window_seconds)
        }
    
    # Filter requests within current window
    recent_requests = [
        req for req in session.get("requests", [])
        if req > window_start
    ]
    
    # Check if limit exceeded
    if len(recent_requests) >= max_requests:
        oldest_request = min(recent_requests)
        reset_at = oldest_request + timedelta(seconds=window_seconds)
        
        logger.warning(
            f"Rate limit exceeded for {limit_type}",
            extra={
                "user_id": user_id,
                "limit_type": limit_type,
                "count": len(recent_requests),
                "max": max_requests
            }
        )
        
        return {
            "allowed": False,
            "remaining": 0,
            "reset_at": reset_at,
            "retry_after_seconds": (reset_at - now).total_seconds()
        }
    
    # Add current request
    recent_requests.append(now)
    
    await sessions.update_one(
        {"session_id": session_key},
        {
            "$set": {
                "requests": recent_requests,
                "expires_at": now + timedelta(seconds=window_seconds)
            }
        }
    )
    
    return {
        "allowed": True,
        "remaining": max_requests - len(recent_requests),
        "reset_at": now + timedelta(seconds=window_seconds)
    }


async def get_user_stats(user_id: str) -> Dict[str, Any]:
    """
    Retrieves user statistics for monitoring and analytics.
    
    Args:
        user_id: User ID
    
    Returns:
        Dict with user stats
    """
    users = get_users_collection()
    user = await users.find_one({"user_id": user_id})
    
    if not user:
        return {}
    
    state_history = user.get("state_history", [])
    
    return {
        "user_id": user_id,
        "current_state": user.get("current_state"),
        "total_filings": user.get("total_filings", 0),
        "retry_count": user.get("retry_count", 0),
        "created_at": user.get("created_at"),
        "last_interaction": user.get("last_interaction"),
        "total_state_transitions": len(state_history),
        "gstin": user.get("gstin"),
        "business_name": user.get("business_details", {}).get("trade_name")
    }
