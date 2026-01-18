from contextlib import asynccontextmanager
import bcrypt
# Monkey patch bcrypt for passlib compatibility
if not hasattr(bcrypt, "__about__"):
    try:
        class About:
            __version__ = bcrypt.__version__
        bcrypt.__about__ = About()
    except Exception:
        pass

import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.routers import auth, job, resume, company, review, notification, ai
from app.routers import profiles, profile, applications, saved_jobs, jobseeker, company_verification, job_alert, candidate_search
from app.routers import admin, employer
from app.database.indexes import create_indexes
import os

from create_admin_user import create_admin_user

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("AI Job Portal API starting up...")
    # Create database indexes
    try:
        await create_indexes()
        print("Database indexes created successfully")
    except Exception as e:
        print(f"Error creating database indexes: {e}")
    
    # Create default admin user if it doesn't exist
    try:
        await create_admin_user()
        print("Admin user initialization completed")
    except Exception as e:
        print(f"Error initializing admin user: {e}")
    
    yield  # This is where the application runs
    print("AI Job Portal API shutting down...")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create app with lifespan
app = FastAPI(title="AI Job Portal API", version="1.0.0", lifespan=lifespan)

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount uploads directory for static access
# Mount uploads directory for static access (using absolute path)
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# Configure CORS with more restrictive settings
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    os.getenv("FRONTEND_URL", "http://localhost:3000")
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
try:
    print("Including auth router...")
    app.include_router(auth.router)
    print("Auth router included successfully")
except Exception as e:
    print(f"Error including auth router: {e}")

try:
    print("Including job router...")
    app.include_router(job.router)
    print("Job router included successfully")
except Exception as e:
    print(f"Error including job router: {e}")

try:
    print("Including resume router...")
    app.include_router(resume.router)
    print("Resume router included successfully")
except Exception as e:
    print(f"Error including resume router: {e}")

try:
    print("Including company router...")
    app.include_router(company.router)
    print("Company router included successfully")
except Exception as e:
    print(f"Error including company router: {e}")

try:
    print("Including review router...")
    app.include_router(review.router)
    print("Review router included successfully")
except Exception as e:
    print(f"Error including review router: {e}")

try:
    print("Including notification router...")
    app.include_router(notification.router)
    print("Notification router included successfully")
except Exception as e:
    print(f"Error including notification router: {e}")

try:
    print("Including ai router...")
    app.include_router(ai.router)
    print("AI router included successfully")
except Exception as e:
    print(f"Error including ai router: {e}")

try:
    print("Including profiles router...")
    app.include_router(profiles.router)
    print("Profiles router included successfully")
except Exception as e:
    print(f"Error including profiles router: {e}")

try:
    print("Including profile router...")
    app.include_router(profile.router)
    print("Profile router included successfully")
except Exception as e:
    print(f"Error including profile router: {e}")

try:
    print("Including applications router...")
    app.include_router(applications.router)
    print("Applications router included successfully")
except Exception as e:
    print(f"Error including applications router: {e}")

try:
    print("Including saved_jobs router...")
    app.include_router(saved_jobs.router)
    print("Saved jobs router included successfully")
except Exception as e:
    print(f"Error including saved_jobs router: {e}")

try:
    print("Including jobseeker router...")
    app.include_router(jobseeker.router)
    print("Jobseeker router included successfully")
except Exception as e:
    print(f"Error including jobseeker router: {e}")

try:
    print("Including company_verification router...")
    app.include_router(company_verification.router)
    print("Company verification router included successfully")
except Exception as e:
    print(f"Error including company_verification router: {e}")

try:
    print("Including job_alert router...")
    app.include_router(job_alert.router)
    print("Job alert router included successfully")
    
    try:
        print("Including admin router...")
        app.include_router(admin.router)
        print("Admin router included successfully")
    except Exception as e:
        print(f"Error including admin router: {e}")
    
    try:
        print("Including employer router...")
        app.include_router(employer.router)
        print("Employer router included successfully")
    except Exception as e:
        print(f"Error including employer router: {e}")
except Exception as e:
    print(f"Error including job_alert router: {e}")

try:
    print("Including candidate_search router...")
    app.include_router(candidate_search.router)
    print("Candidate search router included successfully")
except Exception as e:
    print(f"Error including candidate_search router: {e}")

@app.get("/")
async def root():
    return {"message": "AI Job Portal API"}

@app.get("/health")
async def health_check():
    try:
        # Test database connectivity
        from app.database.database import get_users_collection
        # This will raise an exception if database is not accessible
        users_collection = get_users_collection()
        await users_collection.estimated_document_count()  # Test the connection
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
