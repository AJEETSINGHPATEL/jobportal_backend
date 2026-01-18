from datetime import datetime, timezone  # Import datetime class, not just module
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from app.models.job import Job, JobCreate, JobUpdate
from app.database.database import get_jobs_collection, get_applications_collection
from app.utils.auth import get_current_user
from bson import ObjectId
from typing import List

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

@router.post("/", response_model=Job)
async def create_job(
    job: JobCreate,
    token: str = Depends(oauth2_scheme)
):
    try:
        current_user = await get_current_user(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )
    
    # Only employers can create jobs
    if current_user.get("role") != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can create jobs"
        )
    
    # Get collections in the current request context
    jobs_collection = get_jobs_collection()
    
    # Create job - convert to dict and add server-side fields
    job_dict = job.model_dump()  # Updated for Pydantic v2
    job_dict["created_by"] = current_user["id"]
    job_dict["posted_date"] = datetime.now(timezone.utc)
    job_dict["updated_at"] = datetime.now(timezone.utc)
    job_dict["is_active"] = True
    job_dict["application_count"] = 0
    job_dict["view_count"] = 0
    
    # Set defaults for any missing optional fields
    if "salary_min" not in job_dict or job_dict["salary_min"] is None:
        job_dict["salary_min"] = None
    if "salary_max" not in job_dict or job_dict["salary_max"] is None:
        job_dict["salary_max"] = None
    if "experience_required" not in job_dict or job_dict["experience_required"] is None:
        job_dict["experience_required"] = None
    if "work_mode" not in job_dict or job_dict["work_mode"] is None:
        job_dict["work_mode"] = None
    if "company_logo_url" not in job_dict or job_dict["company_logo_url"] is None:
        job_dict["company_logo_url"] = None
    if "company_rating" not in job_dict or job_dict["company_rating"] is None:
        job_dict["company_rating"] = None
    if "reviews_count" not in job_dict or job_dict["reviews_count"] is None:
        job_dict["reviews_count"] = None
    if "skills" not in job_dict or job_dict["skills"] is None:
        job_dict["skills"] = []
    
    result = await jobs_collection.insert_one(job_dict)
    job_dict["id"] = str(result.inserted_id)
    
    # Create Job instance with all required fields
    return Job(
        id=job_dict["id"],
        title=job_dict["title"],
        description=job_dict["description"],
        company=job_dict["company"],
        salary_min=job_dict["salary_min"],
        salary_max=job_dict["salary_max"],
        location=job_dict["location"],
        skills=job_dict["skills"],
        experience_required=job_dict["experience_required"],
        work_mode=job_dict["work_mode"],
        company_logo_url=job_dict["company_logo_url"],
        company_rating=job_dict["company_rating"],
        reviews_count=job_dict["reviews_count"],
        posted_date=job_dict["posted_date"],
        is_active=job_dict["is_active"],
        application_count=job_dict["application_count"],
        view_count=job_dict["view_count"]
    )

@router.get("/", response_model=List[Job])
async def get_jobs(
    skip: int = 0,
    limit: int = 20,
    search: str = "",
    location: str = "",
    job_type: str = ""
):
    # Get collection in the current request context
    jobs_collection = get_jobs_collection()
    
    # Build query based on provided parameters
    query = {"is_active": True}  # Only active jobs
    
    # Apply filters based on parameters
    if search:
        # For search, we'll use $or with multiple fields
        search_conditions = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"skills": {"$in": [search]}}  # Search in skills array
        ]
        query["$or"] = search_conditions
    
    if location:
        query["location"] = {"$regex": location, "$options": "i"}
    
    if job_type:
        query["work_mode"] = job_type

    jobs = []
    async for job in jobs_collection.find(query).skip(skip).limit(limit).sort("posted_date", -1):
        job["id"] = str(job["_id"])
        del job["_id"]
        
        # Ensure boolean fields have correct types
        if "is_active" in job:
            if isinstance(job["is_active"], list):
                # Convert list to boolean - if list has items, set to True, otherwise False
                job["is_active"] = bool(job["is_active"])
            elif not isinstance(job["is_active"], bool):
                # Handle other non-boolean types
                job["is_active"] = bool(job["is_active"])
        
        jobs.append(Job(**job))
    
    return jobs

