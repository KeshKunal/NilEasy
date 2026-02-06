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
        phone: str,
        gstin: str,
        gst_type: str,
        period: str,
        business_name: Optional[str] = None,
        sms_link: Optional[str] = None
    ) -> str:
        """
        Creates filing attempt when SMS link is generated.
        Uses upsert to prevent duplicate filings for same GSTIN/period.
        
        Args:
            phone: User's phone number
            gstin: 15-digit GSTIN
            gst_type: "3B" or "R1"
            period: MMYYYY format
            business_name: Business name from captcha verification
            sms_link: Generated SMS deep link
        
        Returns:
            Filing attempt ID
        """
        collection = await self._get_collection()
        
        # Use upsert to avoid duplicates for same GSTIN/period
        filter_query = {
            "phone": phone,
            "gstin": gstin,
            "gst_type": gst_type,
            "period": period
        }
        
        attempt_data = {
            **filter_query,
            "business_name": business_name,
            "sms_link": sms_link,
            "status": "sms_link_generated",
            "sms_link_generated_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "completed_at": None,
            "arn": None,
            "error_message": None,
        }
        
        # Set created_at only on insert
        update_doc = {
            "$set": attempt_data,
            "$setOnInsert": {"created_at": datetime.utcnow(), "retry_count": 0}
        }
        
        result = await collection.update_one(
            filter_query,
            update_doc,
            upsert=True
        )
        
        # Get the document ID
        if result.upserted_id:
            attempt_id = str(result.upserted_id)
        else:
            doc = await collection.find_one(filter_query)
            attempt_id = str(doc["_id"])
        
        logger.info(
            f"Filing attempt {'created' if result.upserted_id else 'updated'}",
            extra={
                "attempt_id": attempt_id,
                "phone": phone,
                "gstin": gstin,
                "gst_type": gst_type,
                "period": period
            }
        )
        
        return attempt_id
    
    async def update_filing_status(
        self,
        phone: str,
        gstin: str,
        period: str,
        status: str,
        gst_type: Optional[str] = None,
        arn: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Updates filing status when user reports completion via track-completion endpoint.
        
        Args:
            phone: User's phone number
            gstin: GSTIN
            period: Filing period
            status: "completed" or "failed"
            gst_type: Optional GST type filter
            arn: Optional ARN number (for successful filings)
            error_message: Optional error message for failures
        
        Returns:
            True if updated successfully
        """
        collection = await self._get_collection()
        
        # Build query
        query = {
            "phone": phone,
            "gstin": gstin,
            "period": period
        }
        if gst_type:
            query["gst_type"] = gst_type
        
        # Find latest attempt
        attempt = await collection.find_one(
            query,
            sort=[("created_at", -1)]
        )
        
        if not attempt:
            logger.warning(
                f"No filing attempt found",
                extra={"phone": phone, "gstin": gstin, "period": period}
            )
            return False
        
        # Build update data
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow()
        }
        
        # Add completion timestamp and ARN for successful filings
        if status == "completed":
            update_data["completed_at"] = datetime.utcnow()
            if arn:
                update_data["arn"] = arn
        elif status == "failed" and error_message:
            update_data["error_message"] = error_message
            update_data["failed_at"] = datetime.utcnow()
        
        # Update
        result = await collection.update_one(
            {"_id": attempt["_id"]},
            {"$set": update_data}
        )
        
        logger.info(
            f"Filing status updated to {status}",
            extra={
                "phone": phone,
                "attempt_id": str(attempt["_id"]),
                "status": status,
                "gstin": gstin
            }
        )
        
        return result.modified_count > 0
    
    async def store_arn(
        self,
        phone: str,
        gstin: str,
        period: str,
        arn: str,
        gst_type: Optional[str] = None
    ) -> bool:
        """
        Stores ARN (Acknowledgement Reference Number) for a successful filing.
        Called from track-completion endpoint.
        
        Args:
            phone: User's phone number
            gstin: GSTIN
            period: Filing period  
            arn: ARN number
            gst_type: Optional GST type filter
        
        Returns:
            True if stored successfully
        """
        return await self.update_filing_status(
            phone=phone,
            gstin=gstin,
            period=period,
            status="completed",
            gst_type=gst_type,
            arn=arn
        )
    
    async def increment_retry_count(
        self,
        phone: str,
        gstin: str,
        period: str,
        gst_type: Optional[str] = None
    ) -> int:
        """
        Increments retry count when user regenerates SMS link.
        
        Args:
            phone: User's phone number
            gstin: GSTIN
            period: Filing period
            gst_type: Optional GST type filter
        
        Returns:
            New retry count
        """
        collection = await self._get_collection()
        
        query = {
            "phone": phone,
            "gstin": gstin,
            "period": period
        }
        if gst_type:
            query["gst_type"] = gst_type
        
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
        phone: str,
        gstin: Optional[str] = None,
        period: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Gets the latest filing attempt for a user.
        
        Args:
            phone: User's phone number
            gstin: Optional GSTIN filter
            period: Optional period filter
        
        Returns:
            Filing attempt dict or None
        """
        collection = await self._get_collection()
        
        query = {"phone": phone}
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
        phone: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Gets filing history for a user.
        
        Args:
            phone: User's phone number
            limit: Maximum number of attempts to return
        
        Returns:
            List of filing attempts
        """
        collection = await self._get_collection()
        
        cursor = collection.find(
            {"phone": phone}
        ).sort("created_at", -1).limit(limit)
        
        attempts = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string
        for attempt in attempts:
            attempt["_id"] = str(attempt["_id"])
        
        return attempts
    
    async def get_filing_stats(
        self,
        phone: str
    ) -> Dict[str, int]:
        """
        Gets filing statistics for a user.
        
        Args:
            phone: User's phone number
        
        Returns:
            Dict with counts: total, completed, failed, pending
        """
        collection = await self._get_collection()
        
        # Aggregate counts by status
        pipeline = [
            {"$match": {"phone": phone}},
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
        phone: str,
        gstin: str,
        period: str,
        hours: int = 24
    ) -> bool:
        """
        Checks if there's a recent successful filing to prevent duplicates.
        
        Args:
            phone: User's phone number
            gstin: GSTIN
            period: Period
            hours: Hours to look back
        
        Returns:
            True if recent filing exists
        """
        from datetime import timedelta
        
        collection = await self._get_collection()
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        attempt = await collection.find_one({
            "phone": phone,
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
