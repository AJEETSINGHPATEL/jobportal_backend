from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer
from app.models.profile import ProfileCreate, ProfileUpdate, ProfileInDB
from app.database.database import get_profiles_collection, get_users_collection
from app.utils.auth import get_current_user
from bson import ObjectId
from typing import List, Optional
import datetime
import os
from pathlib import Path

router = APIRouter(prefix="/api/profile", tags=["Profile"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def calculate_profile_completion(profile_data: dict) -> int:
    """Calculate profile completion percentage based on required and optional fields"""
    total_points = 0
    earned_points = 0
    
    # Required fields (higher weight)
    required_fields = ['fullName', 'email']
    for field in required_fields:
        if profile_data.get(field) and str(profile_data.get(field)).strip():
            earned_points += 2  # Weighted more heavily
        total_points += 2
    
    # Optional fields (standard weight)
    optional_fields = ['phone', 'address', 'headline', 'summary', 'profilePicture']
    for field in optional_fields:
        if profile_data.get(field) and str(profile_data.get(field)).strip():
            earned_points += 1
        total_points += 1
    
    # Experience section (can have multiple entries)
    experience = profile_data.get('experience', [])
    if experience:
        # Count each experience entry with at least title and company as 2 points
        for exp in experience:
            if exp.get('title') and exp.get('company'):
                earned_points += 2
            total_points += 2  # Max possible for experience section
    
    # Education section (can have multiple entries)
    education = profile_data.get('education', [])
    if education:
        # Count each education entry with at least school and degree as 2 points
        for edu in education:
            if edu.get('school') and edu.get('degree'):
                earned_points += 2
            total_points += 2  # Max possible for education section
    
    # Skills section
    skills = profile_data.get('skills', [])
    if skills:
        # Count each skill as 0.5 points, max 10 points for skills
        skill_points = min(len(skills) * 0.5, 10)
        earned_points += skill_points
        total_points += 10  # Max possible for skills section

    # Projects section
    projects = profile_data.get('projects', [])
    if projects:
        # Count each project as 2 points
        for proj in projects:
            if proj.get('title') and proj.get('description'):
                earned_points += 2
            total_points += 2
    else:
        # Assume 2 projects for total points calculation if none exist yet
        total_points += 4
    
    if total_points == 0:
        return 0
    
    completion_percentage = int((earned_points / total_points) * 100)
    return min(completion_percentage, 100)  # Cap at 100%

@router.post("/", response_model=ProfileInDB)
async def create_profile(profile: ProfileCreate, token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists
        user = await get_current_user(token)
        
        # Get profiles collection
        profiles_collection = get_profiles_collection()
        
        # Check if profile already exists for this user
        existing_profile = await profiles_collection.find_one({"user_id": profile.user_id})
        if existing_profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profile already exists for this user"
            )
        
        # Verify that the authenticated user is creating a profile for themselves
        if user["id"] != profile.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create profile for another user"
            )
        
        # Calculate profile completion
        profile_dict = profile.model_dump()
        profile_completion = calculate_profile_completion(profile_dict)
        profile_dict["profile_completion"] = profile_completion
        
        profile_dict["user_id"] = profile.user_id
        profile_dict["created_at"] = datetime.datetime.now(datetime.timezone.utc)
        profile_dict["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
        
        result = await profiles_collection.insert_one(profile_dict)
        profile_dict["id"] = str(result.inserted_id)
        
        # Remove the _id from the dict since we added it as "id"
        if "_id" in profile_dict:
            del profile_dict["_id"]
        
        return ProfileInDB(**profile_dict)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating profile: {str(e)}"
        )

@router.put("/{profile_id}", response_model=ProfileInDB)
async def update_profile(profile_id: str, profile: ProfileUpdate, token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists
        user = await get_current_user(token)
        
        # Get profiles collection
        profiles_collection = get_profiles_collection()
        
        # Find existing profile
        existing_profile = await profiles_collection.find_one({"_id": ObjectId(profile_id)})
        if not existing_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )
        
        # Check if user owns this profile
        if existing_profile["user_id"] != user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this profile"
            )
        
        # Calculate profile completion
        profile_dict = profile.model_dump(exclude_unset=True)
        profile_completion = calculate_profile_completion(profile_dict)
        profile_dict["profile_completion"] = profile_completion
        profile_dict["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
        
        await profiles_collection.update_one(
            {"_id": ObjectId(profile_id)},
            {"$set": profile_dict}
        )
        
        # Return updated profile
        updated_profile = await profiles_collection.find_one({"_id": ObjectId(profile_id)})
        if not updated_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found after update"
            )
        updated_profile["id"] = str(updated_profile["_id"])
        
        # Remove the _id from the dict since we added it as "id"
        if "_id" in updated_profile:
            del updated_profile["_id"]
        
        return ProfileInDB(**updated_profile)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating profile: {str(e)}"
        )

