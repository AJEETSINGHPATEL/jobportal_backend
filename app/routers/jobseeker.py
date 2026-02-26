from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.database.database import get_db
from app.database.models import Application as ApplicationModel, SavedJob as SavedJobModel, JobSeekerProfile as JobSeekerProfileModel, Job as JobModel
from app.models.job_seeker_profile import JobSeekerProfileUpdate
from app.utils.auth import get_current_user
from typing import List
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/jobseeker", tags=["Job Seeker"])

@router.post("/jobs/{job_id}/apply")
async def apply_for_job(
    job_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Verify user exists and is a job seeker
        if current_user["role"] != "job_seeker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only job seekers can apply for jobs"
            )
        
        # Check if job exists
        job_stmt = select(JobModel).where(JobModel.id == job_id)
        job = (await db.execute(job_stmt)).scalar_one_or_none()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Check if already applied
        existing_app_stmt = select(ApplicationModel).where(
            and_(ApplicationModel.job_id == job_id, ApplicationModel.user_id == current_user["id"])
        )
        existing_application = (await db.execute(existing_app_stmt)).scalar_one_or_none()
        if existing_application:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already applied for this job"
            )
        
        # Create application
        application = ApplicationModel(
            id=str(uuid.uuid4()),
            job_id=job_id,
            user_id=current_user["id"],
            status="applied",
            applied_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        db.add(application)
        
        # Increment job application count
        job.application_count = (job.application_count or 0) + 1
        
        await db.commit()
        
        return {
            "success": True,
            "message": "Successfully applied for the job",
            "application_id": application.id
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error applying for job: {str(e)}"
        )

@router.post("/jobs/{job_id}/save")
async def save_job(
    job_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Verify user is a job seeker
        if current_user["role"] != "job_seeker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only job seekers can save jobs"
            )
        
        # Check if job exists
        job_stmt = select(JobModel).where(JobModel.id == job_id)
        job = (await db.execute(job_stmt)).scalar_one_or_none()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Check if already saved
        existing_save_stmt = select(SavedJobModel).where(
            and_(SavedJobModel.user_id == current_user["id"], SavedJobModel.job_id == job_id)
        )
        existing_saved_job = (await db.execute(existing_save_stmt)).scalar_one_or_none()
        if existing_saved_job:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job already saved"
            )
        
        # Save job
        saved_job = SavedJobModel(
            id=str(uuid.uuid4()),
            user_id=current_user["id"],
            job_id=job_id,
            created_at=datetime.utcnow()
        )
        db.add(saved_job)
        await db.commit()
        
        return {
            "success": True,
            "message": "Job saved successfully",
            "saved_job_id": saved_job.id
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving job: {str(e)}"
        )

@router.get("/applications")
async def get_applications(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Verify user exists and is a job seeker
        if current_user["role"] != "job_seeker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only job seekers can view their applications"
            )
        
        # Get applications with job details
        stmt = select(ApplicationModel, JobModel.title, JobModel.company, JobModel.location)\
            .join(JobModel, JobModel.id == ApplicationModel.job_id)\
            .where(ApplicationModel.user_id == current_user["id"])\
            .order_by(ApplicationModel.applied_at.desc())
            
        result = await db.execute(stmt)
        applications = []
        for app, title, company, location in result.all():
            applications.append({
                "id": app.id,
                "job_id": app.job_id,
                "status": app.status,
                "created_at": app.applied_at,
                "job_title": title,
                "company": company,
                "location": location
            })
        
        return {
            "success": True,
            "data": applications
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching applications: {str(e)}"
        )

@router.get("/saved-jobs")
async def get_saved_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Verify user exists and is a job seeker
        if current_user["role"] != "job_seeker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only job seekers can view saved jobs"
            )
        
        # Get saved jobs with job details
        stmt = select(SavedJobModel, JobModel)\
            .join(JobModel, JobModel.id == SavedJobModel.job_id)\
            .where(SavedJobModel.user_id == current_user["id"])\
            .order_by(SavedJobModel.created_at.desc())
            
        result = await db.execute(stmt)
        saved_jobs = []
        for saved_job, job in result.all():
            saved_jobs.append({
                "id": saved_job.id,
                "job_id": saved_job.job_id,
                "created_at": saved_job.created_at,
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
        
        return {
            "success": True,
            "data": saved_jobs
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching saved jobs: {str(e)}"
        )

@router.get("/profile")
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Verify user is a job seeker
        if current_user["role"] != "job_seeker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only job seekers can view their profile"
            )
        
        # Get profile
        stmt = select(JobSeekerProfileModel).where(JobSeekerProfileModel.user_id == current_user["id"])
        profile = (await db.execute(stmt)).scalar_one_or_none()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )
        
        return {
            "success": True,
            "data": profile
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching profile: {str(e)}"
        )

@router.put("/profile")
async def update_profile(
    profile_data: JobSeekerProfileUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Verify user is a job seeker
        if current_user["role"] != "job_seeker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only job seekers can update their profile"
            )
        
        # Check if profile exists
        stmt = select(JobSeekerProfileModel).where(JobSeekerProfileModel.user_id == current_user["id"])
        db_profile = (await db.execute(stmt)).scalar_one_or_none()
        
        update_dict = profile_data.model_dump(exclude_unset=True)
        # Handle JSONB fields correctly
        if "skills" in update_dict:
            update_dict["skills"] = [s.model_dump() if hasattr(s, 'model_dump') else s for s in profile_data.skills]
        if "education" in update_dict:
            update_dict["education"] = [e.model_dump() if hasattr(e, 'model_dump') else e for e in profile_data.education]
        if "employment_history" in update_dict:
            update_dict["employment_history"] = [h.model_dump() if hasattr(h, 'model_dump') else h for h in profile_data.employment_history]
        if "projects" in update_dict:
            update_dict["projects"] = [p.model_dump() if hasattr(p, 'model_dump') else p for p in profile_data.projects]
        if "personal_details" in update_dict:
            update_dict["personal_details"] = profile_data.personal_details.model_dump() if profile_data.personal_details else None

        if db_profile:
            # Update existing profile
            for key, value in update_dict.items():
                setattr(db_profile, key, value)
            db_profile.updated_at = datetime.utcnow()
        else:
            # Create new profile
            db_profile = JobSeekerProfileModel(
                id=str(uuid.uuid4()),
                user_id=current_user["id"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                **update_dict
            )
            db.add(db_profile)
        
        await db.commit()
        await db.refresh(db_profile)
        
        return {
            "success": True,
            "message": "Profile updated successfully",
            "data": db_profile
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating profile: {str(e)}"
        )
