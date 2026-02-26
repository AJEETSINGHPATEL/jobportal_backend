from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class NotificationType(str, Enum):
    JOB_ALERT = "job_alert"
    APPLICATION_STATUS = "application_status"
    PROFILE_VIEWED = "profile_viewed"
    JOB_POSTED = "job_posted"
    MESSAGE = "message"

class NotificationBase(BaseModel):
    user_id: str
    title: str
    message: str
    type: NotificationType
    related_id: Optional[str] = None  # Job ID, Application ID, etc.

class NotificationCreate(NotificationBase):
    pass

class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None

class Notification(NotificationBase):
    id: str
    is_read: bool = False
    created_at: datetime = datetime.now()
    read_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        # For backward compatibility with v1
        populate_by_name = True
