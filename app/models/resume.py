from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ResumeBase(BaseModel):
    user_id: str
    file_name: str
    file_size: int
    file_type: str
    ats_score: Optional[int] = None
    skills: Optional[List[str]] = []
    experience_years: Optional[int] = None
    achievements: Optional[List[str]] = []
    improvements: Optional[List[str]] = []
    sections: Optional[dict] = {}
    resume_url: Optional[str] = None

class ResumeCreate(ResumeBase):
    pass

class ResumeUpdate(ResumeBase):
    pass

class ResumeInDB(ResumeBase):
    id: str
    uploaded_at: datetime
    analyzed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        # For backward compatibility with v1
        populate_by_name = True