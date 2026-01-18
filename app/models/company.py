from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class CompanyVerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"

class CompanyBase(BaseModel):
    name: str
    description: str
    website: str
    industry: str
    size: str
    founded_year: int
    headquarters: str
    email_domain: str

class CompanyCreate(CompanyBase):
    owner_id: str  # Employer ID who owns this company

class CompanyUpdate(CompanyBase):
    pass

class Company(CompanyBase):
    id: str
    owner_id: str
    verification_status: CompanyVerificationStatus = CompanyVerificationStatus.PENDING
    is_verified: bool = False
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    
    class Config:
        from_attributes = True
        # For backward compatibility with v1
        populate_by_name = True