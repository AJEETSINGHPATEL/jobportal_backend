from fastapi import APIRouter, HTTPException, status, Query
from app.models.job_alert import JobAlertCreate, JobAlertUpdate, JobAlert
from app.database.database import job_alerts_collection, users_collection, jobs_collection
from bson import ObjectId
from datetime import datetime
from typing import List
from pymongo import ReturnDocument

router = APIRouter(prefix="/api/job-alerts", tags=["Job Alerts"])

@router.post("/", response_model=JobAlert)
async def create_job_alert(alert: JobAlertCreate):
    try:
        # Check if user exists
        user = await users_collection.find_one({"_id": ObjectId(alert.user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if similar alert already exists for this user
        existing_alert = await job_alerts_collection.find_one({
            "user_id": alert.user_id,
            "search_params": alert.search_params
        })
        if existing_alert:
            raise HTTPException(status_code=400, detail="Job alert with these parameters already exists")
        
        # Convert to dict and add required fields
        alert_dict = alert.dict()
        alert_dict["created_at"] = datetime.now()
        alert_dict["updated_at"] = datetime.now()
        alert_dict["last_triggered"] = None
        alert_dict["matched_jobs_count"] = 0
        
        result = await job_alerts_collection.insert_one(alert_dict)
        alert_dict["id"] = str(result.inserted_id)
        del alert_dict["_id"]
        
        return JobAlert(**alert_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating job alert: {str(e)}")

@router.get("/{alert_id}", response_model=JobAlert)
async def get_job_alert(alert_id: str):
    try:
        alert = await job_alerts_collection.find_one({"_id": ObjectId(alert_id)})
        if not alert:
            raise HTTPException(status_code=404, detail="Job alert not found")
        
        alert["id"] = str(alert["_id"])
        del alert["_id"]
        
        # Get user details
        user = await users_collection.find_one({"_id": ObjectId(alert["user_id"])})
        if user:
            alert["user_name"] = user.get("full_name", "Unknown User")
        
        return JobAlert(**alert)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving job alert: {str(e)}")

@router.put("/{alert_id}", response_model=JobAlert)
async def update_job_alert(alert_id: str, alert_update: JobAlertUpdate):
    try:
        existing_alert = await job_alerts_collection.find_one({"_id": ObjectId(alert_id)})
        if not existing_alert:
            raise HTTPException(status_code=404, detail="Job alert not found")
        
        # Prepare update data
        update_data = alert_update.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.now()
        
        # Update the document and return the updated document
        updated_alert = await job_alerts_collection.find_one_and_update(
            {"_id": ObjectId(alert_id)},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER
        )
        
        if updated_alert:
            updated_alert["id"] = str(updated_alert["_id"])
            del updated_alert["_id"]
            
            # Get user details
            user = await users_collection.find_one({"_id": ObjectId(updated_alert["user_id"])})
            if user:
                updated_alert["user_name"] = user.get("full_name", "Unknown User")
            
            return JobAlert(**updated_alert)
        else:
            raise HTTPException(status_code=404, detail="Job alert not found after update")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating job alert: {str(e)}")

@router.delete("/{alert_id}")
async def delete_job_alert(alert_id: str):
    try:
        alert = await job_alerts_collection.find_one({"_id": ObjectId(alert_id)})
        if not alert:
            raise HTTPException(status_code=404, detail="Job alert not found")
        
        await job_alerts_collection.delete_one({"_id": ObjectId(alert_id)})
        return {"message": "Job alert deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting job alert: {str(e)}")

@router.get("/", response_model=List[JobAlert])
async def list_job_alerts(
    user_id: str = Query(None, description="Filter by user ID"),
    is_active: bool = Query(None, description="Filter by active status"),
    skip: int = 0,
    limit: int = 20
):
    try:
        query = {}
        if user_id:
            query["user_id"] = user_id
        if is_active is not None:
            query["is_active"] = is_active
        
        alerts = []
        cursor = job_alerts_collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        async for alert in cursor:
            alert_obj = {
                "user_id": alert.get("user_id", ""),
                "search_params": alert.get("search_params", {}),
                "title": alert.get("title", ""),
                "is_active": alert.get("is_active", True),
                "frequency": alert.get("frequency", "daily"),
                "email_notifications": alert.get("email_notifications", True),
                "push_notifications": alert.get("push_notifications", True),
                "id": str(alert["_id"]),
                "created_at": alert.get("created_at", datetime.now()),
                "updated_at": alert.get("updated_at", datetime.now()),
                "last_triggered": alert.get("last_triggered"),
                "matched_jobs_count": alert.get("matched_jobs_count", 0)
            }
            del alert["_id"]
            
            # Get user details
            user = await users_collection.find_one({"_id": ObjectId(alert_obj["user_id"])})
            if user:
                alert_obj["user_name"] = user.get("full_name", "Unknown User")
            
            alerts.append(JobAlert(**alert_obj))
        
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing job alerts: {str(e)}")

@router.get("/user/{user_id}/recent-jobs")
async def get_recent_jobs_for_alerts(user_id: str):
    """Get recent jobs that match user's saved alerts"""
    try:
        # Get user's active job alerts
        alerts = []
        cursor = job_alerts_collection.find({"user_id": user_id, "is_active": True})
        async for alert in cursor:
            alert["id"] = str(alert["_id"])
            del alert["_id"]
            alerts.append(alert)
        
        # For each alert, find matching jobs that were posted after the alert was last triggered
        matching_jobs = []
        for alert in alerts:
            search_params = alert.get("search_params", {})
            
            # Build query from search parameters
            query = {"is_active": True}
            
            # Add search term if present
            if search_params.get("search"):
                query["$or"] = [
                    {"title": {"$regex": search_params["search"], "$options": "i"}},
                    {"description": {"$regex": search_params["search"], "$options": "i"}},
                    {"skills": {"$in": [search_params["search"]]}}
                ]
            
            # Add location filter if present
            if search_params.get("location"):
                query["location"] = {"$regex": search_params["location"], "$options": "i"}
            
            # Add experience filter if present
            if search_params.get("experience_min"):
                query["experience_required"] = {"$regex": f"{search_params['experience_min']}.*", "$options": "i"}
            
            # Add salary filter if present
            if search_params.get("salary_min"):
                query["salary_min"] = {"$gte": search_params["salary_min"]}
            
            # Add job type filter if present
            if search_params.get("job_type"):
                query["job_type"] = search_params["job_type"]
            
            # Add work mode filter if present
            if search_params.get("work_mode"):
                query["work_mode"] = search_params["work_mode"]
            
            # Add skills filter if present
            if search_params.get("skills"):
                query["skills"] = {"$all": search_params["skills"]}
            
            # Only get jobs posted after last trigger (or last 7 days if never triggered)
            from datetime import timedelta
            if alert.get("last_triggered"):
                query["posted_at"] = {"$gte": alert["last_triggered"]}
            else:
                query["posted_at"] = {"$gte": datetime.now() - timedelta(days=7)}
            
            # Find matching jobs
            cursor = jobs_collection.find(query).sort("posted_at", -1)
            async for job in cursor:
                job["id"] = str(job["_id"])
                del job["_id"]
                
                # Get employer details
                if "posted_by" in job:
                    employer = await users_collection.find_one({"_id": ObjectId(job["posted_by"])})
                    if employer:
                        job["employer_name"] = employer.get("full_name", "Unknown Employer")
                
                # Get company details
                if "company_id" in job and job["company_id"]:
                    company = await companies_collection.find_one({"_id": ObjectId(job["company_id"])})
                    if company:
                        job["company"] = company.get("name", job.get("company", ""))
                
                job["matched_alert_id"] = alert["id"]
                job["matched_alert_title"] = alert["title"]
                matching_jobs.append(job)
        
        return matching_jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding matching jobs: {str(e)}")