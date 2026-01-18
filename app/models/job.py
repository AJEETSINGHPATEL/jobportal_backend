from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class JobType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    FREELANCE = "freelance"

class JobLocationType(str, Enum):
    REMOTE = "remote"
    ONSITE = "onsite"
    HYBRID = "hybrid"

class JobBase(BaseModel):
    title: str
    description: str
    company: str
    salary_min: Optional[int]
    salary_max: Optional[int]
    location: str
    skills: List[str]
    experience_required: Optional[str]
    work_mode: Optional[str]
    company_logo_url: Optional[str]
    company_rating: Optional[float]
    reviews_count: Optional[int]

class JobCreate(JobBase):
    pass

class JobUpdate(JobBase):
    pass

class Job(JobBase):
    id: str
    posted_date: datetime
    is_active: bool
    application_count: int
    view_count: int
    
    class Config:
        from_attributes = True
        # For backward compatibility with v1
        populate_by_name = True