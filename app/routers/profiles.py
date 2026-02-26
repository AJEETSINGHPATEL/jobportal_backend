from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.job_seeker_profile import JobSeekerProfileCreate, JobSeekerProfileUpdate, JobSeekerProfile as JobSeekerProfileSchema
from app.models.recruiter_profile import RecruiterProfileCreate, RecruiterProfileUpdate, RecruiterProfile as RecruiterProfileSchema
from app.database.database import get_db
from app.database.models import JobSeekerProfile as JobSeekerProfileModel, RecruiterProfile as RecruiterProfileModel, User as UserModel
from app.utils.auth import get_current_user
from typing import List, Optional
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/profiles", tags=["Profiles"])

@router.post("/job-seeker", response_model=JobSeekerProfileSchema)
async def create_job_seeker_profile(profile: JobSeekerProfileCreate, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        user = current_user
        if user["role"] != "job_seeker":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only job seekers can create job seeker profiles")
        
        stmt = select(JobSeekerProfileModel).where(JobSeekerProfileModel.user_id == user["id"])
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job seeker profile already exists")
        
        db_profile = JobSeekerProfileModel(
            id=str(uuid.uuid4()),
            user_id=user["id"],
            phone=profile.phone,
            skills=[s.model_dump() for s in profile.skills] if profile.skills else [],
            experience_years=profile.experience_years,
            total_experience_months=profile.total_experience_months,
            education=[e.model_dump() for e in profile.education] if profile.education else [],
            employment_history=[h.model_dump() for h in profile.employment_history] if profile.employment_history else [],
            projects=[p.model_dump() for p in profile.projects] if profile.projects else [],
            personal_details=profile.personal_details.model_dump() if profile.personal_details else None,
            social_links=profile.social_links,
            preferred_locations=profile.preferred_locations,
            resume_url=profile.resume_url,
            profile_completion_pct=profile.profile_completion_pct,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(db_profile)
        await db.commit()
        await db.refresh(db_profile)
        return db_profile
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error creating job seeker profile: {str(e)}")

@router.put("/job-seeker", response_model=JobSeekerProfileSchema)
async def update_job_seeker_profile(profile: JobSeekerProfileUpdate, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        user = current_user
        if user["role"] != "job_seeker":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only job seekers can update job seeker profiles")
        
        stmt = select(JobSeekerProfileModel).where(JobSeekerProfileModel.user_id == user["id"])
        result = await db.execute(stmt)
        db_profile = result.scalar_one_or_none()
        if not db_profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job seeker profile not found")
        
        update_data = profile.model_dump(exclude_unset=True)
        
        # Special handling for JSONB fields if they are complex objects
        if "skills" in update_data:
            db_profile.skills = [s.model_dump() if hasattr(s, 'model_dump') else s for s in profile.skills]
        if "education" in update_data:
            db_profile.education = [e.model_dump() if hasattr(e, 'model_dump') else e for e in profile.education]
        if "employment_history" in update_data:
            db_profile.employment_history = [h.model_dump() if hasattr(h, 'model_dump') else h for h in profile.employment_history]
        if "projects" in update_data:
            db_profile.projects = [p.model_dump() if hasattr(p, 'model_dump') else p for p in profile.projects]
        if "personal_details" in update_data:
            db_profile.personal_details = profile.personal_details.model_dump() if profile.personal_details else None
            
        # Standard fields
        for key, value in update_data.items():
            if key not in ["skills", "education", "employment_history", "projects", "personal_details"]:
                setattr(db_profile, key, value)
        
        db_profile.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(db_profile)
        return db_profile
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error updating job seeker profile: {str(e)}")

@router.get("/job-seeker/me", response_model=JobSeekerProfileSchema)
async def get_my_job_seeker_profile(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        user = current_user
        if user["role"] != "job_seeker":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only job seekers can access job seeker profiles")
        
        stmt = select(JobSeekerProfileModel).where(JobSeekerProfileModel.user_id == user["id"])
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job seeker profile not found")
        return profile
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error fetching job seeker profile: {str(e)}")

@router.post("/recruiter", response_model=RecruiterProfileSchema)
async def create_recruiter_profile(profile: RecruiterProfileCreate, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        user = current_user
        if user["role"] != "employer":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only employers can create recruiter profiles")
            
        stmt = select(RecruiterProfileModel).where(RecruiterProfileModel.user_id == user["id"])
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Recruiter profile already exists")
            
        db_profile = RecruiterProfileModel(
            id=str(uuid.uuid4()),
            user_id=user["id"],
            company_name=profile.company_name,
            company_logo=profile.company_logo,
            designation=profile.designation,
            company_website=profile.company_website,
            industry=profile.industry,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(db_profile)
        await db.commit()
        await db.refresh(db_profile)
        return db_profile
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error creating recruiter profile: {str(e)}")

@router.put("/recruiter", response_model=RecruiterProfileSchema)
async def update_recruiter_profile(profile: RecruiterProfileUpdate, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        user = current_user
        if user["role"] != "employer":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only employers can update recruiter profiles")
        
        stmt = select(RecruiterProfileModel).where(RecruiterProfileModel.user_id == user["id"])
        result = await db.execute(stmt)
        db_profile = result.scalar_one_or_none()
        
        if not db_profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recruiter profile not found")
            
        update_data = profile.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_profile, key, value)
            
        db_profile.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(db_profile)
        return db_profile
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error updating recruiter profile: {str(e)}")

@router.get("/recruiter/me", response_model=RecruiterProfileSchema)
async def get_my_recruiter_profile(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        user = current_user
        if user["role"] != "employer":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only employers can access recruiter profiles")
        
        stmt = select(RecruiterProfileModel).where(RecruiterProfileModel.user_id == user["id"])
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recruiter profile not found")
        return profile
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error fetching recruiter profile: {str(e)}")

@router.get("/candidates", response_model=List[dict])
async def search_candidates(
    skills: Optional[str] = None, 
    experience: Optional[int] = None, 
    location: Optional[str] = None, 
    current_user: dict = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    try:
        user = current_user
        if user["role"] != "employer":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only employers can search candidates")
        
        stmt = select(JobSeekerProfileModel, UserModel.full_name, UserModel.email)\
            .join(UserModel, JobSeekerProfileModel.user_id == UserModel.id)
            
        if skills:
            skills_list = [s.strip() for s in skills.split(",")]
            stmt = stmt.where(JobSeekerProfileModel.skills.overlap(skills_list))
            
        if experience:
            stmt = stmt.where(JobSeekerProfileModel.experience_years >= experience)
            
        if location:
            stmt = stmt.where(JobSeekerProfileModel.preferred_locations.contains([location]))
            
        result = await db.execute(stmt)
        candidates = []
        for profile, full_name, email in result.all():
            candidates.append({
                "id": profile.id,
                "user_id": profile.user_id,
                "full_name": full_name,
                "email": email,
                "phone": profile.phone,
                "skills": profile.skills,
                "experience_years": profile.experience_years,
                "preferred_locations": profile.preferred_locations,
                "resume_url": profile.resume_url,
                "profile_completion_pct": profile.profile_completion_pct
            })
        
        return candidates
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error searching candidates: {str(e)}")
