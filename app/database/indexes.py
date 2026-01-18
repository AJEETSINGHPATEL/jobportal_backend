from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError, ConfigurationError
import asyncio
import logging
import os
from dotenv import load_dotenv
import certifi  # For SSL certificate handling on Windows

load_dotenv()

# Use only local MongoDB connection
MONGODB_URI = "mongodb://localhost:27017/"

# For local MongoDB, no special SSL handling needed
client = AsyncIOMotorClient(
    MONGODB_URI, 
    serverSelectionTimeoutMS=5000
)

database = client.job_portal_db

async def create_indexes():
    """Create database indexes for local MongoDB"""
    try:
        # Try to ping the database to verify connection
        await client.admin.command('ping')
        print("Database connection verified for index creation")
    except Exception as e:
        print(f"Could not connect to MongoDB for index creation: {e}")
        print("Skipping index creation - indexes will be created when MongoDB is available")
        return  # Exit early if no connection

    try:
        # Create indexes for users collection
        try:
            users_collection = database.users
            await users_collection.create_index("email", unique=True)
            await users_collection.create_index("role")
            await users_collection.create_index("is_active")
            await users_collection.create_index("created_at")
            print("Users indexes created successfully")
        except Exception as e:
            print(f"Could not create users indexes: {e}")

        # Create indexes for jobs collection
        try:
            jobs_collection = database.jobs
            await jobs_collection.create_index("title")
            await jobs_collection.create_index("company")
            await jobs_collection.create_index("location")
            await jobs_collection.create_index("work_mode")
            await jobs_collection.create_index("created_by")  # Index for employer jobs
            await jobs_collection.create_index("posted_date")
            await jobs_collection.create_index("is_active")
            await jobs_collection.create_index([("salary_min", 1)])
            await jobs_collection.create_index([("salary_max", 1)])
            await jobs_collection.create_index([("title", "text"), ("description", "text")])  # Text search index
            await jobs_collection.create_index([("location", "text"), ("company", "text")])  # Additional text search
            print("Jobs indexes created successfully")
        except Exception as e:
            print(f"Could not create jobs indexes: {e}")

        # Create indexes for applications collection
        try:
            applications_collection = database.applications
            await applications_collection.create_index("user_id")
            await applications_collection.create_index("job_id")
            await applications_collection.create_index([("user_id", 1), ("job_id", 1)])  # Compound index
            await applications_collection.create_index("status")
            await applications_collection.create_index("applied_date")
            print("Applications indexes created successfully")
        except Exception as e:
            print(f"Could not create applications indexes: {e}")

        # Create indexes for resumes collection
        try:
            resumes_collection = database.resumes
            # Index on user_id for efficient user resume queries
            await resumes_collection.create_index([("user_id", 1)])
            # Index on uploaded_at for sorting by date
            await resumes_collection.create_index([("uploaded_at", -1)])
            # Compound index for user_id and uploaded_at for efficient filtering and sorting
            await resumes_collection.create_index([("user_id", 1), ("uploaded_at", -1)])
            # Index on file_name for file searches
            await resumes_collection.create_index([("file_name", 1)])
            print("Resumes indexes created successfully")
        except Exception as e:
            print(f"Could not create resumes indexes: {e}")

        # Create indexes for companies collection
        try:
            companies_collection = database.companies
            await companies_collection.create_index("name", unique=True)
            print("Companies indexes created successfully")
        except Exception as e:
            print(f"Could not create companies indexes: {e}")

        # Create indexes for notifications collection
        try:
            notifications_collection = database.notifications
            await notifications_collection.create_index("user_id")
            await notifications_collection.create_index("created_at")
            print("Notifications indexes created successfully")
        except Exception as e:
            print(f"Could not create notifications indexes: {e}")

        # Create indexes for reviews collection
        try:
            reviews_collection = database.reviews
            await reviews_collection.create_index("company_id")
            await reviews_collection.create_index("user_id")
            await reviews_collection.create_index("created_at")
            print("Reviews indexes created successfully")
        except Exception as e:
            print(f"Could not create reviews indexes: {e}")

        # Create indexes for job_seeker_profiles collection
        try:
            job_seeker_profiles_collection = database.job_seeker_profiles
            await job_seeker_profiles_collection.create_index("user_id", unique=True)
            print("Job seeker profiles indexes created successfully")
        except Exception as e:
            print(f"Could not create job seeker profiles indexes: {e}")

        # Create indexes for recruiter_profiles collection
        try:
            recruiter_profiles_collection = database.recruiter_profiles
            await recruiter_profiles_collection.create_index("user_id", unique=True)
            print("Recruiter profiles indexes created successfully")
        except Exception as e:
            print(f"Could not create recruiter profiles indexes: {e}")

        # Create indexes for saved_jobs collection
        try:
            saved_jobs_collection = database.saved_jobs
            await saved_jobs_collection.create_index("user_id")
            await saved_jobs_collection.create_index("job_id")
            print("Saved jobs indexes created successfully")
        except Exception as e:
            print(f"Could not create saved jobs indexes: {e}")

        # Create indexes for company_verifications collection
        try:
            company_verifications_collection = database.company_verifications
            await company_verifications_collection.create_index("company_id", unique=True)
            await company_verifications_collection.create_index("user_id")
            await company_verifications_collection.create_index("status")
            print("Company verifications indexes created successfully")
        except Exception as e:
            print(f"Could not create company verifications indexes: {e}")

        # Create indexes for job_alerts collection
        try:
            job_alerts_collection = database.job_alerts
            await job_alerts_collection.create_index("user_id")
            await job_alerts_collection.create_index("active")
            print("Job alerts indexes created successfully")
        except Exception as e:
            print(f"Could not create job alerts indexes: {e}")

        print("All database indexes creation attempted")
        
    except ServerSelectionTimeoutError:
        print("Could not connect to MongoDB server to create indexes (timeout)")
    except ConfigurationError as e:
        print(f"Configuration error during index creation: {e}")
    except Exception as e:
        print(f"Unexpected error during index creation: {e}")

if __name__ == "__main__":
    # Create a new event loop to avoid conflicts
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(create_indexes())
    finally:
        loop.close()