from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class ApplicationStatus(str, Enum):
    APPLIED = "applied"
    REVIEWED = "reviewed"
    INTERVIEW = "interview"
    OFFERED = "offered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class ApplicationBase(BaseModel):
    job_id: str
    status: ApplicationStatus = ApplicationStatus.APPLIED
    cover_letter: Optional[str] = None
    resume_url: Optional[str] = None

class ApplicationCreate(ApplicationBase):
    # Don't include user_id in the input model - backend will add it from token
    pass

class ApplicationUpdate(BaseModel):
    status: Optional[ApplicationStatus] = None
    notes: Optional[str] = None
    viewed_at: Optional[datetime] = None

class Application(ApplicationBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    viewed_at: Optional[datetime] = None
    questionnaire_answers: Optional[dict] = {}
    
    class Config:
        from_attributes = True
        # For backward compatibility with v1
        populate_by_name = True
        # Allow extra fields for job title and company
        extra = "allow"