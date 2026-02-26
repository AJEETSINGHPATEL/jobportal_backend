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
import os
from pathlib import Path
from fastapi import FastAPI, Request, Depends, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.routers import auth, job, resume, company, review, notification, ai
from app.routers import profiles, profile, applications, saved_jobs, jobseeker, company_verification, job_alert, candidate_search
from app.routers import admin, employer
from app.database.database import get_db, engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("AI Job Portal API starting up (PostgreSQL mode)...")
    # Tables are created via create_tables.py usually, 
    # but we could call create_tables() here if desired.
    yield
    print("AI Job Portal API shutting down...")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create app with lifespan
app = FastAPI(title="AI Job Portal API", version="1.0.0", lifespan=lifespan)

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = exc.errors()
    print(f"Validation error for {request.method} {request.url}: {error_details}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": error_details, "body": str(exc.body)},
    )

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# Configure CORS
origins = [
    "http://localhost:3000",
    "https://jobflux.netlify.app/",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    os.getenv("FRONTEND_URL", "https://jobflux.netlify.app/")
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
routers = [
    auth, job, resume, company, review, notification, ai,
    profiles, profile, applications, saved_jobs, jobseeker,
    company_verification, job_alert, admin, employer, candidate_search
]

for r in routers:
    try:
        app.include_router(r.router)
    except Exception as e:
        print(f"Error including router {r.__name__ if hasattr(r, '__name__') else 'unknown'}: {e}")

@app.get("/")
async def root():
    return {"message": "AI Job Portal API (PostgreSQL)"}

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "PostgreSQL connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)