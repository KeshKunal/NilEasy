"""
app/services/gstin_cache_service.py

Purpose: Cache verified GSTIN business details to skip captcha

- Stores business details after successful captcha verification
- Retrieves cached details to skip captcha on subsequent requests
- Auto-expires cache after 30 days (GST details rarely change)
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.mongo import get_database
from app.core.logging import get_logger

logger = get_logger(__name__)


class GSTINCacheService:
    """Service for caching GSTIN business details."""
    
    def __init__(self):
        self.collection: Optional[AsyncIOMotorCollection] = None
    
    async def _get_collection(self) -> AsyncIOMotorCollection:
        """Get gstin_cache collection."""
        if not self.collection:
            db = await get_database()
            self.collection = db["gstin_cache"]
        return self.collection
    
    async def get_cached_details(
        self,
        gstin: str,
        max_age_days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves cached business details for a GSTIN.
        
        Args:
            gstin: 15-digit GSTIN
            max_age_days: Maximum age of cache in days (default 30)
        
        Returns:
            Business details dict or None if not cached/expired
        """
        collection = await self._get_collection()
        
        cutoff_time = datetime.utcnow() - timedelta(days=max_age_days)
        
        cached = await collection.find_one({
            "gstin": gstin,
            "updated_at": {"$gte": cutoff_time}
        })
        
        if cached:
            logger.info(
                f"GSTIN cache hit",
                extra={
                    "gstin": gstin,
                    "cached_at": cached.get("updated_at")
                }
            )
            
            # Return business details in expected format
            return {
                "business_name": cached.get("business_name"),
                "legal_name": cached.get("legal_name"),
                "address": cached.get("address"),
                "registration_date": cached.get("registration_date"),
                "status": cached.get("status"),
                "gstin": gstin,
                "cached": True  # Flag to indicate this is from cache
            }
        
        logger.debug(f"GSTIN cache miss", extra={"gstin": gstin})
        return None
    
    async def cache_details(
        self,
        gstin: str,
        business_name: str,
        legal_name: str,
        address: str,
        registration_date: str,
        status: str
    ) -> bool:
        """
        Caches business details for a GSTIN after successful verification.
        
        Args:
            gstin: 15-digit GSTIN
            business_name: Trade/business name
            legal_name: Legal registered name
            address: Principal place of business address
            registration_date: Registration date
            status: Active/Inactive status
        
        Returns:
            True if cached successfully
        """
        collection = await self._get_collection()
        
        cache_data = {
            "gstin": gstin,
            "business_name": business_name,
            "legal_name": legal_name,
            "address": address,
            "registration_date": registration_date,
            "status": status,
            "updated_at": datetime.utcnow()
        }
        
        # Upsert to update if exists
        result = await collection.update_one(
            {"gstin": gstin},
            {
                "$set": cache_data,
                "$setOnInsert": {"created_at": datetime.utcnow()}
            },
            upsert=True
        )
        
        logger.info(
            f"GSTIN details cached",
            extra={
                "gstin": gstin,
                "business_name": business_name
            }
        )
        
        return result.acknowledged
    
    async def invalidate_cache(self, gstin: str) -> bool:
        """
        Invalidates (deletes) cached details for a GSTIN.
        Useful if business details change.
        
        Args:
            gstin: 15-digit GSTIN
        
        Returns:
            True if deleted successfully
        """
        collection = await self._get_collection()
        
        result = await collection.delete_one({"gstin": gstin})
        
        if result.deleted_count > 0:
            logger.info(f"GSTIN cache invalidated", extra={"gstin": gstin})
        
        return result.deleted_count > 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Gets cache statistics.
        
        Returns:
            Dict with total cached GSTINs and age distribution
        """
        collection = await self._get_collection()
        
        total = await collection.count_documents({})
        
        # Count by age buckets
        now = datetime.utcnow()
        buckets = {
            "last_7_days": await collection.count_documents({
                "updated_at": {"$gte": now - timedelta(days=7)}
            }),
            "last_30_days": await collection.count_documents({
                "updated_at": {"$gte": now - timedelta(days=30)}
            }),
            "older": 0
        }
        buckets["older"] = total - buckets["last_30_days"]
        
        return {
            "total": total,
            "age_distribution": buckets
        }


# Global service instance
_gstin_cache_service: Optional[GSTINCacheService] = None


def get_gstin_cache_service() -> GSTINCacheService:
    """Get or create GSTIN cache service instance."""
    global _gstin_cache_service
    if _gstin_cache_service is None:
        _gstin_cache_service = GSTINCacheService()
    return _gstin_cache_service
