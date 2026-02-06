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
    
    async def get_gstin_details(self, gstin: str) -> Optional[Dict[str, Any]]:
        """
        Get cached GSTIN business details from users collection.
        
        Args:
            gstin: 15-character GSTIN
        
        Returns:
            GST business details or None if not found
        """
        user = await self.users.find_one(
            {"gst_data.gstin": gstin},
            {"gst_data": 1}
        )
        
        if user and "gst_data" in user:
            logger.info(f"GSTIN cache hit for: {gstin}")
            return user["gst_data"]
        
        logger.debug(f"GSTIN cache miss for: {gstin}")
        return None
    
    async def store_gst_data(
        self,
        phone: str,
        gst_data: Dict[str, Any],
        business_name: str = None
    ) -> bool:
        """
        Store complete GST data in users collection after verification.
        
        Args:
            phone: User's phone number
            gst_data: Complete GST data from portal (all fields)
            business_name: Business name for quick access
        
        Returns:
            True if stored successfully
        """
        updates = {
            "gst_data": gst_data,
            "gstin": gst_data.get("gstin"),
            "business_name": business_name or gst_data.get("tradeNam"),
            "legal_name": gst_data.get("lgnm"),
            "gst_verified_at": datetime.utcnow(),
            "last_active": datetime.utcnow()
        }
        
        result = await self.users.update_one(
            {"phone": phone},
            {"$set": updates},
            upsert=True
        )
        
        logger.info(
            f"Stored GST data for phone: {phone}, GSTIN: {gst_data.get('gstin')}"
        )
        
        return result.acknowledged

