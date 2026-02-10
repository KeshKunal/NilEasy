"""
app/services/user_service.py

Purpose: User data management with unified schema

- Create or update user records
- User retrieval and management
- Filing tracking (embedded in user document)
- Generated links tracking (embedded in user document)
- Uses phone number as a lookup attribute
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.logging import get_logger
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = get_logger(__name__)


class UserService:
    """
    User service with unified schema.
    All data (filings, generated_links) is embedded in user document.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """Initialize with database connection."""
        self.db = db
        self.users = db.users
    
    async def get_or_create_user(self, phone: str, name: str = None) -> Dict[str, Any]:
        """
        Get existing user or create new one.
        
        Args:
            phone: Phone number (lookup attribute)
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
        
        # Create new user with unified schema
        user_doc = {
            "phone": phone,
            "name": name or "User",
            "gstin": None,
            "business_name": None,
            "legal_name": None,
            "address": None,
            "state": None,
            "created_at": datetime.utcnow(),
            "last_active": datetime.utcnow(),
            "total_filings": 0,
            "successful_filings": 0,
            "failed_filings": 0,
            # Embedded arrays for unified schema
            "filings": [],
            "generated_links": []
        }
        
        await self.users.insert_one(user_doc)
        logger.info(f"Created new user: {phone}")
        
        return user_doc
    
    async def update_or_create_user(
        self, 
        user_id: str, 
        gstin: str = None,
        last_filing_status: str = None,
        business_name: str = None,
        address: str = None,
        last_updated_status: str = None,
        phone: str = None
    ) -> bool:
        """
        Update existing user or create new one with analytics.
        
        Args:
            user_id: Phone number or GSTIN (identifier)
            gstin: GSTIN to store
            last_filing_status: 'completed' or 'failed'
            business_name: Trade name
            address: Business address
            last_updated_status: Status of user journey
            phone: Phone number to explicitly save
        
        Returns:
            True if successful
        """
        updates = {
            "last_active": datetime.utcnow()
        }
        
        if phone:
            updates["phone"] = phone
        if gstin:
            updates["gstin"] = gstin
        if business_name:
            updates["business_name"] = business_name
        if address:
            updates["address"] = address
        if last_updated_status:
            updates["last_updated_status"] = last_updated_status
        
        if last_updated_status:
            updates["last_updated_status"] = last_updated_status
        
        # Determine query field
        # GSTIN contains letters, Phone is typically digits (with optional +)
        is_gstin_format = any(c.isalpha() for c in user_id)
        query = {"gstin": user_id} if is_gstin_format else {"phone": user_id}
        
        # Update filing counters
        if last_filing_status == 'completed':
            result = await self.users.update_one(
                query,
                {
                    "$set": updates,
                    "$inc": {
                        "total_filings": 1,
                        "successful_filings": 1
                    },
                    "$setOnInsert": {
                        "created_at": datetime.utcnow(),
                        "filings": [],
                        "generated_links": []
                    }
                },
                upsert=True
            )
        elif last_filing_status == 'failed':
            result = await self.users.update_one(
                query,
                {
                    "$set": updates,
                    "$inc": {
                        "total_filings": 1,
                        "failed_filings": 1
                    },
                    "$setOnInsert": {
                        "created_at": datetime.utcnow(),
                        "filings": [],
                        "generated_links": []
                    }
                },
                upsert=True
            )
        else:
            result = await self.users.update_one(
                query,
                {
                    "$set": updates,
                    "$setOnInsert": {
                        "created_at": datetime.utcnow(),
                        "filings": [],
                        "generated_links": []
                    }
                },
                upsert=True
            )
        
        logger.info(f"Updated user: {user_id}, Status: {last_filing_status}")
        return result.modified_count > 0 or result.upserted_id is not None
    
    async def get_user_by_gstin(self, gstin: str) -> Optional[Dict[str, Any]]:
        """Find user by GSTIN."""
        return await self.users.find_one({"gstin": gstin})
    
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
    
    # =========================================================================
    # Filing Context Methods (now embedded in user document)
    # =========================================================================
    
    async def save_filing_context(
        self,
        gstin: str,
        gst_type: str,
        period: str
    ) -> bool:
        """
        Save filing context embedded in user document.
        """
        try:
            result = await self.users.update_one(
                {"gstin": gstin},
                {
                    "$set": {
                        "current_filing_context": {
                            "gst_type": gst_type,
                            "period": period,
                            "updated_at": datetime.utcnow()
                        }
                    }
                }
            )
            logger.info(f"Saved filing context for {gstin}: {gst_type}, {period}")
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to save filing context: {e}")
            return False

    async def get_filing_context(self, gstin: str) -> Optional[Dict[str, Any]]:
        """Retrieve filing context for a GSTIN."""
        user = await self.users.find_one({"gstin": gstin})
        return user.get("current_filing_context") if user else None
    
    # =========================================================================
    # Embedded Filings Methods
    # =========================================================================
    
    async def add_filing(
        self,
        phone: str,
        gstin: str,
        gst_type: str,
        period: str,
        status: str,
        arn: str = None
    ) -> bool:
        """
        Add a filing record to user's embedded filings array.
        
        Args:
            phone: User's phone number
            gstin: GSTIN
            gst_type: GST type (3B/R1)
            period: Filing period (MMYYYY)
            status: Filing status (completed/failed)
            arn: ARN number (optional)
        
        Returns:
            True if successful
        """
        filing_doc = {
            "gstin": gstin,
            "gst_type": gst_type,
            "period": period,
            "status": status,
            "timestamp": datetime.utcnow(),
            "arn": arn
        }
        
        result = await self.users.update_one(
            {"phone": phone},
            {
                "$push": {"filings": filing_doc},
                "$set": {"last_active": datetime.utcnow()}
            }
        )
        
        logger.info(f"Added filing for {phone}: {gst_type} {period} - {status}")
        return result.modified_count > 0
    
    async def get_filing_history(
        self,
        phone: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get user's filing history from embedded array.
        
        Args:
            phone: Phone number
            limit: Maximum filings to return
        
        Returns:
            List of filing records
        """
        user = await self.users.find_one({"phone": phone})
        if not user:
            return []
        
        filings = user.get("filings", [])
        # Sort by timestamp descending and limit
        filings.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)
        return filings[:limit]
    
    # =========================================================================
    # Generated Links Methods
    # =========================================================================
    
    async def add_generated_link(
        self,
        phone: str,
        short_url: str,
        short_code: str,
        sms_text: str,
        gstin: str,
        gst_type: str,
        period: str
    ) -> bool:
        """
        Add a generated SMS link to user's embedded array.
        
        Args:
            phone: User's phone number (can be None if not known yet)
            short_url: The shortened URL
            short_code: Short code for analytics
            sms_text: The SMS text content
            gstin: GSTIN
            gst_type: GST type
            period: Filing period
        
        Returns:
            True if successful
        """
        link_doc = {
            "short_url": short_url,
            "short_code": short_code,
            "sms_text": sms_text,
            "gstin": gstin,
            "gst_type": gst_type,
            "period": period,
            "created_at": datetime.utcnow(),
            "clicked": False
        }
        
        # Try to find user by GSTIN if phone not provided
        query = {"phone": phone} if phone else {"gstin": gstin}
        
        result = await self.users.update_one(
            query,
            {"$push": {"generated_links": link_doc}}
        )
        
        logger.info(f"Added generated link for {gstin}: {short_url}")
        return result.modified_count > 0
    
    async def get_generated_links(
        self,
        phone: str = None,
        gstin: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get user's generated links history.
        
        Args:
            phone: Phone number (optional)
            gstin: GSTIN (optional, used if phone not provided)
            limit: Maximum links to return
        
        Returns:
            List of generated link records
        """
        query = {"phone": phone} if phone else {"gstin": gstin}
        user = await self.users.find_one(query)
        
        if not user:
            return []
        
        links = user.get("generated_links", [])
        # Sort by created_at descending and limit
        links.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
        return links[:limit]
    
    async def mark_link_clicked(self, short_code: str) -> bool:
        """
        Mark a generated link as clicked.
        
        Args:
            short_code: The short code of the link
        
        Returns:
            True if updated successfully
        """
        result = await self.users.update_one(
            {"generated_links.short_code": short_code},
            {"$set": {"generated_links.$.clicked": True}}
        )
        return result.modified_count > 0
