from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.database.database import get_db
from app.database.models import User as UserModel, Job as JobModel, Company as CompanyModel
from app.utils.auth import get_current_user
from app.models.user import UserRole
import uuid

router = APIRouter(prefix="/api/admin", tags=["Admin"])

async def require_admin(current_user: dict = Depends(get_current_user)):
    """Dependency to ensure user has admin role"""
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can access this resource"
        )
    return current_user

@router.get("/users")
async def get_all_users(db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin)):
    """Get all users in the system"""
    try:
        stmt = select(UserModel)
        result = await db.execute(stmt)
        users = result.scalars().all()
        return {"users": users, "total": len(users)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching users: {str(e)}"
        )

@router.get("/users/{user_id}")
async def get_user_by_id(user_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin)):
    """Get a specific user by ID"""
    try:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user: {str(e)}"
        )

@router.put("/users/{user_id}/status")
async def update_user_status(user_id: str, is_active: bool = True, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin)):
    """Activate or deactivate a user account"""
    try:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.is_active = is_active
        await db.commit()
        return {"message": f"User status updated successfully", "is_active": is_active}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user status: {str(e)}"
        )

@router.delete("/users/{user_id}")
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin)):
    """Delete a user account"""
    try:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        await db.delete(user)
        await db.commit()
        return {"message": "User deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )

@router.get("/jobs")
async def get_all_jobs(db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin)):
    """Get all jobs in the system"""
    try:
        stmt = select(JobModel)
        result = await db.execute(stmt)
        jobs = result.scalars().all()
        return {"jobs": jobs, "total": len(jobs)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching jobs: {str(e)}"
        )

@router.get("/companies")
async def get_all_companies(db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin)):
    """Get all companies in the system"""
    try:
        stmt = select(CompanyModel)
        result = await db.execute(stmt)
        companies = result.scalars().all()
        return {"companies": companies, "total": len(companies)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching companies: {str(e)}"
        )

@router.put("/jobs/{job_id}/status")
async def update_job_status(job_id: str, is_active: bool, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin)):
    """Activate or deactivate a job listing"""
    try:
        stmt = select(JobModel).where(JobModel.id == job_id)
        result = await db.execute(stmt)
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        job.is_active = is_active
        await db.commit()
        return {"message": f"Job status updated successfully", "is_active": is_active}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating job status: {str(e)}"
        )
