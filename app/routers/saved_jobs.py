from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
from app.models.saved_job import SavedJobCreate, SavedJob as SavedJobSchema
from app.database.database import get_db
from app.database.models import SavedJob as SavedJobModel, Job as JobModel
from app.utils.auth import get_current_user
from typing import List
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/saved-jobs", tags=["Saved Jobs"])

@router.post("/", response_model=SavedJobSchema)
async def save_job(job: SavedJobCreate, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        user = current_user
        if user["role"] != "job_seeker":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only job seekers can save jobs")
        
        # Check if job exists
        job_stmt = select(JobModel).where(JobModel.id == job.job_id)
        job_result = await db.execute(job_stmt)
        if not job_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
            
        # Check if job is already saved
        exist_stmt = select(SavedJobModel).where(
            and_(
                SavedJobModel.user_id == user["id"],
                SavedJobModel.job_id == job.job_id
            )
        )
        exist_result = await db.execute(exist_stmt)
        if exist_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job already saved")
        
        # Save job
        db_saved = SavedJobModel(
            id=str(uuid.uuid4()),
            user_id=user["id"],
            job_id=job.job_id,
            created_at=datetime.utcnow()
        )
        
        db.add(db_saved)
        await db.commit()
        await db.refresh(db_saved)
        
        return db_saved
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error saving job: {str(e)}")

@router.get("/", response_model=List[dict])
async def get_saved_jobs(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        user = current_user
        if user["role"] != "job_seeker":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only job seekers can view saved jobs")
        
        # Get saved jobs with job details via join
        stmt = select(SavedJobModel, JobModel).join(JobModel, SavedJobModel.job_id == JobModel.id)\
            .where(SavedJobModel.user_id == user["id"])\
            .order_by(SavedJobModel.created_at.desc())
            
        result = await db.execute(stmt)
        saved_jobs = []
        for saved, job in result.all():
            saved_jobs.append({
                "id": saved.id,
                "job_id": saved.job_id,
                "created_at": saved.created_at,
                "job_details": {
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "salary_min": job.salary_min,
                    "salary_max": job.salary_max,
                    "experience_required": job.experience_required,
                    "work_mode": job.work_mode,
                    "skills": job.skills
                }
            })
        
        return saved_jobs
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error fetching saved jobs: {str(e)}")

@router.delete("/{saved_job_id}")
async def unsave_job(saved_job_id: str, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        user = current_user
        if user["role"] != "job_seeker":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only job seekers can unsave jobs")
        
        stmt = select(SavedJobModel).where(
            and_(
                SavedJobModel.id == saved_job_id,
                SavedJobModel.user_id == user["id"]
            )
        )
        result = await db.execute(stmt)
        db_saved = result.scalar_one_or_none()
        
        if not db_saved:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved job not found")
        
        await db.delete(db_saved)
        await db.commit()
        
        return {"message": "Job unsaved successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error unsaving job: {str(e)}")
