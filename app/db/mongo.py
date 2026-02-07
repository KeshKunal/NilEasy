"""
app/db/mongo.py

Purpose: MongoDB connection setup (Unified schema)

- Initializes Motor client with connection pooling
- Single collection: users (with embedded filings and generated_links)
- Health checks and retry logic
- Proper connection lifecycle management
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from typing import Optional
import asyncio
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Global MongoDB client
_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


async def connect_to_mongo():
    """
    Establishes connection to MongoDB with retry logic.
    Called during application startup.
    """
    global _client, _database
    
    if _client is not None:
        logger.warning("MongoDB client already initialized")
        return
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                f"Attempting to connect to MongoDB (attempt {attempt}/{max_retries})"
            )
            
            # Fix URL encoding for special characters
            mongodb_url = settings.MONGODB_URL.replace("%%", "%25")
            
            _client = AsyncIOMotorClient(
                mongodb_url,
                maxPoolSize=50,
                minPoolSize=10,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                retryWrites=True,
                retryReads=True,
            )
            
            _database = _client[settings.MONGODB_DB_NAME]
            
            # Verify connection
            await _client.admin.command("ping")
            
            logger.info(
                f"✅ Successfully connected to MongoDB: {settings.MONGODB_DB_NAME}"
            )
            return
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(
                f"Failed to connect to MongoDB (attempt {attempt}/{max_retries}): {e}"
            )
            
            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.critical("Failed to connect to MongoDB after all retries")
                raise ConnectionError("Could not establish MongoDB connection") from e


async def close_mongo_connection():
    """
    Closes the MongoDB connection.
    Called during application shutdown.
    """
    global _client, _database
    
    if _client:
        logger.info("Closing MongoDB connection")
        _client.close()
        _client = None
        _database = None
        logger.info("MongoDB connection closed")


async def check_database_health() -> bool:
    """
    Checks if the database connection is healthy.
    
    Returns:
        True if connection is healthy, False otherwise
    """
    try:
        if _client is None:
            logger.error("MongoDB client not initialized")
            return False
        
        # Ping the database
        await _client.admin.command("ping")
        return True
        
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return False


async def get_database() -> AsyncIOMotorDatabase:
    """
    Returns the MongoDB database instance.
    
    Returns:
        AsyncIOMotorDatabase instance
        
    Raises:
        RuntimeError: If database is not initialized
    """
    if _database is None:
        raise RuntimeError(
            "Database not initialized. Call connect_to_mongo() during startup."
        )
    return _database


def get_users_collection():
    """
    Returns the users collection (unified schema).
    
    Unified Schema Fields:
    - phone: str (primary key)
    - name: str
    - gstin: str
    - business_name: str
    - legal_name: str
    - address: str
    - state: str
    - created_at: datetime
    - last_active: datetime
    - total_filings: int
    - successful_filings: int
    - failed_filings: int
    - current_filing_context: dict (temporary filing context)
    - filings: list[dict] (embedded filing history)
    - generated_links: list[dict] (embedded SMS links history)
    """
    if _database is None:
        raise RuntimeError(
            "Database not initialized. Call connect_to_mongo() during startup."
        )
    return _database["users"]