@router.get("/user/{user_id}", response_model=ProfileInDB)
async def get_user_profile(user_id: str, token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists
        user = await get_current_user(token)
        
        # Get profiles collection
        profiles_collection = get_profiles_collection()
        
        # For security, only allow users to access their own profile
        # Check if the user_id in the URL matches the authenticated user
        authenticated_user_id = user["id"]
        
        # Compare user IDs - they should be equal as both are converted to string representations of ObjectId
        if authenticated_user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to access this profile. Expected {authenticated_user_id}, got {user_id}"
            )
        
        # Find profile
        profile = await profiles_collection.find_one({"user_id": user_id})
        if not profile:
            # Return an empty profile if none exists
            empty_profile = {
                "id": None,
                "user_id": user_id,
                "fullName": user.get("full_name", ""),
                "email": user.get("email", ""),
                "phone": "",
                "address": "",
                "headline": "",
                "summary": "",
                "profilePicture": user.get("profilePicture", ""),
                "experience": [],
                "education": [],
                "skills": [],
                "projects": [],
                "profile_completion": 0,
                "profile_views": 0,
                "created_at": datetime.datetime.now(datetime.timezone.utc),
                "updated_at": datetime.datetime.now(datetime.timezone.utc)
            }
            return ProfileInDB(**empty_profile)
        
        profile["id"] = str(profile["_id"])
        
        # Remove the _id from the dict since we added it as "id"
        if "_id" in profile:
            del profile["_id"]
        
        return ProfileInDB(**profile)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching profile: {str(e)}"
        )

# New endpoint to update profile by user_id (useful for frontend)
@router.put("/user/{user_id}", response_model=ProfileInDB)
async def update_user_profile(user_id: str, profile: ProfileUpdate, token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists
        user = await get_current_user(token)
        
        # Check if the requesting user is the same as the profile user
        authenticated_user_id = user["id"]
        if authenticated_user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to update this profile. Expected {authenticated_user_id}, got {user_id}"
            )
        
        # Get profiles collection
        profiles_collection = get_profiles_collection()
        
        # Find existing profile
        existing_profile = await profiles_collection.find_one({"user_id": user_id})
        if not existing_profile:
            # If profile doesn't exist, create one
            profile_dict = profile.model_dump(exclude_unset=True)
            profile_completion = calculate_profile_completion(profile_dict)
            profile_dict["profile_completion"] = profile_completion
            profile_dict["user_id"] = user_id
            profile_dict["created_at"] = datetime.datetime.now(datetime.timezone.utc)
            profile_dict["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
            
            result = await profiles_collection.insert_one(profile_dict)
            profile_dict["id"] = str(result.inserted_id)
            
            if "_id" in profile_dict:
                del profile_dict["_id"]
            
            return ProfileInDB(**profile_dict)
        
        # If profile exists, update it
        profile_dict = profile.model_dump(exclude_unset=True)
        # Merge with existing profile data to get full data for calculation
        merged_profile = {**existing_profile, **profile_dict}
        profile_completion = calculate_profile_completion(merged_profile)
        profile_dict["profile_completion"] = profile_completion
        profile_dict["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
        
        await profiles_collection.update_one(
            {"user_id": user_id},
            {"$set": profile_dict}
        )
        
        # Return updated profile
        updated_profile = await profiles_collection.find_one({"user_id": user_id})
        if not updated_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found after update"
            )
        updated_profile["id"] = str(updated_profile["_id"])
        
        # Remove the _id from the dict since we added it as "id"
        if "_id" in updated_profile:
            del updated_profile["_id"]
        
        return ProfileInDB(**updated_profile)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating profile: {str(e)}"
        )

# Endpoint to upload profile picture
@router.post("/upload-picture")
async def upload_profile_picture(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists
        user = await get_current_user(token)
        user_id = user["id"]
        
        # Validate file type
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/gif"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only JPEG, PNG, and GIF images are allowed."
            )
        
        # Create uploads directory if it doesn't exist
        upload_dir = Path("uploads/profile_pictures")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{user_id}.{file_extension}"
        file_path = upload_dir / unique_filename
        
        # Save file
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Get profiles collection
        profiles_collection = get_profiles_collection()
        
        # Update user's profile with the picture URL
        profile_picture_url = f"/uploads/profile_pictures/{unique_filename}"
        await profiles_collection.update_one(
            {"user_id": user_id},
            {"$set": {"profilePicture": profile_picture_url, "updated_at": datetime.datetime.now(datetime.timezone.utc)}}
        )
        
        # Also update the user's profile completion
        existing_profile = await profiles_collection.find_one({"user_id": user_id})
        if existing_profile:
            profile_completion = calculate_profile_completion(existing_profile)
            await profiles_collection.update_one(
                {"user_id": user_id},
                {"$set": {"profile_completion": profile_completion}}
            )
        
        return {"filename": unique_filename, "url": profile_picture_url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading profile picture: {str(e)}"
        )

# Endpoint to increment profile view count
@router.post("/user/{user_id}/view")
async def increment_profile_view(user_id: str, token: str = Depends(oauth2_scheme)):
    try:
        # Verify user exists (recruiter viewing the profile)
        viewer = await get_current_user(token)
        
        # Get profiles collection
        profiles_collection = get_profiles_collection()
        
        # Find existing profile
        existing_profile = await profiles_collection.find_one({"user_id": user_id})
        
        if not existing_profile:
            # If profile doesn't exist yet, we can't increment view on it, but we shouldn't error out generally
            # just return success with no action or create empty profile?
            # Better to return 404 if profile strictly required, but for "views" it might be soft.
            # Let's return 404 to be specific.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )
            
        # Increment view count
        # Ensure profile_views exists, if not set to 1
        new_views = existing_profile.get("profile_views", 0) + 1
        
        await profiles_collection.update_one(
            {"user_id": user_id},
            {"$set": {"profile_views": new_views}}
        )
        
        return {"message": "View count incremented", "views": new_views}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error incrementing view count: {str(e)}"
        )