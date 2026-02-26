from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class RecruiterProfileBase(BaseModel):
    company_name: Optional[str] = None
    company_logo: Optional[str] = None
    designation: Optional[str] = None
    company_website: Optional[str] = None
    industry: Optional[str] = None

class RecruiterProfileCreate(RecruiterProfileBase):
    user_id: str

class RecruiterProfileUpdate(RecruiterProfileBase):
    pass

class RecruiterProfile(RecruiterProfileBase):
    id: str
    user_id: str
    created_at: datetime = datetime.now()
    
    class Config:
        from_attributes = True
        # For backward compatibility with v1
        populate_by_name = True