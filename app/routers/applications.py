from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete
from sqlalchemy.orm import joinedload
from app.models.application import ApplicationCreate, ApplicationUpdate, Application as ApplicationSchema
from app.database.database import get_db
from app.database.models import Application as ApplicationModel, Job as JobModel, User as UserModel
from app.utils.auth import get_current_user
from typing import List, Optional
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/applications", tags=["Applications"])

@router.post("/", response_model=ApplicationSchema)
async def create_application(
    application: ApplicationCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        
        # Verify job exists
        job_stmt = select(JobModel).where(JobModel.id == application.job_id)
        job_result = await db.execute(job_stmt)
        job = job_result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check for existing application
        exist_stmt = select(ApplicationModel).where(
            and_(
                ApplicationModel.user_id == current_user["id"],
                ApplicationModel.job_id == application.job_id
            )
        )
        exist_result = await db.execute(exist_stmt)
        if exist_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Application already submitted")
        
        # Create application
        db_app = ApplicationModel(
            id=str(uuid.uuid4()),
            job_id=application.job_id,
            user_id=current_user["id"],
            status=application.status.value if hasattr(application.status, 'value') else str(application.status),
            cover_letter=application.cover_letter,
            resume_url=application.resume_url,
            applied_at=datetime.utcnow()
        )
        
        db.add(db_app)
        
        # Update job application count
        job.application_count += 1
        
        await db.commit()
        await db.refresh(db_app)
        
        return db_app
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[ApplicationSchema])
async def get_user_applications(
    current_user: dict = Depends(get_current_user),
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    
    # We want to return application with job details. 
    # The Pydantic model 'Application' has job_title and company which are not in the table.
    # We can fetch them via join.
    stmt = select(ApplicationModel, JobModel.title, JobModel.company)\
        .join(JobModel, ApplicationModel.job_id == JobModel.id)\
        .where(ApplicationModel.user_id == current_user["id"])\
        .offset(skip).limit(limit)
    
    result = await db.execute(stmt)
    applications = []
    for app, job_title, company in result.all():
        app_dict = {c.name: getattr(app, c.name) for c in app.__table__.columns}
        app_dict["job_title"] = job_title
        app_dict["company"] = company
        applications.append(app_dict)
    
    return applications

@router.get("/job/{job_id}", response_model=List[ApplicationSchema])
async def get_job_applications(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    
    # Verify job exists and belongs to current user
    job_stmt = select(JobModel).where(JobModel.id == job_id)
    job_result = await db.execute(job_stmt)
    job = job_result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.posted_by != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    stmt = select(ApplicationModel, UserModel.full_name, UserModel.email)\
        .join(UserModel, ApplicationModel.user_id == UserModel.id)\
        .where(ApplicationModel.job_id == job_id)
    
    result = await db.execute(stmt)
    applications = []
    for app, applicant_name, applicant_email in result.all():
        app_dict = {c.name: getattr(app, c.name) for c in app.__table__.columns}
        app_dict["applicant_name"] = applicant_name
        app_dict["applicant_email"] = applicant_email
        applications.append(app_dict)
        
    return applications

@router.get("/{application_id}", response_model=ApplicationSchema)
async def get_application(
    application_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    
    stmt = select(ApplicationModel, JobModel.title, JobModel.company, JobModel.posted_by)\
        .join(JobModel, ApplicationModel.job_id == JobModel.id)\
        .where(ApplicationModel.id == application_id)
    
    result = await db.execute(stmt)
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    
    app, job_title, company, posted_by = row
    
    # Check authorization
    if app.user_id != current_user["id"] and posted_by != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    app_dict = {c.name: getattr(app, c.name) for c in app.__table__.columns}
    app_dict["job_title"] = job_title
    app_dict["company"] = company
    
    return app_dict

@router.put("/{application_id}", response_model=ApplicationSchema)
async def update_application(
    application_id: str,
    application_update: ApplicationUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    
    stmt = select(ApplicationModel).where(ApplicationModel.id == application_id)
    result = await db.execute(stmt)
    db_app = result.scalar_one_or_none()
    
    if not db_app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Only the applicant can update (e.g. cover letter) or the employer can update (status)
    # The original implementation seems to allow only the owner to update.
    # But usually employer updates status.
    
    # Let's check who's updating.
    if db_app.user_id != current_user["id"] and current_user.get("role") != "employer" and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    update_data = application_update.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"]:
        if hasattr(update_data["status"], 'value'):
            db_app.status = update_data["status"].value
        else:
            db_app.status = str(update_data["status"])
            
    if "cover_letter" in update_data:
        db_app.cover_letter = update_data["cover_letter"]
    
    if "resume_url" in update_data:
        db_app.resume_url = update_data["resume_url"]
        
    db_app.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(db_app)
    return db_app

@router.delete("/{application_id}")
async def delete_application(application_id: str, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    
    stmt = select(ApplicationModel).where(ApplicationModel.id == application_id)
    result = await db.execute(stmt)
    db_app = result.scalar_one_or_none()
    
    if not db_app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if db_app.user_id != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    await db.delete(db_app)
    await db.commit()
    
    return {"message": "Application deleted successfully"}
