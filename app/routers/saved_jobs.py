from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from app.models.saved_job import SavedJobCreate, SavedJob
from app.database.database import get_saved_jobs_collection, get_jobs_collection
from app.utils.auth import get_current_user
from bson import ObjectId
from typing import List
import datetime

router = APIRouter(prefix="/api/saved-jobs", tags=["Saved Jobs"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

@router.post("/", response_model=SavedJob)
async def save_job(job: SavedJobCreate, token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists and is a job seeker
        user = await get_current_user(token)
        if user["role"] != "job_seeker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only job seekers can save jobs"
            )
        
        # Get saved jobs collection in the current request context
        saved_jobs_collection = get_saved_jobs_collection()
        jobs_collection = get_jobs_collection()
        
        # Check if job is already saved
        existing_saved_job = await saved_jobs_collection.find_one({
            "user_id": user["id"],
            "job_id": job.job_id
        })
        if existing_saved_job:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job already saved"
            )
        
        # Check if job exists
        job_exists = await jobs_collection.find_one({"_id": ObjectId(job.job_id)})
        if not job_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Save job
        saved_job_dict = job.dict()
        saved_job_dict["user_id"] = user["id"]
        saved_job_dict["created_at"] = datetime.datetime.now()
        result = await saved_jobs_collection.insert_one(saved_job_dict)
        saved_job_dict["id"] = str(result.inserted_id)
        
        return SavedJob(**saved_job_dict)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving job: {str(e)}"
        )

@router.get("/", response_model=List[dict])
async def get_saved_jobs(token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists and is a job seeker
        user = await get_current_user(token)
        if user["role"] != "job_seeker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only job seekers can view saved jobs"
            )
        
        # Get collections in the current request context
        saved_jobs_collection = get_saved_jobs_collection()
        jobs_collection = get_jobs_collection()
        
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
        
        return saved_jobs
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching saved jobs: {str(e)}"
        )

@router.delete("/{saved_job_id}")
async def unsave_job(saved_job_id: str, token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists and is a job seeker
        user = await get_current_user(token)
        if user["role"] != "job_seeker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only job seekers can unsave jobs"
            )
        
        # Get saved jobs collection in the current request context
        saved_jobs_collection = get_saved_jobs_collection()
        
        # Find saved job
        saved_job = await saved_jobs_collection.find_one({
            "_id": ObjectId(saved_job_id),
            "user_id": user["id"]
        })
        if not saved_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved job not found"
            )
        
        # Delete saved job
        await saved_jobs_collection.delete_one({"_id": ObjectId(saved_job_id)})
        
        return {"message": "Job unsaved successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error unsaving job: {str(e)}"
        )