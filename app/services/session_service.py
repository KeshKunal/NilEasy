"""
app/services/session_service.py

Purpose: Session and state management (simplified)

NOTE: Most handlers now use direct database operations.
This module is kept for backward compatibility.
"""

from app.db.mongo import get_users_collection
from app.flow.states import ConversationState, is_valid_transition
from app.core.logging import get_logger
from datetime import datetime
from typing import Dict, Any

logger = get_logger(__name__)


async def update_user_state(
    user_id: str,
    new_state: ConversationState,
    validate_transition: bool = False,
    extra_data: Dict[str, Any] = None
) -> bool:
    """
    Updates the user's conversation state.
    
    Args:
        user_id: User's phone number
        new_state: Target state
        validate_transition: Whether to enforce state transition rules
        extra_data: Additional data to save to session_data
    
    Returns:
        True if successful
    """
    users = get_users_collection()
    
    update_ops = {
        "current_state": new_state.value,
        "last_active": datetime.utcnow()
    }
    
    if extra_data:
        for key, value in extra_data.items():
            update_ops[f"session_data.{key}"] = value
    
    result = await users.update_one(
        {"phone": user_id},
        {"$set": update_ops}
    )
    
    return result.modified_count > 0


async def get_session_data(user_id: str) -> Dict[str, Any]:
    """
    Gets user's session data.
    
    Args:
        user_id: User's phone number
    
    Returns:
        Session data dict or empty dict
    """
    users = get_users_collection()
    user = await users.find_one({"phone": user_id})
    
    if not user:
        return {}
    
    return user.get("session_data", {})


async def save_session_data(user_id: str, data: Dict[str, Any]) -> bool:
    """
    Saves data to user's session (merges with existing).
    
    Args:
        user_id: User's phone number
        data: Data to save
    
    Returns:
        True if successful
    """
    users = get_users_collection()
    
    set_ops = {
        f"session_data.{key}": value
        for key, value in data.items()
    }
    set_ops["last_active"] = datetime.utcnow()
    
    result = await users.update_one(
        {"phone": user_id},
        {"$set": set_ops}
    )
    
    return result.modified_count > 0


async def reset_session(user_id: str, reason: str = None) -> bool:
    """
    Resets user's session.
    
    Args:
        user_id: User's phone number
        reason: Optional reason for reset
    
    Returns:
        True if successful
    """
    logger.info(f"Resetting session for {user_id}: {reason or 'No reason'}")
    
    users = get_users_collection()
    
    result = await users.update_one(
        {"phone": user_id},
        {
            "$set": {
                "current_state": ConversationState.WELCOME.value,
                "session_data": {},
                "last_active": datetime.utcnow()
            }
        }
    )
    
    return result.modified_count > 0


async def increment_retry_count(user_id: str) -> int:
    """
    Increments retry count.
    
    Args:
        user_id: User's phone number
    
    Returns:
        New retry count
    """
    users = get_users_collection()
    
    result = await users.find_one_and_update(
        {"phone": user_id},
        {
            "$inc": {"session_data.retry_count": 1},
            "$set": {"last_active": datetime.utcnow()}
        },
        return_document=True
    )
    
    return result.get("session_data", {}).get("retry_count", 0) if result else 0


async def reset_retry_count(user_id: str) -> bool:
    """
    Resets retry count.
    
    Args:
        user_id: User's phone number
    
    Returns:
        True if successful
    """
    users = get_users_collection()
    
    result = await users.update_one(
        {"phone": user_id},
        {
            "$set": {
                "session_data.retry_count": 0,
                "last_active": datetime.utcnow()
            }
        }
    )
    
    return result.modified_count > 0
