"""
User Management Endpoints
"""

__author__ = "Mohammad Saifan"

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from typing import Optional
import logging
from datetime import datetime
import uuid

from app.database.database import get_db
from app.database.db_engine import MongoDBService
from app.models.db_models import Collections
from app.models.schemas import (
    UserProfileResponse,
    UserProfileUpdate,
    AvatarUploadResponse,
    UserPreferencesResponse,
    UserPreferencesUpdate,
    UserCreditsResponse,
    UserStatsResponse,
    UserActivityResponse,
    ActivityItem,
    ContinueListeningResponse,
    ContinueListeningItem,
    BookshelfResponse,
    BookshelfItem,
    UserSettingsResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/users/me", response_model=UserProfileResponse)
async def get_current_user_profile(user_id: str = Query(..., description="User ID"), db = Depends(get_db())):
    """Get current user profile"""
    #DEBUGMOE choose between auth_service or user_data
    user_service = MongoDBService(db, Collections.USER_DATA)
    user = user_service.get_by_id(user_id)
    
    if not user:
        db_func = get_db("auth_service")
        auth_db = db_func()
        auth_user_service = MongoDBService(auth_db, Collections.AUTH_SERVICE_USER_DATA)
        user = auth_user_service.get_by_id(user_id)
        
        # duplicate to userservice
        user = user_service.create(user)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    
    return UserProfileResponse(
        _id=str(user.get("_id") or ""),
        email=user.get("email") or "",
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        hashed_password=user.get("hashed_password"),
        is_active=user.get("is_active"),
        is_verified=user.get("is_verified"),
        auth_provider=user.get("auth_provider"),
        avatar_url=user.get("avatar_url"),
        role=user.get("role"),
        created_at=user.get("created_at").isoformat() if isinstance(user.get("created_at"), datetime) else None,
        updated_at=user.get("updated_at").isoformat() if isinstance(user.get("updated_at"), datetime) else None,
        last_login=user.get("last_login").isoformat() if isinstance(user.get("last_login"), datetime) else None
    )


@router.post("/users/me", response_model=UserProfileResponse)
async def update_user_profile(user_id: str = Query(..., description="User ID"), update_data: UserProfileResponse = None, db = Depends(get_db())):
    """Update user profile"""
    user_service = MongoDBService(db, Collections.USER_DATA)
    
    update_dict = update_data.model_dump(exclude_unset=True)
    user = user_service.update(user_id, update_dict)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserProfileResponse(
        _id=str(user.get("_id") or ""),
        email=user.get("email") or "",
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        hashed_password=user.get("hashed_password"),
        is_active=user.get("is_active"),
        is_verified=user.get("is_verified"),
        auth_provider=user.get("auth_provider"),
        avatar_url=user.get("avatar_url"),
        role=user.get("role"),
        created_at=user.get("created_at").isoformat() if isinstance(user.get("created_at"), datetime) else None,
        updated_at=user.get("updated_at").isoformat() if isinstance(user.get("updated_at"), datetime) else None,
        last_login=user.get("last_login").isoformat() if isinstance(user.get("last_login"), datetime) else None
    )


@router.post("/users/me/avatar", response_model=AvatarUploadResponse)
async def upload_user_avatar(user_id: str = Query(..., description="User ID"), file: UploadFile = File(...), db = Depends(get_db())):
    """Upload user avatar image"""
    # TODO: Upload to R2 storage....
    
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Mock avatar URL (replace with actual R2 upload)
    avatar_url = f"{file.filename}"
    
    # Update user avatar URL
    user_service = MongoDBService(db, Collections.USER_DATA)
    user_service.update(user_id, {"avatar_url": avatar_url})
    
    logger.info(f"Avatar uploaded for user {user_id}")
    
    return AvatarUploadResponse(avatar_url=avatar_url)


@router.delete("/users/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_account(user_id: str = Query(..., description="User ID"), db = Depends(get_db())):
    """Delete user account permanently"""
    user_service = MongoDBService(db, Collections.USER_DATA)
    
    deleted = user_service.delete(user_id)
    #TODO do we really want to delete a user info?
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    
    logger.info(f"User account deleted: {user_id}")
    return None


@router.patch("/users/me/preferences", response_model=UserPreferencesResponse)
async def update_user_preferences(user_id: str = Query(..., description="User ID"), preferences: UserPreferencesUpdate = None, db = Depends(get_db())):
    """Update user preferences"""
    # Get or create user preferences
    prefs_service = MongoDBService(db, Collections.USER_PREFERENCES)
    user_prefs = prefs_service.find_one({"user_id": user_id})
    
    if not user_prefs:
        # Create new preferences
        prefs_data = {
            "user_id": user_id,
            "email_notifications": True,
            "marketing_emails": False,
            "theme": "light",
            "language": "en",
            "autoplay": True,
            "playback_speed": 1.0
        }
        user_prefs = prefs_service.create(prefs_data)
    
    # Update preferences
    update_dict = preferences.model_dump(exclude_unset=True)
    if update_dict:
        user_prefs = prefs_service.update(user_prefs.get("_id"), update_dict)
    
    return UserPreferencesResponse(
        email_notifications=user_prefs.get("email_notifications"),
        marketing_emails=user_prefs.get("marketing_emails"),
        theme=user_prefs.get("theme"),
        language=user_prefs.get("language"),
        autoplay=user_prefs.get("autoplay"),
        playback_speed=user_prefs.get("playback_speed")
    )


@router.get("/users/me/credits", response_model=UserCreditsResponse)
async def get_user_credits(user_id: str = Query(..., description="User ID"), db = Depends(get_db())):
    """Get user's current credit balance"""
    credits_service = MongoDBService(db, Collections.USER_CREDITS)
    credits = credits_service.find_one({"user_id": user_id})
    
    if not credits:
        # Return default credits if not found
        cred_data = {
            "user_id": user_id,
            "credits": 0,
            "credits_used": 0,
            "credits_expiring": 0,
            "expiry_date": None
        }
        user_credits = credits_service.create(cred_data)
        
        return UserCreditsResponse(
            credits=0,
            credits_used=0,
            credits_expiring=0,
            expiry_date=None
        )
    
    return UserCreditsResponse(
        credits=credits.get("credits", 0),
        credits_used=credits.get("credits_used", 0),
        credits_expiring=credits.get("credits_expiring", 0),
        expiry_date=credits.get("expiry_date").isoformat() if credits.get("expiry_date") else None
    )


@router.get("/users/{target_user_id}/stats", response_model=UserStatsResponse)
async def get_user_stats(target_user_id: str, user_id: str = Query(..., description="Requesting user ID"), db = Depends(get_db())):
    """Get user statistics for dashboard"""
    # Verify user is accessing their own data or is admin
    if target_user_id != user_id:
        user_service = MongoDBService(db, Collections.USER_DATA)
        current_user = user_service.get_by_id(user_id)
        if not current_user or current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
    
    stats_service = MongoDBService(db, Collections.USER_STATS)
    stats = stats_service.find_one({"user_id": target_user_id})
    
    if not stats:
        # Return default stats if not found
        stats_data = {
            "user_id": user_id,
            "total_books": 0,
            "hours_listened": 0.0,
            "books_completed": 0,
            "favorite_genre": None
        }
        stats = stats_service.create(stats_data)
    
    return UserStatsResponse(
        total_books=stats.get("total_books", 0),
        hours_listened=stats.get("hours_listened", 0.0),
        books_completed=stats.get("books_completed", 0),
        favorite_genre=stats.get("favorite_genre")
    )


@router.get("/users/{target_user_id}/activity", response_model=UserActivityResponse)
async def get_user_activity(target_user_id: str, user_id: str = Query(..., description="Requesting user ID"), limit: int = 10, db = Depends(get_db())):
    """Get recent user activity"""
    # Verify user is accessing their own data
    if target_user_id != user_id:
        user_service = MongoDBService(db, Collections.USER_DATA)
        current_user = user_service.get_by_id(user_id)
        if not current_user or current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
    
    activity_service = MongoDBService(db, Collections.USER_ACTIVITY)
    activities = activity_service.find_many({"user_id": user_id}, limit=limit)
    if not activities:
        activity_data = {
            "user_id": user_id,
            "activity_type": "default",
            "title": "No activity",
            "hours_listened": 0.0,
            "book_id": "None"
        }
        activities = activity_service.create(activity_data)
    
    activities = [activities] if isinstance(activities, dict) else activities

    #TODO MOEDEBUG [I STOPPED HERE]
    activity_items = [
        ActivityItem(
            user_id=activity.get("user_id"),
            type=activity.get("activity_type"),
            title=activity.get("title"),
            timestamp=activity.get("updated_at").isoformat() if activity.get("updated_at") else "",
            book_id=activity.get("book_id")
        )
        for activity in activities
    ]
    
    return UserActivityResponse(activities=activity_items)


@router.get("/users/{target_user_id}/continue-listening", response_model=ContinueListeningResponse)
async def get_continue_listening(target_user_id: str, user_id: str = Query(..., description="Requesting user ID"), db = Depends(get_db())):
    """Get books user is currently listening to"""
    # Verify user is accessing their own data
    if target_user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get books with progress > 0 and < 1
    library_service = MongoDBService(db, Collections.USER_LIBRARY)
    library_items = library_service.collection.find_one({"user_id": user_id, "progress": {"$gt": 0, "$lt": 1}}).limit(10)
    if not library_items:
        library_load = {
            "user_id": user_id,
            "title": "None",
            "progress": 0.0,
            "last_played_at": None
        }
        library_service.create(library_load)
        library_items = [library_load]
    
    # Sort by last_played_at
    library_items = sorted(
        library_items,
        key=lambda x: x.get("last_played_at") or datetime.min,
        reverse=True
    )
    
    books = []
    book_service = MongoDBService(db, Collections.BOOKS)
    for item in library_items:
        book = book_service.get_by_id(item.get("book_id"))
        if book:
            books.append(
                ContinueListeningItem(
                    id=book.get("_id"),
                    title=book.get("title"),
                    progress=item.get("progress", 0.0),
                    last_played_at=item.get("last_played_at").isoformat() if item.get("last_played_at") else ""
                )
            )
    
    return ContinueListeningResponse(books=books)


@router.get("/users/{target_user_id}/bookshelf", response_model=BookshelfResponse)
async def get_user_bookshelf(target_user_id: str, user_id: str = Query(..., description="Requesting user ID"), db = Depends(get_db())):
    """Get user's saved/bookmarked books"""
    # Verify user is accessing their own data
    if target_user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    library_service = MongoDBService(db, Collections.USER_LIBRARY)
    library_items = library_service.find_one({"user_id": user_id})
    
    if not library_items:
        bookshelf_date = {
            "user_id": f"{user_id}",
            "title": "Empty Bookshelf",
            "added_at": datetime.now().isoformat()
        }
        library_items = library_service.create(bookshelf_date)
    
    library_items = [library_items] if isinstance(library_items, dict) else library_items
    
    # Sort by added_at
    library_items = sorted(
        library_items,
        key=lambda x: x.get("added_at") or datetime.min,
        reverse=True
    )

    books = []
    book_service = MongoDBService(db, Collections.BOOKS)
    if not book_service.find_one({"user_id": user_id}):
            book_data = {
                "user_id": user_id,
                "title": "Sample Book",
                "author": "Author Name",
                "duration": 0,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            book_service.create(book_data)
        
    for item in library_items:
        book = book_service.get_by_id(item.get("book_id"))
        if book:
            books.append(
                BookshelfItem(
                    id=book.get("_id"),
                    title=book.get("title"),
                    added_at=item.get("added_at").isoformat() if item.get("added_at") else ""
                )
            )
    
    return BookshelfResponse(books=books)


@router.get("/users/{target_user_id}/settings", response_model=UserSettingsResponse)
async def get_user_settings(target_user_id: str, user_id: str = Query(..., description="Requesting user ID"), db = Depends(get_db())):
    """Get user settings"""
    # Verify user is accessing their own data
    if target_user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    prefs_service = MongoDBService(db, Collections.USER_PREFERENCES)
    preferences = prefs_service.find_one({"user_id": user_id})
    
    if not preferences:
        # Return default settings
        preferences_date = {
            "user_id": user_id,
            "theme": "light",
            "language": "en",
            "autoplay": True,
            "playback_speed": 1.0
        }
        prefs_service.create(preferences_date)
        preferences =  prefs_service.find_one({"user_id": user_id})

    return UserSettingsResponse(
        theme=preferences.get("theme"),
        language=preferences.get("language"),
        autoplay=preferences.get("autoplay"),
        playback_speed=preferences.get("playback_speed")
    )