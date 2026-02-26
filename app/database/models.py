import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Float, JSON, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()

class UserRole(str, enum.Enum):
    JOB_SEEKER = "job_seeker"
    EMPLOYER = "employer"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True) # Using String to match existing logic if needed, or UUID
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)
    mobile = Column(String, default="")
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    resumes = relationship("Resume", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    job_seeker_profile = relationship("JobSeekerProfile", back_populates="user", uselist=False)
    recruiter_profile = relationship("RecruiterProfile", back_populates="user", uselist=False)

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    company = Column(String, nullable=False)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    location = Column(String, nullable=False)
    skills = Column(JSONB, default=[])
    experience_required = Column(String, nullable=True)
    work_mode = Column(String, nullable=True)
    company_logo_url = Column(String, nullable=True)
    company_rating = Column(Float, nullable=True)
    reviews_count = Column(Integer, default=0)
    employer_phone = Column(String, nullable=True)
    employer_email = Column(String, nullable=True)
    job_type = Column(String, nullable=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=True)
    posted_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    application_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    posted_by = Column(String, ForeignKey("users.id"))

class JobSeekerProfile(Base):
    __tablename__ = "job_seeker_profiles"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True)
    phone = Column(String, nullable=True)
    skills = Column(JSONB, default=[])
    experience_years = Column(Integer, default=0)
    total_experience_months = Column(Integer, default=0)
    education = Column(JSONB, default=[])
    employment_history = Column(JSONB, default=[])
    projects = Column(JSONB, default=[])
    personal_details = Column(JSONB, nullable=True)
    social_links = Column(JSONB, default={})
    preferred_locations = Column(JSONB, default=[])
    resume_url = Column(String, nullable=True)
    profile_completion_pct = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="job_seeker_profile")

class RecruiterProfile(Base):
    __tablename__ = "recruiter_profiles"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True)
    company_name = Column(String, nullable=True)
    company_logo = Column(String, nullable=True)
    designation = Column(String, nullable=True)
    company_website = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    company_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="recruiter_profile")

class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("jobs.id"))
    user_id = Column(String, ForeignKey("users.id"))
    status = Column(String, default="pending")
    applied_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    viewed_at = Column(DateTime, nullable=True)
    resume_url = Column(String, nullable=True)
    cover_letter = Column(Text, nullable=True)
    questionnaire_answers = Column(JSONB, default={})

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    file_name = Column(String)
    file_path = Column(String)
    file_size = Column(Integer)
    file_type = Column(String)
    resume_url = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    ats_score = Column(Integer, nullable=True)
    skills = Column(JSONB, default=[])
    experience_years = Column(Integer, nullable=True)
    achievements = Column(JSONB, default=[])
    improvements = Column(JSONB, default=[])
    analyzed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="resumes")

class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    website = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    size = Column(String, nullable=True)
    founded_at = Column(DateTime, nullable=True)
    headquarters = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    verification_status = Column(String, default="pending")
    is_verified = Column(Boolean, default=False)
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Review(Base):
    __tablename__ = "reviews"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"))
    user_id = Column(String, ForeignKey("users.id"))
    rating_work_culture = Column(Integer)
    rating_salary = Column(Integer)
    rating_hr = Column(Integer)
    rating_management = Column(Integer)
    pros = Column(Text, nullable=True)
    cons = Column(Text, nullable=True)
    interview_experience = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company")
    user = relationship("User")

class SavedJob(Base):
    __tablename__ = "saved_jobs"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    job_id = Column(String, ForeignKey("jobs.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String) # e.g., "application", "job_alert", "system"
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    activity_type = Column(String, nullable=False)
    activity_metadata = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")

class CompanyVerification(Base):
    __tablename__ = "company_verifications"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"))
    owner_id = Column(String, ForeignKey("users.id"))
    verification_documents = Column(JSONB, default={}) # GST, business license, etc.
    verification_status = Column(String, default="pending")
    verification_notes = Column(Text, nullable=True)
    verified_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company")

class JobAlert(Base):
    __tablename__ = "job_alerts"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    title = Column(String, nullable=False)
    search_params = Column(JSONB, default={})
    frequency = Column(String, default="daily") # daily, weekly
    is_active = Column(Boolean, default=True)
    email_notifications = Column(Boolean, default=True)
    push_notifications = Column(Boolean, default=True)
    last_triggered = Column(DateTime, nullable=True)
    matched_jobs_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ChatHistory(Base):
    __tablename__ = "chat_histories"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    session_id = Column(String, index=True)
    role = Column(String)  # user, assistant
    content = Column(Text)
    intent = Column(String, nullable=True)
    chat_metadata = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="chat_histories")

# Add relationship to User class (at the end of User class)
User.chat_histories = relationship("ChatHistory", back_populates="user")
