import asyncio
from app.db.mongo import connect_to_mongo, close_mongo_connection, get_database
from app.core.logging import get_logger

# Configure logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_indexes():
    await connect_to_mongo()
    db = await get_database()
    users = db.users
    
    try:
        # Check existing indexes
        indexes = await users.index_information()
        logger.info(f"Existing indexes: {list(indexes.keys())}")
        
        if "phone_idx" in indexes:
            logger.info("✅ 'phone_idx' (non-unique) exists.")
        elif "phone_unique" in indexes:
             logger.error("❌ 'phone_unique' STILL exists! It should have been removed.")
        else:
             logger.info("ℹ️ Phone index not found (might be creating on startup).")
            
    except Exception as e:
        logger.error(f"Error checking index: {e}")
    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(check_indexes())
