from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from app.models.notification import NotificationCreate, NotificationUpdate, Notification as NotificationSchema
from app.database.database import get_db
from app.database.models import Notification as NotificationModel
from app.utils.auth import get_current_user
from typing import List
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

@router.post("/", response_model=NotificationSchema)
async def create_notification(notification: NotificationCreate, db: AsyncSession = Depends(get_db)):
    try:
        db_notification = NotificationModel(
            id=str(uuid.uuid4()),
            **notification.model_dump(),
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.add(db_notification)
        await db.commit()
        await db.refresh(db_notification)
        return db_notification
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating notification: {str(e)}")

@router.get("/{notification_id}", response_model=NotificationSchema)
async def get_notification(notification_id: str, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(NotificationModel).where(NotificationModel.id == notification_id)
    result = await db.execute(stmt)
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    if notification.user_id != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    return notification

@router.put("/{notification_id}", response_model=NotificationSchema)
async def update_notification(
    notification_id: str, 
    notification_update: NotificationUpdate, 
    current_user: dict = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    stmt = select(NotificationModel).where(NotificationModel.id == notification_id)
    result = await db.execute(stmt)
    db_notification = result.scalar_one_or_none()
    
    if not db_notification:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    if db_notification.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    update_data = notification_update.model_dump(exclude_unset=True)
    if update_data.get("is_read") and not db_notification.is_read:
        db_notification.read_at = datetime.utcnow()
    
    for key, value in update_data.items():
        setattr(db_notification, key, value)
    
    await db.commit()
    await db.refresh(db_notification)
    return db_notification

@router.delete("/{notification_id}")
async def delete_notification(notification_id: str, token: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    current_user = token
    stmt = select(NotificationModel).where(NotificationModel.id == notification_id)
    result = await db.execute(stmt)
    db_notification = result.scalar_one_or_none()
    
    if not db_notification:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    if db_notification.user_id != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.delete(db_notification)
    await db.commit()
    return {"message": "Notification deleted successfully"}

@router.get("/user/{user_id}", response_model=List[NotificationSchema])
async def get_notifications_by_user(
    user_id: str, 
    skip: int = 0, 
    limit: int = 20, 
    token: str = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    current_user = token
    if current_user["id"] != user_id and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    stmt = select(NotificationModel).where(NotificationModel.user_id == user_id)\
        .order_by(NotificationModel.created_at.desc())\
        .offset(skip).limit(limit)
        
    result = await db.execute(stmt)
    return result.scalars().all()

@router.put("/mark-all-read/{user_id}")
async def mark_all_notifications_as_read(
    user_id: str, 
    token: str = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    current_user = token
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    stmt = update(NotificationModel)\
        .where(and_(NotificationModel.user_id == user_id, NotificationModel.is_read == False))\
        .values(is_read=True, read_at=datetime.utcnow())
        
    await db.execute(stmt)
    await db.commit()
    return {"message": "All notifications marked as read"}
