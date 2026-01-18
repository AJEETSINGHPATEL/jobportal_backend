from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class VerificationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class CompanyVerificationBase(BaseModel):
    company_id: str
    owner_id: str
    verification_documents: dict  # Contains paths/URLs to documents like GST, business license, etc.
    verification_status: VerificationStatus = VerificationStatus.PENDING
    verification_notes: Optional[str] = None

class CompanyVerificationCreate(CompanyVerificationBase):
    pass

class CompanyVerificationUpdate(BaseModel):
    verification_status: Optional[VerificationStatus] = None
    verification_notes: Optional[str] = None

class CompanyVerification(CompanyVerificationBase):
    id: str
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    verified_by: Optional[str] = None  # Admin ID who verified
    
    class Config:
        from_attributes = True
        # For backward compatibility with v1
        populate_by_name = True