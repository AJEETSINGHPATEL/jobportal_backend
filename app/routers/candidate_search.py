from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.database.database import get_db
from app.database.models import JobSeekerProfile as JobSeekerProfileModel, User as UserModel
from app.utils.auth import get_current_user
from app.models.job_seeker_profile import JobSeekerProfile as JobSeekerProfileSchema
from typing import List, Optional

router = APIRouter(
    prefix="/api/recruiters/search",
    tags=["recruiters"]
)

@router.get("/candidates", response_model=List[JobSeekerProfileSchema])
async def search_candidates(
    skills: Optional[str] = Query(None, description="Comma separated skills"),
    location: Optional[str] = Query(None, description="Preferred or current location"),
    min_experience: Optional[int] = Query(None, description="Minimum years of experience"),
    token: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    current_user = token
    if current_user.get("role") not in ["employer", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only recruiters can search candidates")

    stmt = select(JobSeekerProfileModel).join(UserModel, JobSeekerProfileModel.user_id == UserModel.id)
    filters = []

    if skills:
        skill_list = [s.strip() for s in skills.split(",")]
        # Using overlap for JSONB array of strings or simple containment check
        # For array of objects, this might need adjustment, but maintaining consistency with profiles.py
        filters.append(JobSeekerProfileModel.skills.overlap(skill_list))

    if location:
        # Check in preferred_locations (JSONB array)
        filters.append(JobSeekerProfileModel.preferred_locations.contains([location]))

    if min_experience is not None:
        filters.append(JobSeekerProfileModel.experience_years >= min_experience)

    if filters:
        stmt = stmt.where(and_(*filters))

    stmt = stmt.limit(50)
    result = await db.execute(stmt)
    return result.scalars().all()
