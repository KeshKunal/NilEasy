"""
app/services/filing_service.py

Purpose: Nil filing lifecycle management (using embedded data in users collection)

- Tracks filing attempts via user's embedded filings array
- Provides filing history and statistics
- Maintains compatibility with existing API
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongo import get_database
from app.core.logging import get_logger

logger = get_logger(__name__)


class FilingService:
    """
    Service for managing GST Nil filing lifecycle.
    Uses embedded filings array in users collection.
    """
    
    def __init__(self):
        self._db: Optional[AsyncIOMotorDatabase] = None
    
    async def _get_db(self) -> AsyncIOMotorDatabase:
        """Get database instance."""
        if not self._db:
            self._db = await get_database()
        return self._db
    
    async def create_filing_attempt(
        self,
        user_id: str,
        gstin: str,
        gst_type: str,
        period: str
    ) -> str:
        """
        Creates a new filing attempt record embedded in user document.
        
        Args:
            user_id: User ID (phone number)
            gstin: GSTIN
            gst_type: GST type (regular/composition)
            period: Filing period (MMYYYY format)
        
        Returns:
            Filing attempt ID (timestamp-based)
        """
        db = await self._get_db()
        
        attempt_id = f"{gstin}_{period}_{int(datetime.utcnow().timestamp())}"
        
        filing_doc = {
            "attempt_id": attempt_id,
            "gstin": gstin,
            "gst_type": gst_type,
            "period": period,
            "status": "initiated",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "sms_sent_at": None,
            "otp_received_at": None,
            "otp_submitted_at": None,
            "completed_at": None,
            "arn": None,
            "error_message": None,
            "retry_count": 0
        }
        
        # Push to user's filings array
        result = await db.users.update_one(
            {"phone": user_id},
            {
                "$push": {"filings": filing_doc},
                "$set": {"last_active": datetime.utcnow()}
            },
            upsert=True
        )
        
        logger.info(
            "Filing attempt created",
            extra={
                "attempt_id": attempt_id,
                "user_id": user_id,
                "gstin": gstin,
                "period": period
            }
        )
        
        return attempt_id
    
    async def update_filing_status(
        self,
        user_id: str,
        status: str,
        gstin: Optional[str] = None,
        period: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Updates the status of the latest filing attempt.
        
        Args:
            user_id: User ID
            status: New status (sms_sent, otp_received, completed, failed)
            gstin: Optional GSTIN filter
            period: Optional period filter
            error_message: Optional error message for failures
        
        Returns:
            True if updated successfully
        """
        db = await self._get_db()
        
        # Build update data
        update_fields = {
            "filings.$.status": status,
            "filings.$.updated_at": datetime.utcnow()
        }
        
        # Add timestamp based on status
        if status == "sms_sent":
            update_fields["filings.$.sms_sent_at"] = datetime.utcnow()
        elif status == "otp_received":
            update_fields["filings.$.otp_received_at"] = datetime.utcnow()
        elif status == "otp_submitted":
            update_fields["filings.$.otp_submitted_at"] = datetime.utcnow()
        elif status == "completed":
            update_fields["filings.$.completed_at"] = datetime.utcnow()
        
        if error_message:
            update_fields["filings.$.error_message"] = error_message
        
        # Build query for finding the right filing
        query = {"phone": user_id}
        if gstin:
            query["filings.gstin"] = gstin
        if period:
            query["filings.period"] = period
        
        result = await db.users.update_one(
            query,
            {"$set": update_fields}
        )
        
        logger.info(
            f"Filing status updated to {status}",
            extra={
                "user_id": user_id,
                "status": status
            }
        )
        
        return result.modified_count > 0
    
    async def store_arn(
        self,
        user_id: str,
        arn: str,
        gstin: Optional[str] = None,
        period: Optional[str] = None
    ) -> bool:
        """
        Stores ARN (Acknowledgement Reference Number) for a filing.
        
        Args:
            user_id: User ID
            arn: ARN number
            gstin: Optional GSTIN filter
            period: Optional period filter
        
        Returns:
            True if stored successfully
        """
        db = await self._get_db()
        
        query = {"phone": user_id}
        if gstin:
            query["filings.gstin"] = gstin
        if period:
            query["filings.period"] = period
        
        result = await db.users.update_one(
            query,
            {
                "$set": {
                    "filings.$.arn": arn,
                    "filings.$.status": "completed",
                    "filings.$.completed_at": datetime.utcnow(),
                    "filings.$.updated_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(
            "ARN stored for filing",
            extra={
                "user_id": user_id,
                "arn": arn
            }
        )
        
        return result.modified_count > 0
    
    async def get_latest_filing_attempt(
        self,
        user_id: str,
        gstin: Optional[str] = None,
        period: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Gets the latest filing attempt for a user.
        
        Args:
            user_id: User ID
            gstin: Optional GSTIN filter
            period: Optional period filter
        
        Returns:
            Filing attempt dict or None
        """
        db = await self._get_db()
        
        user = await db.users.find_one({"phone": user_id})
        if not user:
            return None
        
        filings = user.get("filings", [])
        if not filings:
            return None
        
        # Filter if needed
        if gstin:
            filings = [f for f in filings if f.get("gstin") == gstin]
        if period:
            filings = [f for f in filings if f.get("period") == period]
        
        if not filings:
            return None
        
        # Sort by created_at and return latest
        filings.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
        return filings[0]
    
    async def get_filing_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Gets filing history for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of attempts to return
        
        Returns:
            List of filing attempts
        """
        db = await self._get_db()
        
        user = await db.users.find_one({"phone": user_id})
        if not user:
            return []
        
        filings = user.get("filings", [])
        filings.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
        
        return filings[:limit]
    
    async def get_filing_stats(
        self,
        user_id: str
    ) -> Dict[str, int]:
        """
        Gets filing statistics for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Dict with counts: total, completed, failed, pending
        """
        db = await self._get_db()
        
        user = await db.users.find_one({"phone": user_id})
        if not user:
            return {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "pending": 0
            }
        
        filings = user.get("filings", [])
        
        stats = {
            "total": len(filings),
            "completed": sum(1 for f in filings if f.get("status") == "completed"),
            "failed": sum(1 for f in filings if f.get("status") == "failed"),
            "pending": sum(1 for f in filings if f.get("status") not in ["completed", "failed"])
        }
        
        return stats
    
    async def check_recent_filing(
        self,
        user_id: str,
        gstin: str,
        period: str,
        hours: int = 24
    ) -> bool:
        """
        Checks if there's a recent successful filing.
        
        Args:
            user_id: User ID
            gstin: GSTIN
            period: Period
            hours: Hours to look back
        
        Returns:
            True if recent filing exists
        """
        db = await self._get_db()
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        user = await db.users.find_one({"phone": user_id})
        if not user:
            return False
        
        filings = user.get("filings", [])
        
        for filing in filings:
            if (filing.get("gstin") == gstin and 
                filing.get("period") == period and
                filing.get("status") == "completed" and
                filing.get("completed_at") and
                filing.get("completed_at") >= cutoff_time):
                return True
        
        return False


# Global service instance
_filing_service: Optional[FilingService] = None


def get_filing_service() -> FilingService:
    """Get or create filing service instance."""
    global _filing_service
    if _filing_service is None:
        _filing_service = FilingService()
    return _filing_service
