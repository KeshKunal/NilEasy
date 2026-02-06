"""
app/db/indexes.py

Purpose: Database index management for AiSensy architecture

- Creates unique and performance indexes
- Ensures fast lookups and data integrity
- Optimized for stateless API architecture
"""

from app.db.mongo import get_database
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_indexes():
    """
    Creates all necessary database indexes for optimal performance.
    This function is idempotent - safe to run multiple times.
    
    Optimized for AiSensy stateless API architecture:
    - Users collection: phone-based lookups
    - Filings collection: analytics and tracking
    """
    try:
        db = await get_database()
        users = db.users
        filings = db.filings
        
        logger.info("Creating database indexes...")
        
        # ==============================================
        # USERS COLLECTION INDEXES
        # ==============================================
        
        # Unique index on phone (primary identifier)
        try:
            await users.create_index("phone", unique=True, name="phone_unique")
            logger.info("✅ Created unique index on users.phone")
        except Exception as e:
            logger.debug(f"Index phone_unique already exists: {str(e)}")
        
        # Index on GSTIN for quick lookups
        try:
            await users.create_index("gstin", name="gstin_idx", sparse=True)
            logger.info("✅ Created index on users.gstin")
        except Exception as e:
            logger.debug(f"Index gstin_idx already exists: {str(e)}")
        
        # Index on last_active for analytics
        try:
            await users.create_index("last_active", name="last_active_idx")
            logger.info("✅ Created index on users.last_active")
        except Exception as e:
            logger.debug(f"Index last_active_idx already exists: {str(e)}")
        
        # Index on created_at for analytics
        try:
            await users.create_index("created_at", name="created_at_idx")
            logger.info("✅ Created index on users.created_at")
        except Exception as e:
            logger.debug(f"Index created_at_idx already exists: {str(e)}")
        
        # Index on gst_data.gstin for GSTIN-based cache lookups
        try:
            await users.create_index("gst_data.gstin", name="gst_data_gstin_idx", sparse=True)
            logger.info("✅ Created index on users.gst_data.gstin")
        except Exception as e:
            logger.debug(f"Index gst_data_gstin_idx already exists: {str(e)}")
        
        # ==============================================
        # FILINGS COLLECTION INDEXES
        # ==============================================
        
        # Compound index on phone + timestamp for user's filing history
        try:
            await filings.create_index(
                [("phone", 1), ("timestamp", -1)],
                name="phone_filings_idx"
            )
            logger.info("✅ Created index on filings.phone + timestamp")
        except Exception as e:
            logger.debug(f"Index phone_filings_idx already exists: {str(e)}")
        
        # Index on status for analytics (completed/failed counts)
        try:
            await filings.create_index("status", name="status_idx")
            logger.info("✅ Created index on filings.status")
        except Exception as e:
            logger.debug(f"Index status_idx already exists: {str(e)}")
        
        # Index on gstin for GSTIN-based queries
        try:
            await filings.create_index("gstin", name="filing_gstin_idx")
            logger.info("✅ Created index on filings.gstin")
        except Exception as e:
            logger.debug(f"Index filing_gstin_idx already exists: {str(e)}")
        
        # Compound index on gstin + period for duplicate prevention
        try:
            await filings.create_index(
                [("gstin", 1), ("period", 1), ("gst_type", 1)],
                name="filing_unique_idx"
            )
            logger.info("✅ Created compound index on filings.gstin + period + gst_type")
        except Exception as e:
            logger.debug(f"Index filing_unique_idx already exists: {str(e)}")
        
        # Index on timestamp for time-based queries
        try:
            await filings.create_index("timestamp", name="timestamp_idx")
            logger.info("✅ Created index on filings.timestamp")
        except Exception as e:
            logger.debug(f"Index timestamp_idx already exists: {str(e)}")
        
        logger.info("🎉 All database indexes created successfully")
        
    except Exception as e:
        logger.error(f"❌ Error creating indexes: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    """
    Run this script directly to create indexes manually.
    """
    import asyncio
    from app.db.mongo import connect_to_mongo, close_mongo_connection
    
    async def main():
        await connect_to_mongo()
        await create_indexes()
        await close_mongo_connection()
    
    asyncio.run(main())
