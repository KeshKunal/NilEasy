"""
app/db/indexes.py

Purpose: Database index management

- Creates unique and performance indexes
- Ensures fast lookups and data integrity
- TTL indexes for automatic cleanup
"""

from app.db.mongo import (
    get_users_collection,
    get_filing_attempts_collection
)
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_indexes():
    """
    Creates all necessary database indexes for optimal performance.
    This function is idempotent - safe to run multiple times.
    """
    try:
        users = get_users_collection()
        filings = get_filing_attempts_collection()
        
        logger.info("Creating database indexes...")
        
        # ==============================================
        # USERS COLLECTION INDEXES
        # ==============================================
        
        # Unique index on user_id (primary identifier)
        try:
            await users.create_index("user_id", unique=True, name="user_id_unique")
            logger.debug("Created unique index on users.user_id")
        except Exception as e:
            logger.debug(f"Index user_id_unique already exists or error: {e}")
        
        # Index on GSTIN for quick lookups
        try:
            await users.create_index("gstin", name="gstin_idx")
            logger.debug("Created index on users.gstin")
        except Exception as e:
            logger.debug(f"Index gstin_idx already exists or error: {e}")
        
        # Index on current_state for state-based queries
        try:
            await users.create_index("current_state", name="current_state_idx")
            logger.debug("Created index on users.current_state")
        except Exception as e:
            logger.debug(f"Index current_state_idx already exists or error: {e}")
        
        # Index on last_interaction for session expiry queries
        try:
            await users.create_index("last_interaction", name="last_interaction_idx")
            logger.debug("Created index on users.last_interaction")
        except Exception as e:
            logger.debug(f"Index last_interaction_idx already exists or error: {e}")
        
        # Compound index for user + state queries
        try:
            await users.create_index(
                [("user_id", 1), ("current_state", 1)],
                name="user_state_idx"
            )
            logger.debug("Created compound index on users.user_id + current_state")
        except Exception as e:
            logger.debug(f"Index user_state_idx already exists or error: {e}")
        
        # Index on created_at for analytics
        try:
            await users.create_index("created_at", name="created_at_idx")
            logger.debug("Created index on users.created_at")
        except Exception as e:
            logger.debug(f"Index created_at_idx already exists or error: {e}")
        
        # TTL index to automatically delete expired sessions after 30 days
        try:
            await users.create_index(
                "last_interaction",
                expireAfterSeconds=2592000,  # 30 days
                name="session_ttl_idx"
            )
            logger.debug("Created TTL index on users.last_interaction")
        except Exception as e:
            logger.debug(f"Index session_ttl_idx already exists or error: {e}")
        
        # ==============================================
        # FILING ATTEMPTS COLLECTION INDEXES
        # ==============================================
        
        # Compound index on user_id + created_at for user's filing history
        try:
            await filings.create_index(
                [("user_id", 1), ("created_at", -1)],
                name="user_filings_idx"
            )
            logger.debug("Created compound index on filing_attempts.user_id + created_at")
        except Exception as e:
            logger.debug(f"Index user_filings_idx already exists or error: {e}")
        
        # Index on GSTIN for lookups by business
        try:
            await filings.create_index("gstin", name="filing_gstin_idx")
            logger.debug("Created index on filing_attempts.gstin")
        except Exception as e:
            logger.debug(f"Index filing_gstin_idx already exists or error: {e}")
        
        # Index on status for filtering active/completed filings
        try:
            await filings.create_index("status", name="filing_status_idx")
            logger.debug("Created index on filing_attempts.status")
        except Exception as e:
            logger.debug(f"Index filing_status_idx already exists or error: {e}")
        
        # Compound index on GSTIN + period for duplicate detection
        try:
            await filings.create_index(
                [("gstin", 1), ("gst_type", 1), ("period", 1)],
                name="filing_uniqueness_idx"
            )
            logger.debug("Created compound index on filing_attempts.gstin + gst_type + period")
        except Exception as e:
            logger.debug(f"Index filing_uniqueness_idx already exists or error: {e}")
        
        # Index on created_at for time-based queries
        try:
            await filings.create_index("created_at", name="filing_created_idx")
            logger.debug("Created index on filing_attempts.created_at")
        except Exception as e:
            logger.debug(f"Index filing_created_idx already exists or error: {e}")
        
        # Index on completed_at for analytics
        try:
            await filings.create_index("completed_at", name="filing_completed_idx")
            logger.debug("Created index on filing_attempts.completed_at")
        except Exception as e:
            logger.debug(f"Index filing_completed_idx already exists or error: {e}")
        
        # TTL index to automatically delete old filing attempts after 90 days
        try:
            await filings.create_index(
                "created_at",
                expireAfterSeconds=7776000,  # 90 days
                name="filing_ttl_idx"
            )
            logger.debug("Created TTL index on filing_attempts.created_at")
        except Exception as e:
            logger.debug(f"Index filing_ttl_idx already exists or error: {e}")
        
        logger.info("✅ All database indexes created successfully")
        
        # Log index statistics
        user_indexes = await users.index_information()
        filing_indexes = await filings.index_information()
        
        logger.info(
            f"Index summary: Users={len(user_indexes)}, "
            f"Filings={len(filing_indexes)}"
        )
        
    except Exception as e:
        logger.error(f"Failed to create indexes: {str(e)}", exc_info=True)
        raise


async def drop_all_indexes():
    """
    Drops all custom indexes (keeps _id index).
    Use with caution! Only for maintenance/migration.
    """
    try:
        users = get_users_collection()
        filings = get_filing_attempts_collection()
        
        logger.warning("Dropping all database indexes...")
        
        # Drop all indexes except _id
        await users.drop_indexes()
        await filings.drop_indexes()
        
        logger.info("✅ All indexes dropped successfully")
        
    except Exception as e:
        logger.error(f"Failed to drop indexes: {str(e)}", exc_info=True)
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