# New search endpoint to match frontend expectations
@router.get("/search", response_model=List[Job])
async def search_jobs(
    skip: int = 0,
    limit: int = 20,
    search: str = "",
    location: str = "",
    job_type: str = "",
    work_mode: str = "",
    salary_min: int = 0,
    experience_min: int = 0,
    experience_max: int = 100,
    skills: str = ""
):
    # Get collection in the current request context
    jobs_collection = get_jobs_collection()
    
    # Build query based on provided parameters
    query = {"is_active": True}  # Only active jobs
    
    # Apply filters based on parameters
    if search:
        # For search, we'll use $or with multiple fields
        search_conditions = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"skills": {"$in": [search]}}  # Search in skills array
        ]
        query["$or"] = search_conditions
    
    if location:
        query["location"] = {"$regex": location, "$options": "i"}
    
    if job_type:
        query["work_mode"] = job_type
    
    if work_mode:
        query["work_mode"] = work_mode
    
    if salary_min > 0:
        query["salary_min"] = {"$gte": salary_min}
    
    if experience_min > 0 or experience_max < 100:
        exp_query = {}
        if experience_min > 0:
            exp_query["$gte"] = experience_min
        if experience_max < 100:
            exp_query["$lte"] = experience_max
        if exp_query:
            query["experience_required"] = exp_query
    
    if skills:
        # Split skills by comma if multiple skills provided
        skills_list = [s.strip() for s in skills.split(",")]
        query["skills"] = {"$in": skills_list}

    jobs = []
    async for job in jobs_collection.find(query).skip(skip).limit(limit).sort("posted_date", -1):
        job["id"] = str(job["_id"])
        del job["_id"]
        
        # Ensure boolean fields have correct types
        if "is_active" in job:
            if isinstance(job["is_active"], list):
                # Convert list to boolean - if list has items, set to True, otherwise False
                job["is_active"] = bool(job["is_active"])
            elif not isinstance(job["is_active"], bool):
                # Handle other non-boolean types
                job["is_active"] = bool(job["is_active"])
        
        # Create a clean job object with all required fields
        job_data = {
            "id": job.get("id", ""),
            "title": job.get("title", ""),
            "description": job.get("description", ""),
            "company": job.get("company", ""),
            "salary_min": job.get("salary_min"),
            "salary_max": job.get("salary_max"),
            "location": job.get("location", ""),
            "skills": job.get("skills", []),
            "experience_required": job.get("experience_required"),
            "work_mode": job.get("work_mode"),
            "company_logo_url": job.get("company_logo_url", "" if "company_logo_url" in job else None),
            "company_rating": job.get("company_rating", 0.0 if "company_rating" in job else None),
            "reviews_count": job.get("reviews_count", 0 if "reviews_count" in job else None),
            "posted_date": job.get("posted_date", datetime.now(timezone.utc)),
            "is_active": job.get("is_active", True),
            "application_count": job.get("application_count", 0),
            "view_count": job.get("view_count", 0)
        }
        
        jobs.append(Job(**job_data))
    
    return jobs

@router.get("/my", response_model=List[Job])
async def get_my_jobs(
    token: str = Depends(oauth2_scheme)
):
    current_user = await get_current_user(token)
    
    # Get collection in the current request context
    jobs_collection = get_jobs_collection()
    
    jobs = []
    async for job in jobs_collection.find({"created_by": current_user["id"]}).sort("posted_date", -1):
        job["id"] = str(job["_id"])
        del job["_id"]
        
        # Ensure boolean fields have correct types
        if "is_active" in job:
            if isinstance(job["is_active"], list):
                # Convert list to boolean - if list has items, set to True, otherwise False
                job["is_active"] = bool(job["is_active"])
            elif not isinstance(job["is_active"], bool):
                # Handle other non-boolean types
                job["is_active"] = bool(job["is_active"])
        
        # Create a clean job object with all required fields
        job_data = {
            "id": job.get("id", ""),
            "title": job.get("title", ""),
            "description": job.get("description", ""),
            "company": job.get("company", ""),
            "salary_min": job.get("salary_min"),
            "salary_max": job.get("salary_max"),
            "location": job.get("location", ""),
            "skills": job.get("skills", []),
            "experience_required": job.get("experience_required"),
            "work_mode": job.get("work_mode"),
            "company_logo_url": job.get("company_logo_url", "" if "company_logo_url" in job else None),
            "company_rating": job.get("company_rating", 0.0 if "company_rating" in job else None),
            "reviews_count": job.get("reviews_count", 0 if "reviews_count" in job else None),
            "posted_date": job.get("posted_date", datetime.now(timezone.utc)),
            "is_active": job.get("is_active", True),
            "application_count": job.get("application_count", 0),
            "view_count": job.get("view_count", 0)
        }
        
        jobs.append(Job(**job_data))
    
    return jobs

