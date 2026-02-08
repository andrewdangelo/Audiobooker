"""
Notifications Endpoints
"""
__author__ = "Mohammad Saifan"

from fastapi import APIRouter, Depends, HTTPException, Query
import logging
import uuid

from app.database.database import get_db
from app.database.db_engine import MongoDBService
from app.models.db_models import Collections

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/notifications")
async def get_notifications(user_id: str = Query(..., description="User ID"), unread: bool = Query(False, description="Only unread notifications"),
                            limit: int = Query(10, ge=1, le=50), db = Depends(get_db())):
    """Get user notifications"""
    notification_service = MongoDBService(db, Collections.NOTIFICATIONS)
    
    filter_query = {"user_id": user_id}
    if unread:
        filter_query["read"] = False
    
    notifications = notification_service.find_many(filter_query, limit=limit)
    
    # Sort by created_at
    notifications = sorted(
        notifications,
        key=lambda x: x.get("created_at", ""),
        reverse=True
    )
    
    unread_count = notification_service.count({
        "user_id": user_id,
        "read": False
    })
    
    notification_list = [
        {
            "id": notif.get("_id"),
            "type": notif.get("notification_type"),
            "title": notif.get("title"),
            "message": notif.get("message"),
            "read": notif.get("read", False),
            "createdAt": notif.get("created_at").isoformat() if notif.get("created_at") else None
        }
        for notif in notifications
    ]
    
    return {
        "notifications": notification_list,
        "unreadCount": unread_count
    }


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user_id: str = Query(..., description="User ID"), db = Depends(get_db())):
    """Mark notification as read"""
    notification_service = MongoDBService(db, Collections.NOTIFICATIONS)
    notification = notification_service.find_one({
        "user_id": user_id,
        "id": notification_id
    })
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification_service.update(notification_id, {"read": True})
    
    return {"success": True}


@router.post("/notifications/mark-all-read")
async def mark_all_read(user_id: str = Query(..., description="User ID"), db = Depends(get_db())):
    """Mark all notifications as read"""
    notification_service = MongoDBService(db, Collections.NOTIFICATIONS)
    updated = notification_service.update_many(
        {"user_id": user_id, "read": False},
        {"read": True}
    )
    
    logger.info(f"All notifications marked as read for user {user_id}")
    
    return {"success": True}