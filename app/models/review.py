from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class ReviewType(str, Enum):
    COMPANY = "company"
    JOB = "job"

class ReviewBase(BaseModel):
    company_id: str
    user_id: str
    rating_work_culture: int  # 1-5
    rating_salary: int  # 1-5
    rating_hr: int  # 1-5
    rating_management: int  # 1-5
    pros: str
    cons: str
    interview_experience: Optional[str] = None

class ReviewCreate(ReviewBase):
    pass

class ReviewUpdate(BaseModel):
    pros: Optional[str] = None
    cons: Optional[str] = None
    interview_experience: Optional[str] = None
    rating_work_culture: Optional[int] = None
    rating_salary: Optional[int] = None
    rating_hr: Optional[int] = None
    rating_management: Optional[int] = None

class Review(ReviewBase):
    id: str
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    
    class Config:
        from_attributes = True
        # For backward compatibility with v1
        populate_by_name = True