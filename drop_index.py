import asyncio
from app.db.mongo import connect_to_mongo, close_mongo_connection, get_database
from app.core.logging import get_logger

# Configure logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def drop_phone_index():
    await connect_to_mongo()
    db = await get_database()
    users = db.users
    
    try:
        # Check existing indexes
        indexes = await users.index_information()
        logger.info(f"Existing indexes: {list(indexes.keys())}")
        
        if "phone_unique" in indexes:
            logger.info("Dropping unique index 'phone_unique'...")
            await users.drop_index("phone_unique")
            logger.info("✅ Dropped 'phone_unique' index.")
        else:
            logger.info("'phone_unique' index not found.")
            
    except Exception as e:
        logger.error(f"Error dropping index: {e}")
    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(drop_phone_index())
