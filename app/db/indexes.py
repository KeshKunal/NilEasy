"""
app/db/indexes.py

Purpose: Database index management

- Creates unique and performance indexes
- Ensures fast lookups and data integrity
- TTL indexes for automatic cleanup
"""

from app.db.mongo import (
    get_users_collection,
    get_filing_attempts_collection,
    get_sessions_collection
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
        sessions = get_sessions_collection()
        
        logger.info("Creating database indexes...")
        
        # ==============================================
        # USERS COLLECTION INDEXES
        # ==============================================
        
        # Unique index on user_id (primary identifier)
        await users.create_index("user_id", unique=True, name="user_id_unique")
        logger.debug("Created unique index on users.user_id")
        
        # Index on GSTIN for quick lookups
        await users.create_index("gstin", name="gstin_idx")
        logger.debug("Created index on users.gstin")
        
        # Index on current_state for state-based queries
        await users.create_index("current_state", name="current_state_idx")
        logger.debug("Created index on users.current_state")
        
        # Index on last_interaction for session expiry queries
        await users.create_index("last_interaction", name="last_interaction_idx")
        logger.debug("Created index on users.last_interaction")
        
        # Compound index for user + state queries
        await users.create_index(
            [("user_id", 1), ("current_state", 1)],
            name="user_state_idx"
        )
        logger.debug("Created compound index on users.user_id + current_state")
        
        # Index on created_at for analytics
        await users.create_index("created_at", name="created_at_idx")
        logger.debug("Created index on users.created_at")
        
        # TTL index to automatically delete expired sessions after 30 days
        await users.create_index(
            "last_interaction",
            expireAfterSeconds=2592000,  # 30 days
            name="session_ttl_idx"
        )
        logger.debug("Created TTL index on users.last_interaction")
        
        # ==============================================
        # FILING ATTEMPTS COLLECTION INDEXES
        # ==============================================
        
        # Compound index on user_id + created_at for user's filing history
        await filings.create_index(
            [("user_id", 1), ("created_at", -1)],
            name="user_filings_idx"
        )
        logger.debug("Created compound index on filing_attempts.user_id + created_at")
        
        # Index on GSTIN for lookups by business
        await filings.create_index("gstin", name="filing_gstin_idx")
        logger.debug("Created index on filing_attempts.gstin")
        
        # Index on status for filtering active/completed filings
        await filings.create_index("status", name="filing_status_idx")
        logger.debug("Created index on filing_attempts.status")
        
        # Compound index on GSTIN + period for duplicate detection
        await filings.create_index(
            [("gstin", 1), ("gst_type", 1), ("period", 1)],
            name="filing_uniqueness_idx"
        )
        logger.debug("Created compound index on filing_attempts.gstin + gst_type + period")
        
        # Index on created_at for time-based queries
        await filings.create_index("created_at", name="filing_created_idx")
        logger.debug("Created index on filing_attempts.created_at")
        
        # Index on completed_at for analytics
        await filings.create_index("completed_at", name="filing_completed_idx")
        logger.debug("Created index on filing_attempts.completed_at")
        
        # TTL index to automatically delete old filing attempts after 90 days
        await filings.create_index(
            "created_at",
            expireAfterSeconds=7776000,  # 90 days
            name="filing_ttl_idx"
        )
        logger.debug("Created TTL index on filing_attempts.created_at")
        
        # ==============================================
        # SESSIONS COLLECTION INDEXES
        # ==============================================
        
        # Unique index on session_id
        await sessions.create_index("session_id", unique=True, name="session_id_unique")
        logger.debug("Created unique index on sessions.session_id")
        
        # Index on user_id for user session lookups
        await sessions.create_index("user_id", name="session_user_idx")
        logger.debug("Created index on sessions.user_id")
        
        # TTL index to automatically delete expired sessions after 1 hour
        await sessions.create_index(
            "expires_at",
            expireAfterSeconds=0,  # Delete when expires_at is reached
            name="session_expiry_ttl_idx"
        )
        logger.debug("Created TTL index on sessions.expires_at")
        
        # Index on created_at for analytics
        await sessions.create_index("created_at", name="session_created_idx")
        logger.debug("Created index on sessions.created_at")
        
        logger.info("✅ All database indexes created successfully")
        
        # Log index statistics
        user_indexes = await users.index_information()
        filing_indexes = await filings.index_information()
        session_indexes = await sessions.index_information()
        
        logger.info(
            f"Index summary: Users={len(user_indexes)}, "
            f"Filings={len(filing_indexes)}, "
            f"Sessions={len(session_indexes)}"
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
        sessions = get_sessions_collection()
        
        logger.warning("Dropping all database indexes...")
        
        # Drop all indexes except _id
        await users.drop_indexes()
        await filings.drop_indexes()
        await sessions.drop_indexes()
        
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
