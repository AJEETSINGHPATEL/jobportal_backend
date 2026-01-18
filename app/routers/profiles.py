from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from app.models.job_seeker_profile import JobSeekerProfileCreate, JobSeekerProfileUpdate, JobSeekerProfile
from app.models.recruiter_profile import RecruiterProfileCreate, RecruiterProfileUpdate, RecruiterProfile
from app.database.database import get_job_seeker_profiles_collection, get_recruiter_profiles_collection, get_users_collection
from app.utils.auth import get_current_user
from bson import ObjectId
from typing import List, Optional

router = APIRouter(prefix="/api/profiles", tags=["Profiles"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

@router.post("/job-seeker", response_model=JobSeekerProfile)
async def create_job_seeker_profile(profile: JobSeekerProfileCreate, token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists and is a job seeker
        user = await get_current_user(token)
        if user["role"] != "job_seeker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only job seekers can create job seeker profiles"
            )
        
        # Check if profile already exists
        job_seeker_profiles_collection = get_job_seeker_profiles_collection()
        existing_profile = await job_seeker_profiles_collection.find_one({"user_id": user["id"]})
        if existing_profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job seeker profile already exists"
            )
        
        # Create profile
        profile_dict = profile.model_dump()  # Updated for Pydantic v2
        profile_dict["user_id"] = user["id"]
        result = await job_seeker_profiles_collection.insert_one(profile_dict)
        profile_dict["id"] = str(result.inserted_id)
        
        return JobSeekerProfile(**profile_dict)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating job seeker profile: {str(e)}"
        )

@router.put("/job-seeker", response_model=JobSeekerProfile)
async def update_job_seeker_profile(profile: JobSeekerProfileUpdate, token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists and is a job seeker
        user = await get_current_user(token)
        if user["role"] != "job_seeker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only job seekers can update job seeker profiles"
            )
        
        # Find existing profile
        job_seeker_profiles_collection = get_job_seeker_profiles_collection()
        existing_profile = await job_seeker_profiles_collection.find_one({"user_id": user["id"]})
        if not existing_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job seeker profile not found"
            )
        
        # Update profile
        profile_dict = profile.model_dump(exclude_unset=True)  # Updated for Pydantic v2
        await job_seeker_profiles_collection.update_one(
            {"user_id": user["id"]},
            {"$set": profile_dict}
        )
        
        # Return updated profile
        updated_profile = await job_seeker_profiles_collection.find_one({"user_id": user["id"]})
        if not updated_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job seeker profile not found after update"
            )
        updated_profile["id"] = str(updated_profile["_id"])
        return JobSeekerProfile(**updated_profile)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating job seeker profile: {str(e)}"
        )

@router.get("/job-seeker/me", response_model=JobSeekerProfile)
async def get_my_job_seeker_profile(token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists and is a job seeker
        user = await get_current_user(token)
        if user["role"] != "job_seeker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only job seekers can access job seeker profiles"
            )
        
        # Find profile
        job_seeker_profiles_collection = get_job_seeker_profiles_collection()
        profile = await job_seeker_profiles_collection.find_one({"user_id": user["id"]})
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job seeker profile not found"
            )
        
        profile["id"] = str(profile["_id"])
        return JobSeekerProfile(**profile)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching job seeker profile: {str(e)}"
        )

@router.post("/recruiter", response_model=RecruiterProfile)
async def create_recruiter_profile(profile: RecruiterProfileCreate, token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists and is an employer
        user = await get_current_user(token)
        if user["role"] != "employer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only employers can create recruiter profiles"
            )
        
        # Check if profile already exists
        recruiter_profiles_collection = get_recruiter_profiles_collection()
        existing_profile = await recruiter_profiles_collection.find_one({"user_id": user["id"]})
        if existing_profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recruiter profile already exists"
            )
        
        # Create profile
        profile_dict = profile.model_dump()  # Updated for Pydantic v2
        profile_dict["user_id"] = user["id"]
        result = await recruiter_profiles_collection.insert_one(profile_dict)
        profile_dict["id"] = str(result.inserted_id)
        
        return RecruiterProfile(**profile_dict)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating recruiter profile: {str(e)}"
        )

@router.put("/recruiter", response_model=RecruiterProfile)
async def update_recruiter_profile(profile: RecruiterProfileUpdate, token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists and is an employer
        user = await get_current_user(token)
        if user["role"] != "employer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only employers can update recruiter profiles"
            )
        
        # Find existing profile
        recruiter_profiles_collection = get_recruiter_profiles_collection()
        existing_profile = await recruiter_profiles_collection.find_one({"user_id": user["id"]})
        if not existing_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter profile not found"
            )
        
        # Update profile
        profile_dict = profile.model_dump(exclude_unset=True)  # Updated for Pydantic v2
        await recruiter_profiles_collection.update_one(
            {"user_id": user["id"]},
            {"$set": profile_dict}
        )
        
        # Return updated profile
        updated_profile = await recruiter_profiles_collection.find_one({"user_id": user["id"]})
        if not updated_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter profile not found after update"
            )
        updated_profile["id"] = str(updated_profile["_id"])
        return RecruiterProfile(**updated_profile)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating recruiter profile: {str(e)}"
        )

@router.get("/recruiter/me", response_model=RecruiterProfile)
async def get_my_recruiter_profile(token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists and is an employer
        user = await get_current_user(token)
        if user["role"] != "employer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only employers can access recruiter profiles"
            )
        
        # Find profile
        recruiter_profiles_collection = get_recruiter_profiles_collection()
        profile = await recruiter_profiles_collection.find_one({"user_id": user["id"]})
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter profile not found"
            )
        
        profile["id"] = str(profile["_id"])
        return RecruiterProfile(**profile)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching recruiter profile: {str(e)}"
        )

@router.get("/candidates", response_model=List[dict])
async def search_candidates(skills: Optional[str] = None, experience: Optional[int] = None, location: Optional[str] = None, token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists and is an employer
        user = await get_current_user(token)
        if user["role"] != "employer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only employers can search candidates"
            )
        
        # Build search query
        query = {"role": "job_seeker"}
        
        # Get collections in the current request context
        job_seeker_profiles_collection = get_job_seeker_profiles_collection()
        users_collection = get_users_collection()
        
        # Search in job seeker profiles collection
        profiles_cursor = job_seeker_profiles_collection.find(query)
        candidates = []
        
        async for profile in profiles_cursor:
            # Get user details
            user_details = await users_collection.find_one({"_id": ObjectId(profile["user_id"])})
            if user_details:
                candidate = {
                    "id": str(profile["_id"]),
                    "user_id": profile["user_id"],
                    "full_name": user_details.get("full_name", ""),
                    "email": user_details.get("email", ""),
                    "phone": profile.get("phone", ""),
                    "skills": profile.get("skills", []),
                    "experience_years": profile.get("experience_years", 0),
                    "preferred_locations": profile.get("preferred_locations", []),
                    "resume_url": profile.get("resume_url", ""),
                    "profile_completion_pct": profile.get("profile_completion_pct", 0)
                }
                candidates.append(candidate)
        
        return candidates
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching candidates: {str(e)}"
        )