from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from app.models.application import ApplicationCreate
from app.models.saved_job import SavedJobCreate
from app.models.job_seeker_profile import JobSeekerProfileCreate, JobSeekerProfileUpdate, JobSeekerProfile
from app.database.database import applications_collection, saved_jobs_collection, job_seeker_profiles_collection, jobs_collection
from app.utils.auth import get_current_user
from bson import ObjectId
from typing import List
import datetime

router = APIRouter(prefix="/api/jobseeker", tags=["Job Seeker"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

@router.post("/jobs/{job_id}/apply")
async def apply_for_job(job_id: str, token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists and is a job seeker
        user = await get_current_user(token)
        if user["role"] != "job_seeker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only job seekers can apply for jobs"
            )
        
        # Check if job exists
        job = await jobs_collection.find_one({"_id": ObjectId(job_id)})
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Check if already applied
        existing_application = await applications_collection.find_one({
            "job_id": job_id,
            "user_id": user["id"]
        })
        if existing_application:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already applied for this job"
            )
        
        # Create application
        application_data = {
            "job_id": job_id,
            "user_id": user["id"],
            "status": "applied",
            "created_at": datetime.datetime.now(),
            "updated_at": datetime.datetime.now()
        }
        result = await applications_collection.insert_one(application_data)
        application_data["id"] = str(result.inserted_id)
        
        # Increment job application count
        await jobs_collection.update_one(
            {"_id": ObjectId(job_id)},
            {"$inc": {"application_count": 1}}
        )
        
        return {
            "success": True,
            "message": "Successfully applied for the job",
            "application_id": application_data["id"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error applying for job: {str(e)}"
        )

@router.post("/jobs/{job_id}/save")
async def save_job(job_id: str, token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists and is a job seeker
        user = await get_current_user(token)
        if user["role"] != "job_seeker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only job seekers can save jobs"
            )
        
        # Check if job is already saved
        existing_saved_job = await saved_jobs_collection.find_one({
            "user_id": user["id"],
            "job_id": job_id
        })
        if existing_saved_job:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job already saved"
            )
        
        # Check if job exists
        job_exists = await jobs_collection.find_one({"_id": ObjectId(job_id)})
        if not job_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Save job
        saved_job_data = {
            "user_id": user["id"],
            "job_id": job_id,
            "created_at": datetime.datetime.now()
        }
        result = await saved_jobs_collection.insert_one(saved_job_data)
        saved_job_data["id"] = str(result.inserted_id)
        
        return {
            "success": True,
            "message": "Job saved successfully",
            "saved_job_id": saved_job_data["id"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving job: {str(e)}"
        )

@router.get("/applications")
async def get_applications(token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists and is a job seeker
        user = await get_current_user(token)
        if user["role"] != "job_seeker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only job seekers can view their applications"
            )
        
        # Get applications
        applications_cursor = applications_collection.find({"user_id": user["id"]})
        applications = []
        
        async for app in applications_cursor:
            # Get job details
            job = await jobs_collection.find_one({"_id": ObjectId(app["job_id"])})
            if job:
                app_data = {
                    "id": str(app["_id"]),
                    "job_id": app["job_id"],
                    "status": app["status"],
                    "created_at": app["created_at"],
                    "job_title": job["title"],
                    "company": job["company"],
                    "location": job["location"]
                }
                applications.append(app_data)
        
        return {
            "success": True,
            "data": applications
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching applications: {str(e)}"
        )

@router.get("/saved-jobs")
async def get_saved_jobs(token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists and is a job seeker
        user = await get_current_user(token)
        if user["role"] != "job_seeker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only job seekers can view saved jobs"
            )
        
        # Get saved jobs
        saved_jobs_cursor = saved_jobs_collection.find({"user_id": user["id"]}).sort("created_at", -1)
        saved_jobs = []
        
        async for saved_job in saved_jobs_cursor:
            # Get job details
            job = await jobs_collection.find_one({"_id": ObjectId(saved_job["job_id"])})
            if job:
                job_data = {
                    "id": str(saved_job["_id"]),
                    "job_id": saved_job["job_id"],
                    "created_at": saved_job["created_at"],
                    "job_details": {
                        "title": job["title"],
                        "company": job["company"],
                        "location": job["location"],
                        "salary_min": job.get("salary_min"),
                        "salary_max": job.get("salary_max"),
                        "experience_required": job.get("experience_required"),
                        "work_mode": job.get("work_mode"),
                        "skills": job.get("skills", [])
                    }
                }
                saved_jobs.append(job_data)
        
        return {
            "success": True,
            "data": saved_jobs
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching saved jobs: {str(e)}"
        )

@router.get("/profile")
async def get_profile(token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists and is a job seeker
        user = await get_current_user(token)
        if user["role"] != "job_seeker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only job seekers can view their profile"
            )
        
        # Get profile
        profile = await job_seeker_profiles_collection.find_one({"user_id": user["id"]})
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )
        
        profile["id"] = str(profile["_id"])
        del profile["_id"]
        
        return {
            "success": True,
            "data": profile
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching profile: {str(e)}"
        )

@router.put("/profile")
async def update_profile(profile_data: JobSeekerProfileUpdate, token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists and is a job seeker
        user = await get_current_user(token)
        if user["role"] != "job_seeker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only job seekers can update their profile"
            )
        
        # Check if profile exists
        existing_profile = await job_seeker_profiles_collection.find_one({"user_id": user["id"]})
        
        profile_dict = profile_data.dict(exclude_unset=True)
        profile_dict["updated_at"] = datetime.datetime.now()
        
        if existing_profile:
            # Update existing profile
            await job_seeker_profiles_collection.update_one(
                {"user_id": user["id"]},
                {"$set": profile_dict}
            )
            updated_profile = await job_seeker_profiles_collection.find_one({"user_id": user["id"]})
        else:
            # Create new profile
            profile_dict["user_id"] = user["id"]
            profile_dict["created_at"] = datetime.datetime.now()
            result = await job_seeker_profiles_collection.insert_one(profile_dict)
            profile_dict["id"] = str(result.inserted_id)
            updated_profile = profile_dict
        
        updated_profile["id"] = str(updated_profile["_id"])
        del updated_profile["_id"]
        
        return {
            "success": True,
            "message": "Profile updated successfully",
            "data": updated_profile
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating profile: {str(e)}"
        )