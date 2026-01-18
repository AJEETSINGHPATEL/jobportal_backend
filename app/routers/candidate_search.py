from fastapi import APIRouter, Depends, HTTPException, Query
from app.database.database import get_job_seeker_profiles_collection
from app.routers.auth import get_current_user
from app.models.user import User
from typing import List, Optional
from app.models.job_seeker_profile import JobSeekerProfile

router = APIRouter(
    prefix="/api/recruiters/search",
    tags=["recruiters"]
)

@router.get("/candidates", response_model=List[JobSeekerProfile])
async def search_candidates(
    skills: Optional[str] = Query(None, description="Comma separated skills"),
    location: Optional[str] = Query(None, description="Preferred or current location"),
    min_experience: Optional[int] = Query(None, description="Minimum years of experience"),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "employer" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only recruiters can search candidates")

    query = {}

    if skills:
        skill_list = [s.strip() for s in skills.split(",")]
        # Match if any of the skills are in the skills list (using regex for flexibility or exact match)
        # Assuming skills in DB are stored as objects, but we search by name
        query["skills.name"] = {"$in": skill_list}

    if location:
        # Search in preferred_locations OR personal_details.current_location
        query["$or"] = [
            {"preferred_locations": {"$regex": location, "$options": "i"}},
            {"personal_details.current_location": {"$regex": location, "$options": "i"}}
        ]

    if min_experience is not None:
        query["experience_years"] = {"$gte": min_experience}

    profiles_collection = get_job_seeker_profiles_collection()
    cursor = profiles_collection.find(query).limit(50) # Limit results for now
    
    profiles = []
    async for doc in cursor:
        profiles.append(JobSeekerProfile(**doc))
        
    return profiles
