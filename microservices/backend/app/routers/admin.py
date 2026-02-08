"""
Admin Endpoints
"""
__author__ = "Mohammad Saifan"

from fastapi import APIRouter, Depends, HTTPException, Query, status
import logging
import math

from app.database.database import get_db
from app.database.db_engine import MongoDBService
from app.models.db_models import Collections

logger = logging.getLogger(__name__)
router = APIRouter()


def check_permission(user_id: str) -> bool:
    """Check if user has permission"""
    if user_id != "admin":
        return False
    return True


@router.get("/admin/users")
async def get_all_users(user_id: str = Query(..., description="Admin user ID"), page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=100),
                        role: str = Query("all"), db = Depends(get_db("auth_service"))):
    """Get all users (Admin only)"""
    if not check_permission(user_id):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    skip = (page - 1) * limit
    
    user_service = MongoDBService(db, Collections.AUTH_SERVICE_USER_DATA)
    
    filter_query = {} if role == "all" else {"role": role}
    
    total = user_service.count(filter_query)
    users = user_service.get_all(skip=skip, limit=limit, filter_query=filter_query)
    
    user_list = [
        {
            "id": user.get("id"),
            "email": user.get("email"),
            "name": user.get("name"),
            "role": user.get("role"),
            "createdAt": user.get("created_at").isoformat() if user.get("created_at") else None
        }
        for user in users
    ]
    
    return {
        "users": user_list,
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1
    }


@router.patch("/admin/users/{target_user_id}")
async def update_user(target_user_id: str, user_id: str = Query(..., description="Admin user ID"), request: dict = None, db = Depends(get_db("auth_service"))):
    """Update user (Admin only)"""
    if not check_permission(user_id):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    user_service = MongoDBService(db, Collections.AUTH_SERVICE_USER_DATA)
    user = user_service.update(target_user_id, request)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    logger.info(f"User updated by admin: {target_user_id}")
    
    return {
        "success": True,
        "user": {
            "id": user.get("id"),
            "email": user.get("email"),
            "role": user.get("role")
        }
    }


@router.delete("/admin/users/{target_user_id}", status_code=204)
async def delete_user(target_user_id: str, user_id: str = Query(..., description="Admin user ID"), db = Depends(get_db("auth_service"))):
    """Delete user (Admin only)"""
    if not check_permission(user_id):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    user_service = MongoDBService(db, Collections.AUTH_SERVICE_USER_DATA)
    deleted = user_service.delete(target_user_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    
    logger.info(f"User deleted by admin: {target_user_id}")
    return None


@router.get("/admin/content")
async def get_all_content(user_id: str = Query(..., description="Admin user ID"), db = Depends(get_db())):
    """Get all content for moderation (Admin only)"""
    if not check_permission(user_id):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Get all listings pending review
    listing_service = MongoDBService(db, Collections.STORE_LISTINGS)
    listings = listing_service.find_many({"status": "pending_review"})
    
    content_list = [
        {
            "id": listing.get("id"),
            "title": listing.get("title"),
            "userId": listing.get("user_id"),
            "status": listing.get("status"),
            "createdAt": listing.get("created_at").isoformat() if listing.get("created_at") else None
        }
        for listing in listings
    ]
    
    return {"content": content_list, "total": len(content_list)}


@router.patch("/admin/listings/{listing_id}/status")
async def update_listing_status(listing_id: str, user_id: str = Query(..., description="Admin user ID"), request: dict = None, db = Depends(get_db)):
    """Approve/reject store listings (Admin only)"""
    if not check_permission(user_id):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    from datetime import datetime
    
    status_value = request.get("status")
    feedback = request.get("feedback", "")
    
    listing_service = MongoDBService(db, Collections.STORE_LISTINGS)
    
    update_data = {
        "status": status_value,
        "admin_feedback": feedback
    }
    
    if status_value == "published":
        update_data["published_at"] = datetime.utcnow()
    
    listing = listing_service.update(listing_id, update_data)
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    logger.info(f"Listing {listing_id} status updated to {status_value}")
    
    return {
        "success": True,
        "listingId": listing_id,
        "status": status_value
    }