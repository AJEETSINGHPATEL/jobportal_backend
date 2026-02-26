from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete, desc
from app.database.database import get_db
from app.database.models import JobAlert as JobAlertModel, User as UserModel, Job as JobModel, Company as CompanyModel
from app.models.job_alert import JobAlertCreate, JobAlertUpdate, JobAlert as JobAlertSchema
from datetime import datetime, timedelta
from typing import List
import uuid

router = APIRouter(prefix="/api/job-alerts", tags=["Job Alerts"])

@router.post("/", response_model=JobAlertSchema)
async def create_job_alert(
    alert: JobAlertCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        # Check if user exists
        user_stmt = select(UserModel).where(UserModel.id == alert.user_id)
        user = (await db.execute(user_stmt)).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if similar alert already exists for this user
        existing_stmt = select(JobAlertModel).where(
            and_(JobAlertModel.user_id == alert.user_id, JobAlertModel.title == alert.title)
        )
        existing_alert = (await db.execute(existing_stmt)).scalar_one_or_none()
        if existing_alert:
            raise HTTPException(status_code=400, detail="Job alert with this title already exists")
        
        # Create alert
        alert_db = JobAlertModel(
            id=str(uuid.uuid4()),
            user_id=alert.user_id,
            title=alert.title,
            search_params=alert.search_params,
            frequency=alert.frequency,
            is_active=alert.is_active,
            email_notifications=alert.email_notifications,
            push_notifications=alert.push_notifications,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(alert_db)
        await db.commit()
        await db.refresh(alert_db)
        
        # Add user name for response
        alert_db.user_name = user.full_name
        
        return alert_db
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating job alert: {str(e)}")

@router.get("/{alert_id}", response_model=JobAlertSchema)
async def get_job_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(JobAlertModel, UserModel.full_name)\
            .join(UserModel, UserModel.id == JobAlertModel.user_id)\
            .where(JobAlertModel.id == alert_id)
        
        result = await db.execute(stmt)
        res = result.first()
        if not res:
            raise HTTPException(status_code=404, detail="Job alert not found")
        
        alert, user_name = res
        alert.user_name = user_name
        return alert
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving job alert: {str(e)}")

@router.put("/{alert_id}", response_model=JobAlertSchema)
async def update_job_alert(
    alert_id: str, 
    alert_update: JobAlertUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(JobAlertModel).where(JobAlertModel.id == alert_id)
        alert = (await db.execute(stmt)).scalar_one_or_none()
        if not alert:
            raise HTTPException(status_code=404, detail="Job alert not found")
        
        update_data = alert_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(alert, key, value)
        
        alert.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(alert)
        
        # Get user name for response
        user_stmt = select(UserModel.full_name).where(UserModel.id == alert.user_id)
        user_name = (await db.execute(user_stmt)).scalar()
        alert.user_name = user_name
        
        return alert
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating job alert: {str(e)}")

@router.delete("/{alert_id}")
async def delete_job_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(JobAlertModel).where(JobAlertModel.id == alert_id)
        alert = (await db.execute(stmt)).scalar_one_or_none()
        if not alert:
            raise HTTPException(status_code=404, detail="Job alert not found")
        
        await db.delete(alert)
        await db.commit()
        return {"message": "Job alert deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting job alert: {str(e)}")

@router.get("/", response_model=List[JobAlertSchema])
async def list_job_alerts(
    user_id: str = Query(None),
    is_active: bool = Query(None),
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(JobAlertModel, UserModel.full_name)\
            .join(UserModel, UserModel.id == JobAlertModel.user_id)
            
        if user_id:
            stmt = stmt.where(JobAlertModel.user_id == user_id)
        if is_active is not None:
            stmt = stmt.where(JobAlertModel.is_active == is_active)
        
        stmt = stmt.order_by(desc(JobAlertModel.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(stmt)
        alerts = []
        for alert, user_name in result.all():
            alert.user_name = user_name
            alerts.append(alert)
        
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing job alerts: {str(e)}")

@router.get("/user/{user_id}/recent-jobs")
async def get_recent_jobs_for_alerts(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get recent jobs that match user's saved alerts"""
    try:
        # Get user's active job alerts
        stmt = select(JobAlertModel).where(and_(JobAlertModel.user_id == user_id, JobAlertModel.is_active == True))
        result = await db.execute(stmt)
        alerts = result.scalars().all()
        
        matching_jobs = []
        for alert in alerts:
            search_params = alert.search_params or {}
            
            # Build query from search parameters
            job_stmt = select(JobModel, CompanyModel.name, UserModel.full_name)\
                .outerjoin(CompanyModel, CompanyModel.id == JobModel.company_id)\
                .outerjoin(UserModel, UserModel.id == JobModel.posted_by)\
                .where(JobModel.is_active == True)
            
            # Add search term filters
            if search_params.get("search"):
                search = search_params["search"]
                job_stmt = job_stmt.where(or_(
                    JobModel.title.ilike(f"%{search}%"),
                    JobModel.description.ilike(f"%{search}%"),
                    JobModel.skills.contains([search])
                ))
            
            # Add other filters
            if search_params.get("location"):
                job_stmt = job_stmt.where(JobModel.location.ilike(f"%{search_params['location']}%"))
            
            if search_params.get("experience_min"):
                # Simplified experience filter
                job_stmt = job_stmt.where(JobModel.experience_required.ilike(f"{search_params['experience_min']}%"))
            
            if search_params.get("salary_min"):
                job_stmt = job_stmt.where(JobModel.salary_min >= search_params["salary_min"])
            
            if search_params.get("job_type"):
                job_stmt = job_stmt.where(JobModel.job_type == search_params["job_type"])
            
            if search_params.get("work_mode"):
                job_stmt = job_stmt.where(JobModel.work_mode == search_params["work_mode"])
            
            if search_params.get("skills"):
                job_stmt = job_stmt.where(JobModel.skills.contains(search_params["skills"]))
            
            # Timestamp filter (using posted_at as renamed in Job model)
            since = alert.last_triggered or (datetime.utcnow() - timedelta(days=7))
            job_stmt = job_stmt.where(JobModel.posted_at >= since)
            
            job_stmt = job_stmt.order_by(desc(JobModel.posted_at))
            
            jobs_res = await db.execute(job_stmt)
            for job, company_name, employer_name in jobs_res.all():
                job_dict = {column.name: getattr(job, column.name) for column in job.__table__.columns}
                job_dict["company"] = company_name or job.company
                job_dict["employer_name"] = employer_name
                job_dict["matched_alert_id"] = alert.id
                job_dict["matched_alert_title"] = alert.title
                matching_jobs.append(job_dict)
        
        # Deduplicate jobs by id if they matched multiple alerts
        unique_jobs = {}
        for job in matching_jobs:
            if job["id"] not in unique_jobs:
                unique_jobs[job["id"]] = job
        
        return list(unique_jobs.values())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding matching jobs: {str(e)}")
