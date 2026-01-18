from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from app.models.application import ApplicationCreate, ApplicationUpdate, Application
from app.database.database import get_applications_collection, get_jobs_collection, get_users_collection
from app.utils.auth import get_current_user
from bson import ObjectId
from typing import List
from datetime import datetime
import traceback

router = APIRouter(prefix="/api/applications", tags=["Applications"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

@router.post("/", response_model=Application)
async def create_application(
    application: ApplicationCreate,
    token: str = Depends(oauth2_scheme)
):
    try:
        print(f"Received application data: {application}")
        print(f"Application type: {type(application)}")
        print(f"Application job_id: {getattr(application, 'job_id', 'MISSING')}")
        print(f"Application cover_letter: {getattr(application, 'cover_letter', 'MISSING')}")
        print(f"Application status: {getattr(application, 'status', 'MISSING')}")
        print(f"Application resume_url: {getattr(application, 'resume_url', 'MISSING')}")
        
        current_user = await get_current_user(token)
        print(f"Current user: {current_user['id']}")
        
        # Get collections in the current request context
        applications_collection = get_applications_collection()
        jobs_collection = get_jobs_collection()
        users_collection = get_users_collection()
        
        # Validate job_id format first
        if not ObjectId.is_valid(application.job_id):
            print(f"Invalid job ID format: {application.job_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid job ID format: {application.job_id}"
            )
            
        # Verify job exists
        job_object_id = ObjectId(application.job_id)
        job = await jobs_collection.find_one({"_id": job_object_id})
        if not job:
            print(f"Job not found with ID: {application.job_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job not found with ID: {application.job_id}"
            )
        else:
            print(f"Job found: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
        
        # Verify user exists
        user_object_id = ObjectId(current_user["id"])
        user = await users_collection.find_one({"_id": user_object_id})
        if not user:
            print(f"User not found with ID: {current_user['id']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found with ID: {current_user['id']}"
            )
        else:
            print(f"User found: {user.get('email', 'Unknown')}")
        
        # Check if application already exists for this user and job
        print(f"Checking for existing application - user_id: {current_user['id']}, job_id: {application.job_id}")
        existing_application = await applications_collection.find_one({
            "user_id": current_user["id"],
            "job_id": application.job_id
        })
        if existing_application:
            print(f"Duplicate application found for user {current_user['id']} and job {application.job_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Application already submitted for this job"
            )
        else:
            print(f"No existing application found, proceeding with creation")
        
        # Create application
        application_dict = application.model_dump()  # Updated for Pydantic v2
        application_dict["user_id"] = current_user["id"]
        
        # Make sure status is stored as a string value
        if hasattr(application, 'status') and application.status:
            if hasattr(application.status, 'value'):
                application_dict["status"] = application.status.value
            else:
                application_dict["status"] = str(application.status)
        
        # Ensure resume_url is properly stored
        if hasattr(application, 'resume_url') and application.resume_url:
            application_dict["resume_url"] = application.resume_url
        else:
            application_dict["resume_url"] = None
        
        application_dict["applied_date"] = datetime.utcnow()
        application_dict["updated_date"] = datetime.utcnow()
        application_dict["created_at"] = datetime.utcnow()  # Add required field
        application_dict["updated_at"] = datetime.utcnow()  # Add required field
        
        print(f"About to insert application: {application_dict}")
        result = await applications_collection.insert_one(application_dict)
        print(f"Insert successful, result ID: {result.inserted_id}")
        
        application_dict["id"] = str(result.inserted_id)
        
        # Remove the original _id field to avoid confusion
        if "_id" in application_dict:
            del application_dict["_id"]
        
        print(f"Successfully created application with ID: {application_dict['id']}")
        print(f"Returning application object: {Application(**application_dict)}")
        return Application(**application_dict)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in create_application: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/", response_model=List[Application])
async def get_user_applications(
    token: str = Depends(oauth2_scheme),
    skip: int = 0,
    limit: int = 10
):
    current_user = await get_current_user(token)
    
    # Get collections in the current request context
    applications_collection = get_applications_collection()
    jobs_collection = get_jobs_collection()
    
    applications = []
    async for application in applications_collection.find(
        {"user_id": current_user["id"]}
    ).skip(skip).limit(limit):
        application["id"] = str(application["_id"])
        del application["_id"]
        
        # Get job details to include in response
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
        
        applications.append(Application(**application))
    
    return applications

@router.get("/job/{job_id}", response_model=List[Application])
async def get_job_applications(
    job_id: str,
    token: str = Depends(oauth2_scheme)
):
    current_user = await get_current_user(token)
    
    # Validate job_id format first
    if not ObjectId.is_valid(job_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format"
        )
    
    # Get collections in the current request context
    applications_collection = get_applications_collection()
    users_collection = get_users_collection()
    jobs_collection = get_jobs_collection()
    
    # Verify job exists and belongs to current user (if employer)
    job = await jobs_collection.find_one({"_id": ObjectId(job_id)})
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Check if current user is the job creator or an admin
    if job.get("created_by") != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view applications for this job"
        )
    
    applications = []
    async for application in applications_collection.find({"job_id": job_id}):
        application["id"] = str(application["_id"])
        del application["_id"]
        
        # Get user details to include in response
        user = await users_collection.find_one({"_id": ObjectId(application["user_id"])})
        if user:
            application["applicant_name"] = user.get("full_name", "")
            application["applicant_email"] = user.get("email", "")
        else:
            application["applicant_name"] = "Unknown"
            application["applicant_email"] = "Unknown"
        
        applications.append(Application(**application))
    
    return applications

@router.get("/{application_id}", response_model=Application)
async def get_application(
    application_id: str,
    token: str = Depends(oauth2_scheme)
):
    current_user = await get_current_user(token)
    
    # Get collections in the current request context
    applications_collection = get_applications_collection()
    jobs_collection = get_jobs_collection()
    
    try:
        # Validate ObjectId format first
        if not ObjectId.is_valid(application_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid application ID format"
            )
        
        # First, try to find the application for the current user (job seeker)
        application = await applications_collection.find_one({
            "_id": ObjectId(application_id),
            "user_id": current_user["id"]
        })
        
        # If not found, check if current user is the employer who posted the job
        if not application:
            application = await applications_collection.find_one({"_id": ObjectId(application_id)})
            if application and application.get("job_id"):
                job = await jobs_collection.find_one({"_id": ObjectId(application["job_id"])})
                if job and job.get("created_by") == current_user["id"]:
                    # Employer is viewing application for their job
                    pass
                else:
                    # Neither job seeker nor employer of this job
                    application = None
            else:
                application = None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid application ID"
        )
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or not authorized to view"
        )
    
    application["id"] = str(application["_id"])
    del application["_id"]
    
    # Get job details to include in response
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
    
    return Application(**application)

