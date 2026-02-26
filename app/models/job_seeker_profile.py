from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

class Education(BaseModel):
    institution: str
    degree: str
    field_of_study: str
    start_date: datetime
    end_date: Optional[datetime] = None
    grade: Optional[str] = None
    description: Optional[str] = None

class EmploymentHistory(BaseModel):
    company: str
    designation: str
    start_date: datetime
    end_date: Optional[datetime] = None
    is_current: bool = False
    salary: Optional[str] = None  # e.g., "10 LPA"
    description: Optional[str] = None
    notice_period: Optional[str] = None

class Project(BaseModel):
    title: str
    description: Optional[str] = None
    role: Optional[str] = None
    url: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class PersonalDetails(BaseModel):
    dob: Optional[datetime] = None
    gender: Optional[str] = None
    current_location: Optional[str] = None
    languages: List[str] = []
    resume_headline: Optional[str] = None

class Skill(BaseModel):
    name: str
    version: Optional[str] = None
    experience_months: Optional[int] = None

class JobSeekerProfileBase(BaseModel):
    phone: Optional[str] = None
    skills: List[Skill] = []  # Updated from List[str]
    experience_years: Optional[int] = None
    total_experience_months: Optional[int] = None # Calculated total
    education: List[Education] = []
    employment_history: List[EmploymentHistory] = []
    projects: List[Project] = []
    personal_details: Optional[PersonalDetails] = None
    social_links: Dict[str, str] = {} # e.g. {"linkedin": "url", "github": "url"}
    preferred_locations: List[str] = []
    resume_url: Optional[str] = None
    profile_completion_pct: Optional[int] = 0

class JobSeekerProfileCreate(JobSeekerProfileBase):
    user_id: str

class JobSeekerProfileUpdate(JobSeekerProfileBase):
    pass

class JobSeekerProfile(JobSeekerProfileBase):
    id: str
    user_id: str
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    
    class Config:
        from_attributes = True
        populate_by_name = True