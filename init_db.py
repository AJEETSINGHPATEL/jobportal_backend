import asyncio
import sys
import os
import certifi  # For SSL certificate handling on Windows
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.database import (
    users_collection, 
    jobs_collection, 
    applications_collection, 
    resumes_collection, 
    companies_collection, 
    ai_logs_collection, 
    notifications_collection, 
    reviews_collection
)
import app.database.database as db_module

async def init_database():
    """Initialize database collections with proper indexes"""
    try:
        print("Initializing database collections and indexes...")
        
        # Create indexes for users collection
        await users_collection.create_index("email", unique=True)
        await users_collection.create_index("role")
        print("✓ Users collection indexes created")
        
        # Create indexes for jobs collection
        await jobs_collection.create_index("title")
        await jobs_collection.create_index("company")
        await jobs_collection.create_index("location")
        await jobs_collection.create_index("work_mode")
        await jobs_collection.create_index("skills")
        await jobs_collection.create_index("is_active")
        print("✓ Jobs collection indexes created")
        
        # Create indexes for applications collection
        await applications_collection.create_index("job_id")
        await applications_collection.create_index("user_id")
        await applications_collection.create_index("status")
        print("✓ Applications collection indexes created")
        
        # Create indexes for resumes collection
        await resumes_collection.create_index("user_id")
        await resumes_collection.create_index("created_at")
        print("✓ Resumes collection indexes created")
        
        # Create indexes for companies collection
        await companies_collection.create_index("name", unique=True)
        await companies_collection.create_index("is_verified")
        print("✓ Companies collection indexes created")
        
        # Create indexes for notifications collection
        await notifications_collection.create_index("user_id")
        await notifications_collection.create_index("is_read")
        await notifications_collection.create_index("created_at")
        print("✓ Notifications collection indexes created")
        
        # Create indexes for reviews collection
        await reviews_collection.create_index("company_id")
        await reviews_collection.create_index("user_id")
        await reviews_collection.create_index("rating")
        print("✓ Reviews collection indexes created")
        
        # List all collections
        collections = await db_module.database.list_collection_names()
        print(f"\nDatabase collections: {collections}")
        
        print("\nDatabase initialized successfully with indexes!")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(init_database())