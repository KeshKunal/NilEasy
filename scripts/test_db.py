"""
Quick test to verify MongoDB connection and basic operations

Run: python scripts/test_db.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import os
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

from motor.motor_asyncio import AsyncIOMotorClient
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Load from .env
MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME")

if not MONGODB_URL or not MONGODB_DB_NAME:
    raise ValueError("❌ MONGODB_URL and MONGODB_DB_NAME must be set in .env file")


async def test_connection():
    """Test MongoDB connection"""
    print("=" * 60)
    print("  MongoDB Connection Test")
    print("=" * 60 + "\n")
    
    try:
        # Connect
        logger.info("🔌 Connecting to MongoDB...")
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[MONGODB_DB_NAME]
        
        # Test ping
        await client.admin.command('ping')
        logger.info("✅ Connection successful!\n")
        
        # List collections
        collections = await db.list_collection_names()
        logger.info(f"📦 Collections: {collections if collections else '(none yet)'}\n")
        
        # Test insert user
        logger.info("🧪 Testing user insert...")
        test_user = {
            "phone": "+919876543210",
            "name": "Test User",
            "gstin": None,
            "business_name": None,
            "gst_type": None,
            "current_state": "WELCOME",
            "session_data": {},
            "created_at": datetime.utcnow(),
            "last_active": datetime.utcnow()
        }
        
        result = await db.users.update_one(
            {"phone": test_user["phone"]},
            {"$set": test_user},
            upsert=True
        )
        
        if result.upserted_id:
            logger.info(f"✅ Created test user: {test_user['phone']}")
        else:
            logger.info(f"✅ Updated test user: {test_user['phone']}")
        
        # Fetch user
        user = await db.users.find_one({"phone": test_user["phone"]})
        logger.info(f"📄 User data: {user}\n")
        
        # Count documents
        user_count = await db.users.count_documents({})
        filing_count = await db.filing_attempts.count_documents({})
        
        logger.info(f"📊 Statistics:")
        logger.info(f"   Users: {user_count}")
        logger.info(f"   Filing attempts: {filing_count}\n")
        
        logger.info("✅ All tests passed!")
        
        client.close()
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_connection())
