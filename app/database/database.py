import motor.motor_asyncio
import os
from dotenv import load_dotenv
import certifi  # For SSL certificate handling on Windows
from pymongo.errors import ServerSelectionTimeoutError

load_dotenv()

def get_database():
    """Create and return a database instance - call this in each request context"""
    # Use only local MongoDB connection
    MONGODB_URI = "mongodb://localhost:27017/"

    # For local MongoDB, no special SSL handling needed
    client = motor.motor_asyncio.AsyncIOMotorClient(
        MONGODB_URI,
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=30000,
        socketTimeoutMS=30000,
        maxPoolSize=50,
        minPoolSize=5,
        retryWrites=True,
        retryReads=True,
        w="majority"
    )

    database = client.job_portal_db
    return database, client

# Create collections access functions instead of global objects
def get_users_collection():
    database, _ = get_database()
    return database.get_collection("users")

def get_jobs_collection():
    database, _ = get_database()
    return database.get_collection("jobs")

def get_applications_collection():
    database, _ = get_database()
    return database.get_collection("applications")

def get_resumes_collection():
    database, _ = get_database()
    return database.get_collection("resumes")

def get_companies_collection():
    database, _ = get_database()
    return database.get_collection("companies")

def get_ai_logs_collection():
    database, _ = get_database()
    return database.get_collection("ai_logs")

def get_notifications_collection():
    database, _ = get_database()
    return database.get_collection("notifications")

def get_reviews_collection():
    database, _ = get_database()
    return database.get_collection("reviews")

def get_job_seeker_profiles_collection():
    database, _ = get_database()
    return database.get_collection("job_seeker_profiles")

def get_recruiter_profiles_collection():
    database, _ = get_database()
    return database.get_collection("recruiter_profiles")

def get_saved_jobs_collection():
    database, _ = get_database()
    return database.get_collection("saved_jobs")

def get_company_verifications_collection():
    database, _ = get_database()
    return database.get_collection("company_verifications")

def get_job_alerts_collection():
    database, _ = get_database()
    return database.get_collection("job_alerts")

def get_profiles_collection():
    database, _ = get_database()
    return database.get_collection("profiles")

# Global database instance for backward compatibility
# Initialize with None to avoid connection issues at startup
users_collection = None
jobs_collection = None
applications_collection = None
resumes_collection = None
companies_collection = None
ai_logs_collection = None
notifications_collection = None
reviews_collection = None
job_seeker_profiles_collection = None
recruiter_profiles_collection = None
saved_jobs_collection = None
company_verifications_collection = None
job_alerts_collection = None
profiles_collection = None

def get_global_collections():
    """Initialize global collections with actual database connections"""
    global users_collection, jobs_collection, applications_collection, resumes_collection
    global companies_collection, ai_logs_collection, notifications_collection, reviews_collection
    global job_seeker_profiles_collection, recruiter_profiles_collection, saved_jobs_collection
    global company_verifications_collection, job_alerts_collection, profiles_collection
    
    users_collection = get_users_collection()
    jobs_collection = get_jobs_collection()
    applications_collection = get_applications_collection()
    resumes_collection = get_resumes_collection()
    companies_collection = get_companies_collection()
    ai_logs_collection = get_ai_logs_collection()
    notifications_collection = get_notifications_collection()
    reviews_collection = get_reviews_collection()
    job_seeker_profiles_collection = get_job_seeker_profiles_collection()
    recruiter_profiles_collection = get_recruiter_profiles_collection()
    saved_jobs_collection = get_saved_jobs_collection()
    company_verifications_collection = get_company_verifications_collection()
    job_alerts_collection = get_job_alerts_collection()
    profiles_collection = get_profiles_collection()

# Initialize global collections when module is imported
get_global_collections()