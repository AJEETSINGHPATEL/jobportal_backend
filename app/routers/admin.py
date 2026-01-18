from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from bson import ObjectId
from typing import List, Optional
import datetime
from app.models.user import User, UserRole
from app.database.database import get_users_collection, get_jobs_collection, get_companies_collection
from app.utils.auth import get_current_user, get_current_user_role

router = APIRouter(prefix="/api/admin", tags=["Admin"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def require_admin(token: str = Depends(oauth2_scheme)):
    """Dependency to ensure user has admin role"""
    current_user = await get_current_user(token)
    user_role = await get_current_user_role(current_user["id"])
    if user_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can access this resource"
        )
    return current_user

@router.get("/users")
async def get_all_users(current_user: dict = Depends(require_admin)):
    """Get all users in the system"""
    users_collection = get_users_collection()
    
    try:
        users = []
        async for user in users_collection.find():
            user["id"] = str(user["_id"])
            del user["_id"]
            users.append(user)
        
        return {"users": users, "total": len(users)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching users: {str(e)}"
        )

@router.get("/users/{user_id}")
async def get_user_by_id(user_id: str, current_user: dict = Depends(require_admin)):
    """Get a specific user by ID"""
    users_collection = get_users_collection()
    
    try:
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user["id"] = str(user["_id"])
        del user["_id"]
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user: {str(e)}"
        )

@router.put("/users/{user_id}/status")
async def update_user_status(user_id: str, is_active: bool = True, current_user: dict = Depends(require_admin)):
    """Activate or deactivate a user account"""
    users_collection = get_users_collection()
    
    try:
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        result = await users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_active": is_active}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update user status"
            )
        
        return {"message": f"User status updated successfully", "is_active": is_active}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user status: {str(e)}"
        )

@router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(require_admin)):
    """Delete a user account"""
    users_collection = get_users_collection()
    
    try:
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        result = await users_collection.delete_one({"_id": ObjectId(user_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete user"
            )
        
        return {"message": "User deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )

@router.get("/jobs")
async def get_all_jobs(current_user: dict = Depends(require_admin)):
    """Get all jobs in the system"""
    jobs_collection = get_jobs_collection()
    
    try:
        jobs = []
        async for job in jobs_collection.find():
            job["id"] = str(job["_id"])
            del job["_id"]
            jobs.append(job)
        
        return {"jobs": jobs, "total": len(jobs)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching jobs: {str(e)}"
        )

@router.get("/companies")
async def get_all_companies(current_user: dict = Depends(require_admin)):
    """Get all companies in the system"""
    companies_collection = get_companies_collection()
    
    try:
        companies = []
        async for company in companies_collection.find():
            company["id"] = str(company["_id"])
            del company["_id"]
            companies.append(company)
        
        return {"companies": companies, "total": len(companies)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching companies: {str(e)}"
        )

@router.put("/jobs/{job_id}/status")
async def update_job_status(job_id: str, is_active: bool, current_user: dict = Depends(require_admin)):
    """Activate or deactivate a job listing"""
    jobs_collection = get_jobs_collection()
    
    try:
        job = await jobs_collection.find_one({"_id": ObjectId(job_id)})
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        result = await jobs_collection.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": {"is_active": is_active}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update job status"
            )
        
        return {"message": f"Job status updated successfully", "is_active": is_active}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating job status: {str(e)}"
        )