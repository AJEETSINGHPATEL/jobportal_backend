from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.database.database import get_db
from app.database.models import JobSeekerProfile as JobSeekerProfileModel, User as UserModel
from app.models.profile import ProfileCreate, ProfileUpdate, ProfileInDB
from app.utils.auth import get_current_user
from typing import List, Optional
import datetime
import uuid
import os
from pathlib import Path

router = APIRouter(prefix="/api/profile", tags=["Profile"])

def calculate_profile_completion(profile_data: dict) -> int:
    """Calculate profile completion percentage based on required and optional fields"""
    total_points = 0
    earned_points = 0
    
    # Required fields (higher weight)
    personal_details = profile_data.get('personal_details', {})
    if not personal_details:
        personal_details = profile_data # Fallback for schema dict
        
    required_fields = ['fullName', 'email']
    for field in required_fields:
        if personal_details.get(field) and str(personal_details.get(field)).strip():
            earned_points += 2
        total_points += 2
    
    # Optional fields
    phone = profile_data.get('phone')
    if phone and str(phone).strip():
        earned_points += 1
    total_points += 1
    
    for field in ['address', 'headline', 'summary', 'profilePicture']:
        if personal_details.get(field) and str(personal_details.get(field)).strip():
            earned_points += 1
        total_points += 1
    
    # Experience section
    experience = profile_data.get('employment_history', profile_data.get('experience', []))
    if experience:
        for exp in experience:
            if exp.get('title') and exp.get('company'):
                earned_points += 2
            total_points += 2
    
    # Education section
    education = profile_data.get('education', [])
    if education:
        for edu in education:
            if edu.get('school') and edu.get('degree'):
                earned_points += 2
            total_points += 2
    
    # Skills section
    skills = profile_data.get('skills', [])
    if skills:
        skill_points = min(len(skills) * 0.5, 10)
        earned_points += skill_points
        total_points += 10

    # Projects section
    projects = profile_data.get('projects', [])
    if projects:
        for proj in projects:
            if proj.get('title') and proj.get('description'):
                earned_points += 2
            total_points += 2
    else:
        total_points += 4
    
    if total_points == 0:
        return 0
    
    completion_percentage = int((earned_points / total_points) * 100)
    return min(completion_percentage, 100)

def map_model_to_schema(db_profile: JobSeekerProfileModel, user: Optional[UserModel] = None) -> ProfileInDB:
    pd = db_profile.personal_details or {}
    return ProfileInDB(
        id=db_profile.id,
        user_id=db_profile.user_id,
        fullName=pd.get("fullName", user.full_name if user else ""),
        email=pd.get("email", user.email if user else ""),
        phone=db_profile.phone,
        address=pd.get("address"),
        headline=pd.get("headline"),
        summary=pd.get("summary"),
        experience=[{"title": h["title"], "company": h["company"], "startDate": h.get("startDate"), "endDate": h.get("endDate"), "description": h.get("description")} for h in db_profile.employment_history],
        education=[{"school": e["school"], "degree": e["degree"], "field": e.get("field"), "startDate": e.get("startDate"), "endDate": e.get("endDate")} for e in db_profile.education],
        skills=db_profile.skills,
        projects=[{"title": p["title"], "description": p["description"], "url": p.get("url"), "technologies": p.get("technologies", [])} for p in db_profile.projects],
        profilePicture=pd.get("profilePicture"),
        created_at=db_profile.created_at,
        updated_at=db_profile.updated_at,
        profile_completion=db_profile.profile_completion_pct,
        profile_views=db_profile.profile_views or 0
    )

