from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class JobAlertBase(BaseModel):
    user_id: str
    search_params: Dict[str, Any]  # Stores the search parameters that triggered the alert
    title: str  # Human-readable title for the alert
    is_active: bool = True
    frequency: str = "daily"  # daily, weekly, instant
    email_notifications: bool = True
    push_notifications: bool = True

class JobAlertCreate(JobAlertBase):
    pass

class JobAlertUpdate(BaseModel):
    is_active: Optional[bool] = None
    frequency: Optional[str] = None
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None

class JobAlert(JobAlertBase):
    id: str
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    last_triggered: Optional[datetime] = None
    matched_jobs_count: int = 0
    
    class Config:
        from_attributes = True
        # For backward compatibility with v1
        populate_by_name = True