@router.put("/{application_id}", response_model=Application)
async def update_application(
    application_id: str,
    application_update: ApplicationUpdate,
    token: str = Depends(oauth2_scheme)
):
    current_user = await get_current_user(token)
    
    # Get collection in the current request context
    applications_collection = get_applications_collection()
    
    try:
        # Validate application_id format first
        if not ObjectId.is_valid(application_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid application ID format"
            )
        
        update_data = application_update.model_dump(exclude_unset=True)  # Updated for Pydantic v2
        # Convert enum to string if present
        if "status" in update_data and update_data["status"] is not None:
            update_data["status"] = update_data["status"].value
        update_data["updated_date"] = datetime.utcnow()
        
        result = await applications_collection.update_one(
            {
                "_id": ObjectId(application_id),
                "user_id": current_user["id"]
            },
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        updated_application = await applications_collection.find_one({
            "_id": ObjectId(application_id)
        })
        
        if updated_application:
            updated_application["id"] = str(updated_application["_id"])
            del updated_application["_id"]
            return Application(**updated_application)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid application ID"
        )

@router.delete("/{application_id}")
async def delete_application(
    application_id: str,
    token: str = Depends(oauth2_scheme)
):
    current_user = await get_current_user(token)
    
    # Get collection in the current request context
    applications_collection = get_applications_collection()
    
    try:
        # Validate application_id format first
        if not ObjectId.is_valid(application_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid application ID format"
            )
        
        # Check if the current user is the owner of the application
        application = await applications_collection.find_one({
            "_id": ObjectId(application_id)
        })
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        # Only the application owner or admin can delete the application
        if application["user_id"] != current_user["id"] and current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this application"
            )
        
        result = await applications_collection.delete_one({
            "_id": ObjectId(application_id)
        })
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        return {"message": "Application deleted successfully"}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid application ID"
        )