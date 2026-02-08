"""
Permissions & Access Control Endpoints
"""

__author__ = "Mohammad Saifan"

from fastapi import APIRouter, Depends, HTTPException, Query
import logging

from app.database.database import get_db
from app.database.db_engine import MongoDBService
from app.models.db_models import Collections

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/users/me/permissions")
async def get_user_permissions(user_id: str = Query(..., description="User ID"), db = Depends(get_db())):
    """Get current user's permissions and role"""
    user_service = MongoDBService(db, Collections.USER_DATA)
    user = user_service.get_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Define role-based permissions
    role_permissions = {
        "free": {
            "permissions": [""],
            "limits": {
                "idk": ""
            }
        },
        "premium": {
            "permissions": [""],
            "limits": {
                "idk": ""
            }
        },
        "publisher": {
            "permissions": [""],
            "limits": {
                "idk": ""
            }
        },
        "admin": {
            "permissions": [""],
            "limits": {
                "idk": ""
            }
        }
    }
    
    role_data = role_permissions.get(user.get("role"), role_permissions["free"])
    
    return {
        "role": user.get("role"),
        "tier": user.get("role"),
        "permissions": role_data["permissions"],
        "limits": role_data["limits"],
        "isAdmin": user.get("role") == "admin"
    }


@router.get("/users/me/usage")
async def get_user_usage(user_id: str = Query(..., description="User ID"), db = Depends(get_db())):
    """Get current usage stats against limits"""
    # Get user's library count
    library_service = MongoDBService(db, Collections.USER_LIBRARY)
    uploads = library_service.count({"user_id": user_id})
    
    # Get published books count
    listing_service = MongoDBService(db, Collections.STORE_LISTINGS)
    published_books = listing_service.count({
        "user_id": user_id,
        "status": "published"
    })
    
    # TODO: Calculate actual storage used
    storage_used = 0.0
    
    # TODO: Get connected devices count
    devices_connected = 1
    
    return {
        "uploads": uploads,
        "storageUsed": storage_used,
        "devicesConnected": devices_connected,
        "publishedBooks": published_books
    }


@router.get("/permissions/check")
async def check_permission(user_id: str = Query(..., description="User ID"), permission: str = Query(..., description="Permission to check"), db = Depends(get_db())):
    """Check if user has specific permission"""
    user_service = MongoDBService(db, Collections.USER_DATA)
    user = user_service.get_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Define role permissions
    role_permissions = {
        "free": [""],
        "premium": ["L"],
        "publisher": [""],
        "admin": [""]
    }
    
    user_permissions = role_permissions.get(user.get("role"), [])
    allowed = permission in user_permissions
    
    return {
        "allowed": allowed,
        "reason": None if allowed else f"User role '{user.get('role')}' does not have permission '{permission}'"
    }