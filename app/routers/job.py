from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, update, delete, func
from app.models.job import Job as JobSchema, JobCreate, JobUpdate
from app.database.database import get_db
from app.database.models import Job as JobModel
from app.utils.auth import get_current_user
from typing import List, Optional
import uuid

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

@router.post("/", response_model=JobSchema)
async def create_job(
    job: JobCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    
    if current_user.get("role") != "employer":
        raise HTTPException(status_code=403, detail="Only employers can create jobs")
    
    db_job = JobModel(
        id=str(uuid.uuid4()),
        title=job.title,
        description=job.description,
        company=job.company,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        location=job.location,
        skills=job.skills,
        experience_required=job.experience_required,
        work_mode=job.work_mode,
        company_logo_url=job.company_logo_url,
        company_rating=job.company_rating,
        reviews_count=job.reviews_count or 0,
        employer_phone=job.employer_phone,
        employer_email=job.employer_email,
        posted_by=current_user["id"],
        is_active=True,
        application_count=0,
        view_count=0,
        posted_date=datetime.now(timezone.utc)
    )
    
    db.add(db_job)
    await db.commit()
    await db.refresh(db_job)
    return db_job

@router.get("/", response_model=List[JobSchema])
async def get_jobs(
    skip: int = 0,
    limit: int = 20,
    search: str = "",
    location: str = "",
    job_type: str = "",
    db: AsyncSession = Depends(get_db)
):
    stmt = select(JobModel).where(JobModel.is_active == True)
    
    if search:
        search_filter = or_(
            JobModel.title.ilike(f"%{search}%"),
            JobModel.description.ilike(f"%{search}%"),
            JobModel.skills.contains([search])
        )
        stmt = stmt.where(search_filter)
    
    if location:
        stmt = stmt.where(JobModel.location.ilike(f"%{location}%"))
    
    if job_type:
        stmt = stmt.where(JobModel.work_mode == job_type)
    
    stmt = stmt.order_by(JobModel.posted_date.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/search", response_model=List[JobSchema])
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
    skills: str = "",
    db: AsyncSession = Depends(get_db)
):
    stmt = select(JobModel).where(JobModel.is_active == True)
    
    if search:
        stmt = stmt.where(or_(
            JobModel.title.ilike(f"%{search}%"),
            JobModel.description.ilike(f"%{search}%"),
            JobModel.skills.contains([search])
        ))
    
    if location:
        stmt = stmt.where(JobModel.location.ilike(f"%{location}%"))
    
    final_work_mode = job_type or work_mode
    if final_work_mode:
        stmt = stmt.where(JobModel.work_mode == final_work_mode)
    
    if salary_min > 0:
        stmt = stmt.where(JobModel.salary_min >= salary_min)
    
    if skills:
        skills_list = [s.strip() for s in skills.split(",")]
        # For Postgres JSONB, we can check if it overlaps
        stmt = stmt.where(JobModel.skills.overlap(skills_list))

    stmt = stmt.order_by(JobModel.posted_date.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/my", response_model=List[JobSchema])
async def get_my_jobs(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(JobModel).where(JobModel.posted_by == current_user["id"]).order_by(JobModel.posted_date.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{job_id}", response_model=JobSchema)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(JobModel).where(and_(JobModel.id == job_id, JobModel.is_active == True))
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.put("/{job_id}", response_model=JobSchema)
async def update_job(
    job_id: str,
    job_update: JobUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(JobModel).where(JobModel.id == job_id)
    result = await db.execute(stmt)
    db_job = result.scalar_one_or_none()
    
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if db_job.posted_by != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    update_data = job_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_job, key, value)
    
    try:
        await db.commit()
        await db.refresh(db_job)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    
    return db_job

@router.delete("/{job_id}")
async def delete_job(job_id: str, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(JobModel).where(JobModel.id == job_id)
    result = await db.execute(stmt)
    db_job = result.scalar_one_or_none()
    
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if db_job.posted_by != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.delete(db_job)
    await db.commit()
    return {"message": "Job deleted successfully"}
