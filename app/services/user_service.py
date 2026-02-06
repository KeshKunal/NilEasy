"""
app/services/user_service.py

Purpose: User data management

- Create or update user records
- User retrieval and management
- Analytics and filing tracking
- Uses phone number as primary identifier
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.logging import get_logger
from datetime import datetime
from typing import Optional, Dict, Any

logger = get_logger(__name__)


class UserService:
    """
    Enhanced user service for AiSensy integration.
    Handles user creation, updates, and analytics tracking.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """Initialize with database connection."""
        self.db = db
        self.users = db.users
        self.filings = db.filings
class UserService:
    """
    Enhanced user service for AiSensy integration.
    Handles user creation, updates, and analytics tracking.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """Initialize with database connection."""
        self.db = db
        self.users = db.users
        self.filings = db.filings
        self.filing_contexts = db.filing_contexts
    
    async def save_filing_context(
        self,
        gstin: str,
        gst_type: str,
        period: str
    ) -> bool:
        """
        Save temporary filing context for a GSTIN.
        This allows us to track completion later without asking the user for these details again.
        """
        try:
            await self.filing_contexts.update_one(
                {"gstin": gstin},
                {
                    "$set": {
                        "gst_type": gst_type,
                        "period": period,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
            logger.info(f"Saved filing context for {gstin}: {gst_type}, {period}")
            return True
        except Exception as e:
            logger.error(f"Failed to save filing context: {e}")
            return False

    async def get_filing_context(self, gstin: str) -> Optional[Dict[str, Any]]:
        """Retrieve filing context for a GSTIN."""
        return await self.filing_contexts.find_one({"gstin": gstin})
    
    async def get_or_create_user(self, phone: str, name: str = None) -> Dict[str, Any]:
        """
        Get existing user or create new one.
        
        Args:
            phone: Phone number (primary identifier)
            name: User's display name (optional)
        
        Returns:
            User document
        """
        # Try to get existing user
        user = await self.users.find_one({"phone": phone})
        
        if user:
            # Update last active
            await self.users.update_one(
                {"phone": phone},
                {"$set": {"last_active": datetime.utcnow()}}
            )
            logger.info(f"Retrieved existing user: {phone}")
            return user
        
        # Create new user
        user_doc = {
            "phone": phone,
            "name": name or "User",
            "gstin": None,
            "business_name": None,
            "legal_name": None,
            "state": None,
            "created_at": datetime.utcnow(),
            "last_active": datetime.utcnow(),
            "total_filings": 0,
            "successful_filings": 0,
            "failed_filings": 0
        }
        
        await self.users.insert_one(user_doc)
        logger.info(f"Created new user: {phone}")
        
        return user_doc
    
    async def update_or_create_user(
        self, 
        user_id: str, 
        gstin: str = None,
        last_filing_status: str = None
    ) -> bool:
        """
        Update existing user or create new one with analytics.
        
        Args:
            user_id: Phone number
            gstin: GSTIN to store
            last_filing_status: 'completed' or 'failed'
        
        Returns:
            True if successful
        """
        updates = {
            "last_active": datetime.utcnow()
        }
        
        if gstin:
            updates["gstin"] = gstin
        
        # Update filing counters
        if last_filing_status == 'completed':
            result = await self.users.update_one(
                {"phone": user_id},
                {
                    "$set": updates,
                    "$inc": {
                        "total_filings": 1,
                        "successful_filings": 1
                    }
                },
                upsert=True
            )
        elif last_filing_status == 'failed':
            result = await self.users.update_one(
                {"phone": user_id},
                {
                    "$set": updates,
                    "$inc": {
                        "total_filings": 1,
                        "failed_filings": 1
                    }
                },
                upsert=True
            )
        else:
            result = await self.users.update_one(
                {"phone": user_id},
                {"$set": updates},
                upsert=True
            )
        
        logger.info(f"Updated user: {user_id}, Status: {last_filing_status}")
        return result.modified_count > 0 or result.upserted_id is not None
    
    async def get_user_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user by phone number.
        
        Args:
            phone: Phone number
        
        Returns:
            User document or None
        """
        return await self.users.find_one({"phone": phone})
    
    async def get_user_stats(self, phone: str) -> Dict[str, Any]:
        """
        Get user's filing statistics.
        
        Args:
            phone: Phone number
        
        Returns:
            Statistics dictionary
        """
        user = await self.get_user_by_phone(phone)
        
        if not user:
            return {
                "total_filings": 0,
                "successful_filings": 0,
                "failed_filings": 0,
                "success_rate": 0.0
            }
        
        total = user.get("total_filings", 0)
        successful = user.get("successful_filings", 0)
        success_rate = (successful / total * 100) if total > 0 else 0.0
        
        return {
            "total_filings": total,
            "successful_filings": successful,
            "failed_filings": user.get("failed_filings", 0),
            "success_rate": round(success_rate, 2)
        }

