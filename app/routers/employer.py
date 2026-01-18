from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from bson import ObjectId
from typing import List
import datetime
from app.models.job import Job
from app.models.application import Application
from app.database.database import get_jobs_collection, get_applications_collection, get_users_collection
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/employer", tags=["Employer"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

@router.get("/dashboard/stats")
async def get_employer_dashboard_stats(token: str = Depends(oauth2_scheme)):
    """Get dashboard statistics for the employer"""
    current_user = await get_current_user(token)
    
    # Only employers can access this
    if current_user.get("role") != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can access dashboard stats"
        )
    
    jobs_collection = get_jobs_collection()
    applications_collection = get_applications_collection()
    
    # Get employer's jobs
    employer_jobs = []
    async for job in jobs_collection.find({"created_by": current_user["id"]}):
        job["id"] = str(job["_id"])
        del job["_id"]
        employer_jobs.append(job)
    
    total_jobs = len(employer_jobs)
    active_jobs = len([job for job in employer_jobs if job.get("is_active", False)])
    
    # Get applications for employer's jobs
    employer_job_ids = [job["id"] for job in employer_jobs]
    applications = []
    async for application in applications_collection.find({"job_id": {"$in": employer_job_ids}}):
        application["id"] = str(application["_id"])
        del application["_id"]
        applications.append(application)
    
    total_applications = len(applications)
    shortlisted_applications = len([app for app in applications if app.get("status") == "shortlisted"])
    
    return {
        "totalJobs": total_jobs,
        "activeJobs": active_jobs,
        "totalApplications": total_applications,
        "shortlisted": shortlisted_applications
    }

@router.get("/jobs")
async def get_employer_jobs(token: str = Depends(oauth2_scheme)):
    """Get jobs created by the employer"""
    current_user = await get_current_user(token)
    
    # Only employers can access this
    if current_user.get("role") != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can access their jobs"
        )
    
    jobs_collection = get_jobs_collection()
    
    jobs = []
    async for job in jobs_collection.find({"created_by": current_user["id"]}).sort("posted_date", -1):
        job["id"] = str(job["_id"])
        del job["_id"]
        
        # Count applications for this job
        applications_collection = get_applications_collection()
        application_count = await applications_collection.count_documents({"job_id": job["id"]})
        job["application_count"] = application_count
        
        jobs.append(Job(**job))
    
    return jobs

@router.get("/applications")
async def get_employer_applications(token: str = Depends(oauth2_scheme)):
    """Get applications for the employer's jobs"""
    current_user = await get_current_user(token)
    
    # Only employers can access this
    if current_user.get("role") != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can access their job applications"
        )
    
    jobs_collection = get_jobs_collection()
    applications_collection = get_applications_collection()
    users_collection = get_users_collection()
    
    # Get employer's jobs
    employer_jobs = []
    async for job in jobs_collection.find({"created_by": current_user["id"]}):
        employer_jobs.append(str(job["_id"]))
    
    applications = []
    async for application in applications_collection.find({"job_id": {"$in": employer_jobs}}):
        application["id"] = str(application["_id"])
        del application["_id"]
        
        # Get job details
        if ObjectId.is_valid(application["job_id"]):
            job = await jobs_collection.find_one({"_id": ObjectId(application["job_id"])})
            if job:
                application["job_title"] = job.get("title", "")
                application["company"] = job.get("company", "")
            else:
                application["job_title"] = "Job Not Found"
                application["company"] = "Unknown"
        else:
            application["job_title"] = "Invalid Job ID"
            application["company"] = "Unknown"
        
        # Get user details
        user = await users_collection.find_one({"_id": ObjectId(application["user_id"])})
        if user:
            application["applicant_name"] = user.get("full_name", user.get("email", "Unknown"))
            application["applicant_email"] = user.get("email", "")
        else:
            application["applicant_name"] = "Unknown"
            application["applicant_email"] = ""
        
        applications.append(Application(**application))
    
    return applications

@router.get("/activity")
async def get_employer_activity(token: str = Depends(oauth2_scheme)):
    """Get recent activity for the employer"""
    current_user = await get_current_user(token)
    
    # Only employers can access this
    if current_user.get("role") != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can access their activity"
        )
    
    jobs_collection = get_jobs_collection()
    applications_collection = get_applications_collection()
    users_collection = get_users_collection()
    
    # Get employer's jobs
    employer_jobs = []
    async for job in jobs_collection.find({"created_by": current_user["id"]}):
        employer_jobs.append({
            "id": str(job["_id"]),
            "title": job.get("title", ""),
            "created_at": job.get("posted_date", datetime.datetime.utcnow())
        })
    
    activity = []
    
    # Add job posting activities
    for job in employer_jobs:
        activity.append({
            "type": "job_posted",
            "title": job["title"],
            "description": f"Job posted: {job['title']}",
            "timestamp": job["created_at"],
            "icon": "plus"
        })
    
    # Add application activities
    for job in employer_jobs:
        async for app in applications_collection.find({"job_id": job["id"]}).sort("applied_date", -1).limit(5):
            user = await users_collection.find_one({"_id": ObjectId(app["user_id"])})
            applicant_name = user.get("full_name", user.get("email", "Applicant")) if user else "Applicant"
            
            activity.append({
                "type": "application_received",
                "title": applicant_name,
                "description": f"{applicant_name} applied for {job['title']}",
                "timestamp": app.get("applied_date", datetime.datetime.utcnow()),
                "icon": "user"
            })
    
    # Add shortlist activities
    for job in employer_jobs:
        async for app in applications_collection.find({"job_id": job["id"], "status": "shortlisted"}).sort("updated_date", -1):
            user = await users_collection.find_one({"_id": ObjectId(app["user_id"])})
            applicant_name = user.get("full_name", user.get("email", "Applicant")) if user else "Applicant"
            
            activity.append({
                "type": "shortlisted",
                "title": applicant_name,
                "description": f"{applicant_name} shortlisted for {job['title']}",
                "timestamp": app.get("updated_date", datetime.datetime.utcnow()),
                "icon": "star"
            })
    
    # Sort by most recent
    activity.sort(key=lambda x: x["timestamp"], reverse=True)
    
    # Limit to top 5 activities
    return activity[:5]