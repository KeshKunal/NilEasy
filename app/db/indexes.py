"""
app/db/indexes.py

Purpose: Database index management

- Creates unique and performance indexes
- Ensures fast lookups and data integrity
"""

from app.db.mongo import (
    get_users_collection,
    get_filing_attempts_collection
)
from app.core.logging import get_logger

logger = get_logger(__name__)


async def drop_problematic_indexes():
    """
    Drops indexes that may cause issues.
    """
    try:
        users = get_users_collection()
        
        # Drop the problematic user_id_unique index if it exists
        try:
            await users.drop_index("user_id_unique")
            logger.info("Dropped problematic user_id_unique index")
        except Exception:
            pass  # Index may not exist
        
        # Drop user_state_idx if it uses user_id
        try:
            await users.drop_index("user_state_idx")
            logger.info("Dropped user_state_idx index")
        except Exception:
            pass
            
    except Exception as e:
        logger.warning(f"Error dropping indexes: {e}")


async def create_indexes():
    """
    Creates all necessary database indexes for optimal performance.
    This function is idempotent - safe to run multiple times.
    """
    try:
        users = get_users_collection()
        filings = get_filing_attempts_collection()
        
        logger.info("Creating database indexes...")
        
        # First, drop problematic indexes
        await drop_problematic_indexes()
        
        # ==============================================
        # USERS COLLECTION INDEXES
        # ==============================================
        
        # Unique index on phone (primary identifier)
        try:
            await users.create_index("phone", unique=True, name="phone_unique")
            logger.info("Created unique index on users.phone")
        except Exception as e:
            logger.debug(f"Index phone_unique already exists: {e}")
        
        # Index on GSTIN for quick lookups
        try:
            await users.create_index("gstin", name="gstin_idx", sparse=True)
            logger.info("Created index on users.gstin")
        except Exception as e:
            logger.debug(f"Index gstin_idx already exists: {e}")
        
        # Index on current_state for state-based queries
        try:
            await users.create_index("current_state", name="current_state_idx")
            logger.info("Created index on users.current_state")
        except Exception as e:
            logger.debug(f"Index current_state_idx already exists: {e}")
        
        # Index on last_active for session queries
        try:
            await users.create_index("last_active", name="last_active_idx")
            logger.info("Created index on users.last_active")
        except Exception as e:
            logger.debug(f"Index last_active_idx already exists: {e}")
        
        # Index on created_at for analytics
        try:
            await users.create_index("created_at", name="created_at_idx")
            logger.info("Created index on users.created_at")
        except Exception as e:
            logger.debug(f"Index created_at_idx already exists: {e}")
        
        # ==============================================
        # FILING ATTEMPTS COLLECTION INDEXES
        # ==============================================
        
        # Index on phone + created_at for user's filing history
        try:
            await filings.create_index(
                [("phone", 1), ("created_at", -1)],
                name="phone_filings_idx"
            )
            logger.info("Created index on filings.phone + created_at")
        except Exception as e:
            logger.debug(f"Index phone_filings_idx already exists: {e}")
        
        # Index on status for analytics
        try:
            await filings.create_index("status", name="status_idx")
            logger.info("Created index on filings.status")
        except Exception as e:
            logger.debug(f"Index status_idx already exists: {e}")
        
        # Index on gstin for GSTIN-based queries
        try:
            await filings.create_index("gstin", name="filing_gstin_idx")
            logger.info("Created index on filings.gstin")
        except Exception as e:
            logger.debug(f"Index filing_gstin_idx already exists: {e}")
        
        logger.info("✅ Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Error creating indexes: {e}", exc_info=True)
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
