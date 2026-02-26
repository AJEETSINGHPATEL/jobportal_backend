from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SavedJobBase(BaseModel):
    user_id: str
    job_id: str

class SavedJobCreate(SavedJobBase):
    pass

class SavedJob(SavedJobBase):
    id: str
    created_at: datetime = datetime.now()
    
    class Config:
        from_attributes = True
        # For backward compatibility with v1
        populate_by_name = True