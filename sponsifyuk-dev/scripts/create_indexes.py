#!/usr/bin/env python3
"""
Script to create MongoDB indexes for production performance optimization
"""
import asyncio
import os
import sys
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Add backend to path
ROOT_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / '.env')

async def create_indexes():
    """Create MongoDB indexes for performance optimization"""
    mongo_url = os.environ['MONGO_URL']
    db_name = os.environ['DB_NAME']
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("Creating MongoDB indexes for production optimization...")
    
    # Jobs collection indexes
    await db.jobs.create_index([("posted_date", -1)])
    print("✓ Created index on jobs.posted_date")
    
    await db.jobs.create_index([("industry", 1), ("job_type", 1), ("experience_level", 1)])
    print("✓ Created compound index on jobs filters")
    
    await db.jobs.create_index([("title", "text"), ("company", "text"), ("description", "text")])
    print("✓ Created text index on jobs for search")
    
    # User sessions indexes
    await db.user_sessions.create_index([("session_token", 1)])
    print("✓ Created index on user_sessions.session_token")
    
    await db.user_sessions.create_index([("expires_at", 1)], expireAfterSeconds=0)
    print("✓ Created TTL index on user_sessions.expires_at")
    
    # Users collection indexes
    await db.users.create_index([("id", 1)], unique=True)
    print("✓ Created unique index on users.id")
    
    await db.users.create_index([("email", 1)], unique=True)
    print("✓ Created unique index on users.email")
    
    # Saved jobs indexes
    await db.saved_jobs.create_index([("user_id", 1)])
    print("✓ Created index on saved_jobs.user_id")
    
    await db.saved_jobs.create_index([("user_id", 1), ("job_id", 1)], unique=True)
    print("✓ Created compound unique index on saved_jobs")
    
    print("\n✅ All indexes created successfully!")
    print("Application is now optimized for production deployment.")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(create_indexes())
