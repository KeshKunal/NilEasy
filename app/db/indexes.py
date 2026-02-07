"""
app/db/indexes.py

Purpose: Database index management for unified schema

- Creates indexes for users collection only
- Optimized for phone-based lookups and embedded array queries
- Ensures fast lookups and data integrity
"""

from app.db.mongo import get_database
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_indexes():
    """
    Creates all necessary database indexes for optimal performance.
    This function is idempotent - safe to run multiple times.
    
    Unified Schema: All data stored in users collection with embedded arrays.
    """
    try:
        db = await get_database()
        users = db.users
        
        logger.info("Creating database indexes...")
        
        # ==============================================
        # USERS COLLECTION INDEXES
        # ==============================================
        
        # Unique index on phone (primary identifier)
        try:
            await users.create_index("phone", unique=True, sparse=True, name="phone_unique")
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
        
        # ==============================================
        # EMBEDDED FILINGS ARRAY INDEXES
        # ==============================================
        
        # Compound index for querying filings by gstin + period
        try:
            await users.create_index(
                [("filings.gstin", 1), ("filings.period", 1)],
                name="filings_gstin_period_idx",
                sparse=True
            )
            logger.info("✅ Created index on users.filings.gstin + period")
        except Exception as e:
            logger.debug(f"Index filings_gstin_period_idx already exists: {str(e)}")
        
        # Index on filings status for analytics
        try:
            await users.create_index("filings.status", name="filings_status_idx", sparse=True)
            logger.info("✅ Created index on users.filings.status")
        except Exception as e:
            logger.debug(f"Index filings_status_idx already exists: {str(e)}")
        
        # ==============================================
        # EMBEDDED GENERATED_LINKS ARRAY INDEXES
        # ==============================================
        
        # Index on short_code for link click tracking
        try:
            await users.create_index(
                "generated_links.short_code",
                name="links_short_code_idx",
                sparse=True
            )
            logger.info("✅ Created index on users.generated_links.short_code")
        except Exception as e:
            logger.debug(f"Index links_short_code_idx already exists: {str(e)}")
        
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
