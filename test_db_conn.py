import asyncio
import motor.motor_asyncio
import sys
import os

async def test_mongodb_connection():
    print("Testing MongoDB connection...")
    MONGODB_URI = "mongodb://localhost:27017/"
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        # The ismaster command is cheap and does not require auth.
        await client.admin.command('ismaster')
        print("SUCCESS: Connected to MongoDB at", MONGODB_URI)
        
        db = client.job_portal_db
        count = await db.users.estimated_document_count()
        print(f"Data Info: Estimated users count: {count}")
        
        # List collections
        collections = await db.list_collection_names()
        print(f"Collections in 'job_portal_db': {collections}")
        
    except Exception as e:
        print(f"ERROR: Failed to connect to MongoDB: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_mongodb_connection())
