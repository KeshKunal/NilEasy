"""
app/services/user_service.py

Purpose: User data management

- Create or update user records
- Persist GSTIN and business details
- Update user state and metadata
- User retrieval and management
"""

from app.db.mongo import get_users_collection
from app.flow.states import ConversationState
from app.core.logging import get_logger, LogContext
from datetime import datetime
from typing import Optional, Dict, Any

logger = get_logger(__name__)


async def get_or_create_user(user_id: str) -> Dict[str, Any]:
    """
    Retrieves an existing user or creates a new one.
    
    Args:
        user_id: WhatsApp user ID
    
    Returns:
        User document
    """
    with LogContext(user_id=user_id):
        users = get_users_collection()
        
        user = await users.find_one({"user_id": user_id})
        
        if not user:
            logger.info(f"Creating new user", extra={"user_id": user_id})
            
            user = {
                "user_id": user_id,
                "current_state": ConversationState.WELCOME,
                "created_at": datetime.utcnow(),
                "last_interaction": datetime.utcnow(),
                "gstin": None,
                "business_details": {},
                "session_data": {},
                "filing_history": [],
                "retry_count": 0,
                "total_filings": 0,
                "preferences": {
                    "language": "en",  # Future: multi-language support
                    "notifications": True
                }
            }
            
            await users.insert_one(user)
            logger.info(f"New user created successfully", extra={"user_id": user_id})
        else:
            # Update last interaction
            await users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "last_interaction": datetime.utcnow()
                    }
                }
            )
        
        return user


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a user by ID.
    
    Args:
        user_id: WhatsApp user ID
    
    Returns:
        User document or None if not found
    """
    users = get_users_collection()
    return await users.find_one({"user_id": user_id})


async def update_user_gstin(user_id: str, gstin: str) -> bool:
    """
    Updates user's GSTIN.
    
    Args:
        user_id: User ID
        gstin: GSTIN to store
    
    Returns:
        True if successful
    """
    with LogContext(user_id=user_id, gstin=gstin):
        users = get_users_collection()
        
        result = await users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "gstin": gstin.upper(),
                    "last_interaction": datetime.utcnow()
                }
            }
        )
        
        success = result.modified_count > 0
        if success:
            logger.info("GSTIN updated", extra={"user_id": user_id, "gstin": gstin})
        else:
            logger.warning("Failed to update GSTIN", extra={"user_id": user_id})
        
        return success


async def update_business_details(user_id: str, details: Dict[str, Any]) -> bool:
    """
    Updates user's business details from GST verification.
    
    Args:
        user_id: User ID
        details: Business details dict
    
    Returns:
        True if successful
    """
    with LogContext(user_id=user_id):
        users = get_users_collection()
        
        result = await users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "business_details": details,
                    "last_interaction": datetime.utcnow(),
                    "business_verified_at": datetime.utcnow()
                }
            }
        )
        
        success = result.modified_count > 0
        if success:
            logger.info(
                "Business details updated",
                extra={
                    "user_id": user_id,
                    "trade_name": details.get("trade_name")
                }
            )
        
        return success


async def increment_retry_count(user_id: str) -> int:
    """
    Increments retry count for current step.
    
    Args:
        user_id: User ID
    
    Returns:
        Updated retry count
    """
    users = get_users_collection()
    
    result = await users.find_one_and_update(
        {"user_id": user_id},
        {
            "$inc": {"retry_count": 1},
            "$set": {"last_interaction": datetime.utcnow()}
        },
        return_document=True
    )
    
    retry_count = result.get("retry_count", 0) if result else 0
    logger.debug(f"Retry count incremented to {retry_count}", extra={"user_id": user_id})
    
    return retry_count


async def reset_retry_count(user_id: str) -> bool:
    """
    Resets retry count (called when step succeeds).
    
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
                "retry_count": 0,
                "last_interaction": datetime.utcnow()
            }
        }
    )
    
    return result.modified_count > 0


async def add_to_filing_history(user_id: str, filing_data: Dict[str, Any]) -> bool:
    """
    Adds a filing attempt to user's history.
    
    Args:
        user_id: User ID
        filing_data: Filing attempt details
    
    Returns:
        True if successful
    """
    users = get_users_collection()
    
    result = await users.update_one(
        {"user_id": user_id},
        {
            "$push": {
                "filing_history": {
                    **filing_data,
                    "timestamp": datetime.utcnow()
                }
            },
            "$inc": {"total_filings": 1},
            "$set": {"last_interaction": datetime.utcnow()}
        }
    )
    
    success = result.modified_count > 0
    if success:
        logger.info("Filing added to history", extra={"user_id": user_id})
    
    return success


async def get_user_filing_history(user_id: str, limit: int = 10) -> list:
    """
    Retrieves user's filing history.
    
    Args:
        user_id: User ID
        limit: Maximum number of filings to return
    
    Returns:
        List of filing records
    """
    user = await get_user_by_id(user_id)
    if not user:
        return []
    
    history = user.get("filing_history", [])
    # Return most recent first
    return sorted(history, key=lambda x: x.get("timestamp", datetime.min), reverse=True)[:limit]


async def check_duplicate_filing(user_id: str, gstin: str, gst_type: str, period: str) -> bool:
    """
    Checks if user has already filed for the given GSTIN, type, and period.
    
    Args:
        user_id: User ID
        gstin: GSTIN
        gst_type: GST return type
        period: Filing period
    
    Returns:
        True if duplicate found
    """
    user = await get_user_by_id(user_id)
    if not user:
        return False
    
    history = user.get("filing_history", [])
    
    for filing in history:
        if (filing.get("gstin") == gstin and 
            filing.get("gst_type") == gst_type and 
            filing.get("period") == period and
            filing.get("status") == "completed"):
            logger.warning(
                "Duplicate filing detected",
                extra={
                    "user_id": user_id,
                    "gstin": gstin,
                    "gst_type": gst_type,
                    "period": period
                }
            )
            return True
    
    return False


async def update_user_preferences(user_id: str, preferences: Dict[str, Any]) -> bool:
    """
    Updates user preferences.
    
    Args:
        user_id: User ID
        preferences: Preferences dict
    
    Returns:
        True if successful
    """
    users = get_users_collection()
    
    result = await users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "preferences": preferences,
                "last_interaction": datetime.utcnow()
            }
        }
    )
    
    return result.modified_count > 0
