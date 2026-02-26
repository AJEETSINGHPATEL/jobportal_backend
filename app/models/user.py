from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    JOB_SEEKER = "job_seeker"
    EMPLOYER = "employer"
    ADMIN = "admin"

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole

class UserCreate(UserBase):
    password: str
    mobile: str = ""
    resume_url: str = ""
    is_active: bool = True
    
    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v):
        if len(v) > 72:
            raise ValueError("Password cannot be longer than 72 characters due to security limitations")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    id: str
    is_verified: bool = False
    is_active: bool = True
    created_at: datetime = datetime.now()
    
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None