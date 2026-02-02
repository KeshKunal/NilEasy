"""
app/services/filing_service.py

Purpose: Nil filing lifecycle management

- Tracks filing attempts
- Stores OTP/ARN timestamps
- Updates filing status (initiated, confirmed, failed)
- Provides auditability for compliance
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.mongo import get_filing_attempts_collection
from app.core.logging import get_logger

logger = get_logger(__name__)


class FilingService:
    """Service for managing GST Nil filing lifecycle."""
    
    def __init__(self):
        self.collection: Optional[AsyncIOMotorCollection] = None
    
    async def _get_collection(self) -> AsyncIOMotorCollection:
        """Get filing attempts collection."""
        if not self.collection:
            self.collection = get_filing_attempts_collection()
        return self.collection
    
    async def create_filing_attempt(
        self,
        user_id: str,
        gstin: str,
        gst_type: str,
        period: str
    ) -> str:
        """
        Creates a new filing attempt record.
        
        Args:
            user_id: User ID
            gstin: GSTIN
            gst_type: GST type (regular/composition)
            period: Filing period (MMYYYY format)
        
        Returns:
            Filing attempt ID
        """
        collection = await self._get_collection()
        
        attempt_data = {
            "user_id": user_id,
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
        
        result = await collection.insert_one(attempt_data)
        attempt_id = str(result.inserted_id)
        
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
        collection = await self._get_collection()
        
        # Build query
        query = {"user_id": user_id}
        if gstin:
            query["gstin"] = gstin
        if period:
            query["period"] = period
        
        # Find latest attempt
        attempt = await collection.find_one(
            query,
            sort=[("created_at", -1)]
        )
        
        if not attempt:
            logger.warning(f"No filing attempt found for user {user_id}")
            return False
        
        # Build update data
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow()
        }
        
        # Add timestamp based on status
        if status == "sms_sent":
            update_data["sms_sent_at"] = datetime.utcnow()
        elif status == "otp_received":
            update_data["otp_received_at"] = datetime.utcnow()
        elif status == "otp_submitted":
            update_data["otp_submitted_at"] = datetime.utcnow()
        elif status == "completed":
            update_data["completed_at"] = datetime.utcnow()
        
        if error_message:
            update_data["error_message"] = error_message
        
        # Update
        result = await collection.update_one(
            {"_id": attempt["_id"]},
            {"$set": update_data}
        )
        
        logger.info(
            f"Filing status updated to {status}",
            extra={
                "user_id": user_id,
                "attempt_id": str(attempt["_id"]),
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
        collection = await self._get_collection()
        
        query = {"user_id": user_id}
        if gstin:
            query["gstin"] = gstin
        if period:
            query["period"] = period
        
        # Find latest attempt
        attempt = await collection.find_one(
            query,
            sort=[("created_at", -1)]
        )
        
        if not attempt:
            return False
        
        # Update with ARN
        result = await collection.update_one(
            {"_id": attempt["_id"]},
            {
                "$set": {
                    "arn": arn,
                    "status": "completed",
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
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
    
    async def increment_retry_count(
        self,
        user_id: str,
        gstin: Optional[str] = None,
        period: Optional[str] = None
    ) -> int:
        """
        Increments retry count for a filing attempt.
        
        Args:
            user_id: User ID
            gstin: Optional GSTIN filter
            period: Optional period filter
        
        Returns:
            New retry count
        """
        collection = await self._get_collection()
        
        query = {"user_id": user_id}
        if gstin:
            query["gstin"] = gstin
        if period:
            query["period"] = period
        
        # Find latest attempt
        attempt = await collection.find_one(
            query,
            sort=[("created_at", -1)]
        )
        
        if not attempt:
            return 0
        
        new_count = attempt.get("retry_count", 0) + 1
        
        await collection.update_one(
            {"_id": attempt["_id"]},
            {
                "$set": {
                    "retry_count": new_count,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return new_count
    
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
        collection = await self._get_collection()
        
        query = {"user_id": user_id}
        if gstin:
            query["gstin"] = gstin
        if period:
            query["period"] = period
        
        attempt = await collection.find_one(
            query,
            sort=[("created_at", -1)]
        )
        
        if attempt:
            attempt["_id"] = str(attempt["_id"])
        
        return attempt
    
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
        collection = await self._get_collection()
        
        cursor = collection.find(
            {"user_id": user_id}
        ).sort("created_at", -1).limit(limit)
        
        attempts = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string
        for attempt in attempts:
            attempt["_id"] = str(attempt["_id"])
        
        return attempts
    
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
        collection = await self._get_collection()
        
        # Aggregate counts by status
        pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        results = await collection.aggregate(pipeline).to_list(length=None)
        
        # Build stats dict
        stats = {
            "total": 0,
            "completed": 0,
            "failed": 0,
            "pending": 0
        }
        
        for result in results:
            status = result["_id"]
            count = result["count"]
            stats["total"] += count
            
            if status == "completed":
                stats["completed"] = count
            elif status == "failed":
                stats["failed"] = count
            else:
                stats["pending"] += count
        
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
        collection = await self._get_collection()
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        attempt = await collection.find_one({
            "user_id": user_id,
            "gstin": gstin,
            "period": period,
            "status": "completed",
            "completed_at": {"$gte": cutoff_time}
        })
        
        return attempt is not None


# Global service instance
_filing_service: Optional[FilingService] = None


def get_filing_service() -> FilingService:
    """Get or create filing service instance."""
    global _filing_service
    if _filing_service is None:
        _filing_service = FilingService()
    return _filing_service
