from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Experience(BaseModel):
    title: str
    company: str
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    description: Optional[str] = None

class Education(BaseModel):
    school: str
    degree: str
    field: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None

class Project(BaseModel):
    title: str
    description: str
    url: Optional[str] = None
    technologies: List[str] = []

class ProfileBase(BaseModel):
    fullName: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    experience: List[Experience] = []
    education: List[Education] = []
    skills: List[str] = []
    projects: List[Project] = []
    profilePicture: Optional[str] = None  # URL to profile picture

class ProfileCreate(ProfileBase):
    user_id: str
    pass

class ProfileUpdate(ProfileBase):
    pass

class ProfileInDB(ProfileBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    profile_completion: Optional[int] = 0  # Percentage of profile completion
    profile_views: int = 0  # Number of recruiter views

    class Config:
        from_attributes = True
        # For backward compatibility with v1
        populate_by_name = True