@router.post("/", response_model=ProfileInDB)
async def create_profile(
    profile: ProfileCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        if current_user["id"] != profile.user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        stmt = select(JobSeekerProfileModel).where(JobSeekerProfileModel.user_id == profile.user_id)
        if (await db.execute(stmt)).scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Profile already exists")
        
        profile_dict = profile.model_dump()
        completion = calculate_profile_completion(profile_dict)
        
        db_profile = JobSeekerProfileModel(
            id=str(uuid.uuid4()),
            user_id=profile.user_id,
            phone=profile.phone,
            skills=profile.skills,
            education=[e.model_dump() for e in profile.education] if profile.education else [],
            employment_history=[h.model_dump() for h in profile.experience] if profile.experience else [],
            projects=[p.model_dump() for p in profile.projects] if profile.projects else [],
            personal_details={
                "fullName": profile.fullName,
                "email": profile.email,
                "address": profile.address,
                "headline": profile.headline,
                "summary": profile.summary,
                "profilePicture": profile.profilePicture
            },
            profile_completion_pct=completion,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
            profile_views=0
        )
        db.add(db_profile)
        
        # Sync user full name
        user_stmt = select(UserModel).where(UserModel.id == current_user["id"])
        user = (await db.execute(user_stmt)).scalar_one()
        if user.full_name != profile.fullName:
            user.full_name = profile.fullName
            
        await db.commit()
        await db.refresh(db_profile)
        return map_model_to_schema(db_profile, user)
    except HTTPException: raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me", response_model=ProfileInDB)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    stmt = select(JobSeekerProfileModel).where(JobSeekerProfileModel.user_id == current_user["id"])
    db_profile = (await db.execute(stmt)).scalar_one_or_none()
    
    if not db_profile:
        return ProfileInDB(
            id="", user_id=current_user["id"], fullName=current_user.get("full_name", ""),
            email=current_user.get("email", ""), phone="", experience=[], education=[],
            skills=[], projects=[], created_at=datetime.datetime.utcnow(), profile_completion=0
        )
    
    return map_model_to_schema(db_profile)

@router.get("/{user_id}", response_model=ProfileInDB)
async def get_profile(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(JobSeekerProfileModel).where(JobSeekerProfileModel.user_id == user_id)
    db_profile = (await db.execute(stmt)).scalar_one_or_none()
    
    if not db_profile:
        user_stmt = select(UserModel).where(UserModel.id == user_id)
        user = (await db.execute(user_stmt)).scalar_one_or_none()
        if not user: raise HTTPException(status_code=404, detail="Not found")
        return ProfileInDB(
            id="", user_id=user_id, fullName=user.full_name, email=user.email,
            phone="", experience=[], education=[], skills=[], projects=[],
            created_at=datetime.datetime.utcnow(), profile_completion=0
        )
    
    db_profile.profile_views = (db_profile.profile_views or 0) + 1
    await db.commit()
    await db.refresh(db_profile)
    return map_model_to_schema(db_profile)

@router.put("/me", response_model=ProfileInDB)
async def update_my_profile(
    update_data: ProfileUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        stmt = select(JobSeekerProfileModel).where(JobSeekerProfileModel.user_id == current_user["id"])
        db_profile = (await db.execute(stmt)).scalar_one_or_none()
        if not db_profile: raise HTTPException(status_code=404, detail="Not found")
        
        data = update_data.model_dump(exclude_unset=True)
        pd = db_profile.personal_details or {}
        
        for k in ["fullName", "email", "address", "headline", "summary", "profilePicture"]:
            if k in data: pd[k] = data[k]
        db_profile.personal_details = pd
        
        if "phone" in data: db_profile.phone = data["phone"]
        if "skills" in data: db_profile.skills = data["skills"]
        if "experience" in data:
            db_profile.employment_history = [e.model_dump() if hasattr(e, 'model_dump') else e for e in (update_data.experience or [])]
        if "education" in data:
            db_profile.education = [e.model_dump() if hasattr(e, 'model_dump') else e for e in (update_data.education or [])]
        if "projects" in data:
            db_profile.projects = [p.model_dump() if hasattr(p, 'model_dump') else p for p in (update_data.projects or [])]
            
        # Re-calc completion
        completion_data = {
            "personal_details": pd, "phone": db_profile.phone, "skills": db_profile.skills,
            "employment_history": db_profile.employment_history, "education": db_profile.education,
            "projects": db_profile.projects
        }
        db_profile.profile_completion_pct = calculate_profile_completion(completion_data)
        db_profile.updated_at = datetime.datetime.utcnow()
        
        if "fullName" in data:
            user_stmt = select(UserModel).where(UserModel.id == current_user["id"])
            user = (await db.execute(user_stmt)).scalar_one()
            user.full_name = data["fullName"]
            
        await db.commit()
        await db.refresh(db_profile)
        return map_model_to_schema(db_profile)
    except HTTPException: raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-picture")
async def upload_picture(
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        upload_dir = Path("uploads/profiles")
        upload_dir.mkdir(parents=True, exist_ok=True)
        ext = os.path.splitext(file.filename)[1]
        fname = f"{current_user['id']}_{uuid.uuid4()}{ext}"
        fpath = upload_dir / fname
        
        with open(fpath, "wb") as buffer:
            buffer.write(await file.read())
        
        url = f"/uploads/profiles/{fname}"
        stmt = select(JobSeekerProfileModel).where(JobSeekerProfileModel.user_id == current_user["id"])
        db_profile = (await db.execute(stmt)).scalar_one_or_none()
        
        if db_profile:
            pd = db_profile.personal_details or {}
            pd["profilePicture"] = url
            db_profile.personal_details = pd
            db_profile.updated_at = datetime.datetime.utcnow()
            await db.commit()
            
        return {"profilePicture": url}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/user/{user_id}/view")
async def increment_view(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(JobSeekerProfileModel).where(JobSeekerProfileModel.user_id == user_id)
    db_profile = (await db.execute(stmt)).scalar_one_or_none()
    if not db_profile: raise HTTPException(status_code=404, detail="Not found")
    db_profile.profile_views = (db_profile.profile_views or 0) + 1
    await db.commit()
    return {"views": db_profile.profile_views}