@router.get("/{job_id}", response_model=Job)
async def get_job(job_id: str):
    # Get collection in the current request context
    jobs_collection = get_jobs_collection()
    
    # First, try to find by ObjectId (primary method)
    if ObjectId.is_valid(job_id):
        try:
            job = await jobs_collection.find_one({"_id": ObjectId(job_id), "is_active": True})
            if job:
                # Process the job with proper type conversions
                posted_date_raw = job.get("posted_date", datetime.now(timezone.utc))
                
                # Handle posted_date with proper type conversion
                if isinstance(posted_date_raw, str):
                    try:
                        # Handle ISO format date strings
                        processed_posted_date = datetime.fromisoformat(posted_date_raw.replace('Z', '+00:00'))
                    except ValueError:
                        # Fallback to current time
                        processed_posted_date = datetime.now(timezone.utc)
                elif isinstance(posted_date_raw, datetime):
                    processed_posted_date = posted_date_raw
                else:
                    # If it's neither string nor datetime, use current time
                    processed_posted_date = datetime.now(timezone.utc)
                
                # Create a clean dict with only the fields expected by the Job model
                job_data = {
                    "id": str(job["_id"]),
                    "title": job.get("title", ""),
                    "description": job.get("description", ""),
                    "company": job.get("company", ""),
                    "salary_min": job.get("salary_min"),
                    "salary_max": job.get("salary_max"),
                    "location": job.get("location", ""),
                    "skills": job.get("skills", []),
                    "experience_required": job.get("experience_required"),
                    "work_mode": job.get("work_mode"),
                    "company_logo_url": job.get("company_logo_url"),
                    "company_rating": job.get("company_rating"),
                    "reviews_count": job.get("reviews_count"),
                    "posted_date": processed_posted_date,
                    "is_active": bool(job.get("is_active", True)),
                    "application_count": int(job.get("application_count", 0)),
                    "view_count": int(job.get("view_count", 0))
                }
                
                return Job(**job_data)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid job ID"
            )
    
    # If ObjectId search didn't find anything, check for potential legacy numeric IDs
    # This is for backward compatibility if the system stores numeric IDs in a different way
    # But for now, just return 404 if the ObjectId search fails
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Job not found"
    )

@router.put("/{job_id}", response_model=Job)
async def update_job(
    job_id: str,
    job_update: JobUpdate,
    token: str = Depends(oauth2_scheme)
):
    current_user = await get_current_user(token)
    
    # Get collection in the current request context
    jobs_collection = get_jobs_collection()
    
    try:
        # Find the job first
        job = await jobs_collection.find_one({"_id": ObjectId(job_id)})
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Check if user is authorized to update (owner or admin)
        if job["created_by"] != current_user["id"] and current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this job"
            )
        
        # Prepare update data
        update_data = job_update.model_dump(exclude_unset=True)  # Updated for Pydantic v2
        update_data["updated_at"] = datetime.now(timezone.utc)
        
        # Update the job
        result = await jobs_collection.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No changes made to job"
            )
        
        # Return updated job
        updated_job = await jobs_collection.find_one({"_id": ObjectId(job_id)})
        if updated_job:
            updated_job["id"] = str(updated_job["_id"])
            del updated_job["_id"]
            
            # Ensure boolean fields have correct types
            if "is_active" in updated_job:
                if isinstance(updated_job["is_active"], list):
                    # Convert list to boolean - if list has items, set to True, otherwise False
                    updated_job["is_active"] = bool(updated_job["is_active"])
                elif not isinstance(updated_job["is_active"], bool):
                    # Handle other non-boolean types
                    updated_job["is_active"] = bool(updated_job["is_active"])
            
            return Job(**updated_job)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID"
        )

@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    token: str = Depends(oauth2_scheme)
):
    current_user = await get_current_user(token)
    
    # Get collection in the current request context
    jobs_collection = get_jobs_collection()
    
    try:
        # Find the job first
        job = await jobs_collection.find_one({"_id": ObjectId(job_id)})
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Check if user is authorized to delete (owner or admin)
        if job["created_by"] != current_user["id"] and current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this job"
            )
        
        # Delete the job
        result = await jobs_collection.delete_one({"_id": ObjectId(job_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        return {"message": "Job deleted successfully"}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID"
        )
