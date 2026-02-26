from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List
from datetime import datetime
from app.database.database import get_db
from app.database.models import Job as JobModel, Application as ApplicationModel, User as UserModel
from app.models.job import Job as JobSchema
from app.models.application import Application as ApplicationSchema
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/employer", tags=["Employer"])

@router.get("/dashboard/stats")
async def get_employer_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get dashboard statistics for the employer"""
    if current_user.get("role") != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can access dashboard stats"
        )
    
    # Total jobs posted by employer
    jobs_stmt = select(func.count(JobModel.id)).where(JobModel.posted_by == current_user["id"])
    total_jobs = (await db.execute(jobs_stmt)).scalar() or 0
    
    # Active jobs
    active_jobs_stmt = select(func.count(JobModel.id)).where(
        and_(JobModel.posted_by == current_user["id"], JobModel.is_active == True)
    )
    active_jobs = (await db.execute(active_jobs_stmt)).scalar() or 0
    
    # Total applications for employer's jobs
    apps_stmt = select(func.count(ApplicationModel.id)).join(JobModel, JobModel.id == ApplicationModel.job_id).where(
        JobModel.posted_by == current_user["id"]
    )
    total_applications = (await db.execute(apps_stmt)).scalar() or 0
    
    # Shortlisted applications
    shortlisted_stmt = select(func.count(ApplicationModel.id)).join(JobModel, JobModel.id == ApplicationModel.job_id).where(
        and_(JobModel.posted_by == current_user["id"], ApplicationModel.status == "shortlisted")
    )
    shortlisted = (await db.execute(shortlisted_stmt)).scalar() or 0
    
    return {
        "totalJobs": total_jobs,
        "activeJobs": active_jobs,
        "totalApplications": total_applications,
        "shortlisted": shortlisted
    }

@router.get("/jobs")
async def get_employer_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get jobs created by the employer"""
    if current_user.get("role") != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can access their jobs"
        )
    
    stmt = select(JobModel).where(JobModel.posted_by == current_user["id"]).order_by(JobModel.posted_date.desc())
    result = await db.execute(stmt)
    jobs_list = result.scalars().all()
    
    # Map to schema and add application count
    jobs_with_counts = []
    for job in jobs_list:
        app_count_stmt = select(func.count(ApplicationModel.id)).where(ApplicationModel.job_id == job.id)
        app_count = (await db.execute(app_count_stmt)).scalar() or 0
        
        # Merge model data into dict for return
        job_dict = {column.name: getattr(job, column.name) for column in job.__table__.columns}
        job_dict["application_count"] = app_count
        jobs_with_counts.append(job_dict)
    
    return jobs_with_counts

@router.get("/applications")
async def get_employer_applications(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get applications for the employer's jobs"""
    if current_user.get("role") != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can access their job applications"
        )
    
    stmt = select(ApplicationModel, JobModel.title, JobModel.company, UserModel.full_name, UserModel.email)\
        .join(JobModel, JobModel.id == ApplicationModel.job_id)\
        .join(UserModel, UserModel.id == ApplicationModel.user_id)\
        .where(JobModel.posted_by == current_user["id"])\
        .order_by(ApplicationModel.applied_at.desc())
    
    result = await db.execute(stmt)
    applications = []
    for app, job_title, company, applicant_name, applicant_email in result.all():
        app_dict = {column.name: getattr(app, column.name) for column in app.__table__.columns}
        app_dict["job_title"] = job_title
        app_dict["company"] = company
        app_dict["applicant_name"] = applicant_name
        app_dict["applicant_email"] = applicant_email
        applications.append(app_dict)
    
    return applications

@router.get("/activity")
async def get_employer_activity(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get recent activity for the employer"""
    if current_user.get("role") != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can access their activity"
        )
    
    activity = []
    
    # 1. Recent job postings
    jobs_stmt = select(JobModel).where(JobModel.posted_by == current_user["id"]).order_by(JobModel.posted_date.desc()).limit(10)
    jobs_res = await db.execute(jobs_stmt)
    for job in jobs_res.scalars().all():
        activity.append({
            "type": "job_posted",
            "title": job.title,
            "description": f"Job posted: {job.title}",
            "timestamp": job.posted_date,
            "icon": "plus"
        })
    
    # 2. Recent applications received & shortlist actions
    apps_stmt = select(ApplicationModel, JobModel.title, UserModel.full_name)\
        .join(JobModel, JobModel.id == ApplicationModel.job_id)\
        .join(UserModel, UserModel.id == ApplicationModel.user_id)\
        .where(JobModel.posted_by == current_user["id"])\
        .order_by(ApplicationModel.applied_at.desc()).limit(10)
    apps_res = await db.execute(apps_stmt)
    
    for app, job_title, applicant_name in apps_res.all():
        # Application received activity
        activity.append({
            "type": "application_received",
            "title": applicant_name,
            "description": f"{applicant_name} applied for {job_title}",
            "timestamp": app.applied_at,
            "icon": "user"
        })
        
        # Shortlisted activity (using updated_at as proxy for action time)
        if app.status == "shortlisted":
            activity.append({
                "type": "shortlisted",
                "title": applicant_name,
                "description": f"{applicant_name} shortlisted for {job_title}",
                "timestamp": app.updated_at or app.applied_at,
                "icon": "star"
            })
    
    # Sort by timestamp and return top 5
    activity.sort(key=lambda x: x["timestamp"], reverse=True)
    return activity[:5]
