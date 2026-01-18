from fastapi import APIRouter, HTTPException
from app.models.notification import NotificationCreate, NotificationUpdate, Notification
from app.database.database import notifications_collection
from typing import List
from bson import ObjectId
from datetime import datetime

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

@router.post("/", response_model=Notification)
async def create_notification(notification: NotificationCreate):
    notification_dict = notification.dict()
    notification_dict["is_read"] = False
    result = await notifications_collection.insert_one(notification_dict)
    notification_dict["id"] = str(result.inserted_id)
    return Notification(**notification_dict)

@router.get("/{notification_id}", response_model=Notification)
async def get_notification(notification_id: str):
    notification = await notifications_collection.find_one({"_id": ObjectId(notification_id)})
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification["id"] = str(notification["_id"])
    return Notification(**notification)

@router.put("/{notification_id}", response_model=Notification)
async def update_notification(notification_id: str, notification_update: NotificationUpdate):
    notification = await notifications_collection.find_one({"_id": ObjectId(notification_id)})
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    update_data = notification_update.dict(exclude_unset=True)
    if "is_read" in update_data and update_data["is_read"]:
        update_data["read_at"] = datetime.now()
    
    updated_notification = await notifications_collection.update_one(
        {"_id": ObjectId(notification_id)}, 
        {"$set": update_data}
    )
    
    if updated_notification.modified_count == 0:
        raise HTTPException(status_code=400, detail="Notification could not be updated")
    
    updated_notification = await notifications_collection.find_one({"_id": ObjectId(notification_id)})
    updated_notification["id"] = str(updated_notification["_id"])
    return Notification(**updated_notification)

@router.delete("/{notification_id}")
async def delete_notification(notification_id: str):
    notification = await notifications_collection.find_one({"_id": ObjectId(notification_id)})
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    await notifications_collection.delete_one({"_id": ObjectId(notification_id)})
    return {"message": "Notification deleted successfully"}

@router.get("/user/{user_id}", response_model=List[Notification])
async def get_notifications_by_user(user_id: str, skip: int = 0, limit: int = 20):
    notifications = []
    cursor = notifications_collection.find({"user_id": user_id}).skip(skip).limit(limit)
    async for notification in cursor:
        notification["id"] = str(notification["_id"])
        notifications.append(Notification(**notification))
    return notifications

@router.put("/mark-all-read/{user_id}")
async def mark_all_notifications_as_read(user_id: str):
    await notifications_collection.update_many(
        {"user_id": user_id, "is_read": False},
        {"$set": {"is_read": True, "read_at": datetime.now()}}
    )
    return {"message": "All notifications marked as read"}