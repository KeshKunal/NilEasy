"""
app/services/user_service.py

Purpose: User data management

- Create or update user records
- User retrieval and management
- Uses phone number as primary identifier
"""

from app.db.mongo import get_users_collection
from app.flow.states import ConversationState
from app.core.logging import get_logger
from datetime import datetime
from typing import Optional, Dict, Any

logger = get_logger(__name__)


async def create_user(phone: str, name: str = None) -> Dict[str, Any]:
    """
    Creates a new user with phone and name.
    
    Args:
        phone: Phone number (E.164 format: +919876543210)
        name: User's display name (optional)
    
    Returns:
        Created user document
    """
    users = get_users_collection()
    
    # Check if user already exists
    existing = await users.find_one({"phone": phone})
    if existing:
        logger.info(f"User already exists: {phone}")
        return existing
    
    user_doc = {
        "phone": phone,
        "name": name or "User",
        "gstin": None,
        "legal_name": None,
        "trade_name": None,
        "business_address": None,
        "constitution": None,
        "business_activities": None,
        "registration_date": None,
        "current_state": ConversationState.WELCOME.value,
        "session_data": {},
        "filing_history": [],
        "total_filings": 0,
        "created_at": datetime.utcnow(),
        "last_active": datetime.utcnow()
    }
    
    await users.insert_one(user_doc)
    logger.info(f"Created new user: {phone}")
    
    return user_doc


async def get_user_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a user by phone number.
    
    Args:
        phone: Phone number (E.164 format: +919876543210)
    
    Returns:
        User document or None if not found
    """
    users = get_users_collection()
    return await users.find_one({"phone": phone})


async def update_user(phone: str, updates: Dict[str, Any]) -> bool:
    """
    Updates user document.
    
    Args:
        phone: Phone number
        updates: Fields to update
    
    Returns:
        True if successful
    """
    users = get_users_collection()
    
    # Always update last_active
    updates["last_active"] = datetime.utcnow()
    
    result = await users.update_one(
        {"phone": phone},
        {"$set": updates}
    )
    
    return result.modified_count > 0


async def update_user_state(phone: str, new_state: ConversationState) -> bool:
    """
    Updates user's conversation state.
    
    Args:
        phone: Phone number
        new_state: New conversation state
    
    Returns:
        True if successful
    """
    return await update_user(phone, {
        "current_state": new_state.value
    })


async def update_session_data(phone: str, session_data: Dict[str, Any]) -> bool:
    """
    Updates user's session data (merges with existing).
    
    Args:
        phone: Phone number
        session_data: Session data to merge
    
    Returns:
        True if successful
    """
    users = get_users_collection()
    
    # Build $set operations for nested session_data
    set_ops = {
        f"session_data.{key}": value 
        for key, value in session_data.items()
    }
    set_ops["last_active"] = datetime.utcnow()
    
    result = await users.update_one(
        {"phone": phone},
        {"$set": set_ops}
    )
    
    return result.modified_count > 0


async def reset_session(phone: str) -> bool:
    """
    Resets user's session data and state.
    
    Args:
        phone: Phone number
    
    Returns:
        True if successful
    """
    users = get_users_collection()
    
    result = await users.update_one(
        {"phone": phone},
        {
            "$set": {
                "current_state": ConversationState.WELCOME.value,
                "session_data": {},
                "last_active": datetime.utcnow()
            }
        }
    )
    
    return result.modified_count > 0


async def add_filing_to_history(phone: str, filing_data: Dict[str, Any]) -> bool:
    """
    Adds a filing record to user's history.
    
    Args:
        phone: Phone number
        filing_data: Filing details
    
    Returns:
        True if successful
    """
    users = get_users_collection()
    
    result = await users.update_one(
        {"phone": phone},
        {
            "$push": {"filing_history": filing_data},
            "$inc": {"total_filings": 1},
            "$set": {"last_active": datetime.utcnow()}
        }
    )
    
    return result.modified_count > 0
