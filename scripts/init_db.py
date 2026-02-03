"""
Database initialization script - Minimal schema for GST Nil filing

Run once to create collections and indexes:
    python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# MongoDB connection - load from .env
MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME")

if not MONGODB_URL or not MONGODB_DB_NAME:
    raise ValueError("❌ MONGODB_URL and MONGODB_DB_NAME must be set in .env file")


async def create_indexes():
    """Create minimal indexes for efficient queries"""
    
    logger.info(f"🔌 Connecting to MongoDB: {MONGODB_DB_NAME}")
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[MONGODB_DB_NAME]
    
    try:
        # Test connection
        await client.admin.command('ping')
        logger.info("✅ Connected successfully\n")
        
        # ==================== USERS COLLECTION ====================
        logger.info("📋 Creating 'users' collection...")
        users = db.users
        
        # 1. Unique phone number
        await users.create_index(
            [("phone", ASCENDING)],
            unique=True,
            name="idx_phone"
        )
        logger.info("  ✅ Phone index created (unique)")
        
        # 2. GSTIN lookup
        await users.create_index(
            [("gstin", ASCENDING)],
            name="idx_gstin",
            sparse=True
        )
        logger.info("  ✅ GSTIN index created")
        
        # 3. Current state (for resuming conversations)
        await users.create_index(
            [("current_state", ASCENDING)],
            name="idx_state"
        )
        logger.info("  ✅ State index created")
        
        # 4. Auto-cleanup inactive sessions (expire after 24 hours of inactivity)
        await users.create_index(
            [("last_active", ASCENDING)],
            name="idx_ttl",
            expireAfterSeconds=86400  # 24 hours
        )
        logger.info("  ✅ TTL index created (24h auto-cleanup)")
        
        # ==================== FILING ATTEMPTS COLLECTION ====================
        logger.info("\n📋 Creating 'filing_attempts' collection...")
        filings = db.filing_attempts
        
        # 1. User's filing history
        await filings.create_index(
            [("phone", ASCENDING), ("created_at", DESCENDING)],
            name="idx_user_history"
        )
        logger.info("  ✅ User history index created")
        
        # 2. Prevent duplicate filings
        await filings.create_index(
            [("gstin", ASCENDING), ("period", ASCENDING)],
            unique=True,
            name="idx_unique_filing",
            partialFilterExpression={"status": "completed"}
        )
        logger.info("  ✅ Duplicate prevention index created")
        
        # 3. Status tracking
        await filings.create_index(
            [("status", ASCENDING)],
            name="idx_status"
        )
        logger.info("  ✅ Status index created")
        
        # ==================== VERIFICATION ====================
        logger.info("\n🔍 Verifying indexes...")
        
        for collection_name in ["users", "filing_attempts"]:
            collection = db[collection_name]
            indexes = await collection.index_information()
            logger.info(f"\n  {collection_name}:")
            for idx_name in indexes.keys():
                if idx_name != "_id_":
                    logger.info(f"    ✅ {idx_name}")
        
        # ==================== STATS ====================
        stats = {
            "users": await users.count_documents({}),
            "filing_attempts": await filings.count_documents({})
        }
        
        logger.info(f"\n📊 Current documents:")
        logger.info(f"  Users: {stats['users']}")
        logger.info(f"  Filing attempts: {stats['filing_attempts']}")
        
        logger.info("\n✅ Database initialization complete!")
        logger.info("\n🚀 Ready to start your bot!")
        
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        raise
    
    finally:
        client.close()


async def test_insert():
    """Test inserting a sample user (optional)"""
    logger.info("\n🧪 Testing database insert...")
    
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[MONGODB_DB_NAME]
    
    try:
        test_user = {
            "phone": "+919999999999",
            "name": "Test User",
            "gstin": None,
            "business_name": None,
            "current_state": "WELCOME",
            "session_data": {},
            "created_at": datetime.utcnow(),
            "last_active": datetime.utcnow()
        }
        
        result = await db.users.update_one(
            {"phone": test_user["phone"]},
            {"$setOnInsert": test_user},
            upsert=True
        )
        
        if result.upserted_id:
            logger.info("✅ Test user created")
        else:
            logger.info("ℹ️  Test user already exists")
        
    except Exception as e:
        logger.error(f"❌ Test insert failed: {e}")
    
    finally:
        client.close()


async def main():
    """Main initialization"""
    logger.info("=" * 60)
    logger.info("  NilEasy Database Setup")
    logger.info("=" * 60 + "\n")
    
    await create_indexes()
    
    # Uncomment to create test user
    # await test_insert()
    
    logger.info("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
