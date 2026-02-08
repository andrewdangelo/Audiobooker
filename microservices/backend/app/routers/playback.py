"""
Playback & Progress Endpoints
"""

__author__ = "Mohammad Saifan"

from fastapi import APIRouter, Depends, HTTPException, Query
import logging
import uuid
from datetime import datetime

from app.database.database import get_db
from app.database.db_engine import MongoDBService
from app.models.db_models import Collections

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/audiobooks/{book_id}/audio")
async def get_audio_url(book_id: str, user_id: str = Query(..., description="User ID"), db = Depends(get_db())):
    """Get streaming audio URL"""
    book_service = MongoDBService(db, Collections.BOOKS)
    book = book_service.get_by_id(book_id)
    
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Check if user owns the book
    library_service = MongoDBService(db, Collections.USER_LIBRARY)
    library_item = library_service.find_one({
        "user_id": user_id,
        "book_id": book_id
    })
    
    if not library_item:
        raise HTTPException(status_code=403, detail="You don't own this book")
    
    return {
        "audioUrl": book.get("audio_url") or f"https://cloudflare/{book_id}.mp3",
        "format": "mp3",
        "duration": book.get("duration")
    }


@router.post("/audiobooks/{book_id}/progress")
async def save_progress(book_id: str, user_id: str = Query(..., description="User ID"), request: dict = None, db = Depends(get_db())):
    """Save playback position"""
    position = request.get("position")
    duration = request.get("duration")
    chapter_id = request.get("chapterId")
    
    library_service = MongoDBService(db, Collections.USER_LIBRARY)
    library_item = library_service.find_one({
        "user_id": user_id,
        "book_id": book_id
    })
    
    if not library_item:
        raise HTTPException(status_code=404, detail="Book not found in library")
    
    # Calculate progress
    progress = position / duration if duration > 0 else 0.0
    
    library_service.update(library_item.get("_id"), {
        "progress": progress,
        "last_played_at": datetime.utcnow()
    })
    
    logger.info(f"Progress saved for book {book_id}: {progress}")
    
    return {
        "success": True,
        "position": position,
        "progress": progress
    }


@router.get("/audiobooks/{book_id}/progress")
async def get_progress(book_id: str, user_id: str = Query(..., description="User ID"), db = Depends(get_db())):
    """Get saved playback position"""
    library_service = MongoDBService(db, Collections.USER_LIBRARY)
    library_item = library_service.find_one({
        "user_id": user_id,
        "book_id": book_id
    })
    
    if not library_item:
        raise HTTPException(status_code=404, detail="Book not found in library")
    
    book_service = MongoDBService(db, Collections.BOOKS)
    book = book_service.get_by_id(book_id)
    position = int(library_item.get("progress", 0) * book.get("duration")) if book else 0
    
    return {
        "position": position,
        "progress": library_item.get("progress", 0.0),
        "lastPlayedAt": library_item.get("last_played_at").isoformat() if library_item.get("last_played_at") else None
    }


@router.post("/audiobooks/{book_id}/bookmarks", status_code=201)
async def create_bookmark(book_id: str, user_id: str = Query(..., description="User ID"), request: dict = None, db = Depends(get_db())):
    """Create bookmark"""
    position = request.get("position")
    note = request.get("note", "")
    
    bookmark_service = MongoDBService(db, Collections.BOOKMARKS)
    bookmark_data = {
        "user_id": user_id,
        "book_id": book_id,
        "position": position,
        "note": note
    }
    
    bookmark = bookmark_service.create(bookmark_data)
    
    logger.info(f"Bookmark created for book {book_id}")
    
    return {
        "id": bookmark.get("_id"),
        "position": bookmark.get("position"),
        "note": bookmark.get("note"),
        "createdAt": bookmark.get("created_at").isoformat() if bookmark.get("created_at") else None
    }


@router.get("/audiobooks/{book_id}/bookmarks")
async def get_bookmarks(book_id: str, user_id: str = Query(..., description="User ID"), db = Depends(get_db())):
    """Get all bookmarks for audiobook"""
    bookmark_service = MongoDBService(db, Collections.BOOKMARKS)
    bookmarks = bookmark_service.find_many({
        "user_id": user_id,
        "book_id": book_id
    })
    
    # Sort by position
    bookmarks = sorted(bookmarks, key=lambda x: x.get("position", 0))
    
    bookmark_list = [
        {
            "id": bookmark.get("_id"),
            "position": bookmark.get("position"),
            "note": bookmark.get("note"),
            "createdAt": bookmark.get("created_at").isoformat() if bookmark.get("created_at") else None
        }
        for bookmark in bookmarks
    ]
    
    return {"bookmarks": bookmark_list}


@router.get("/audiobooks/{book_id}/chapters")
async def get_chapters(book_id: str, db = Depends(get_db())):
    """Get chapter information"""
    book_service = MongoDBService(db, Collections.BOOKS)
    book = book_service.get_by_id(book_id)
    
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    chapters = book.get("chapters", [])
    
    # Sort by chapter_number
    chapters = sorted(chapters, key=lambda x: x.get("chapter_number", 0))
    
    chapter_list = [
        {
            "id": ch.get("_id"),
            "title": ch.get("title"),
            "startTime": ch.get("start_time"),
            "duration": ch.get("duration"),
            "chapterNumber": ch.get("chapter_number")
        }
        for ch in chapters
    ]
    
    return {"chapters": chapter_list}


@router.post("/audiobooks/{book_id}/complete")
async def mark_complete(book_id: str, user_id: str = Query(..., description="User ID"), db = Depends(get_db())):
    """Mark audiobook as completed"""
    library_service = MongoDBService(db, Collections.USER_LIBRARY)
    library_item = library_service.find_one({
        "user_id": user_id,
        "book_id": book_id
    })
    
    if not library_item:
        raise HTTPException(status_code=404, detail="Book not found in library")
    
    library_service.update(library_item.get("_id"), {
        "completed": True,
        "progress": 1.0
    })
    
    # Update user stats
    stats_service = MongoDBService(db, Collections.USER_STATS)
    stats = stats_service.find_one({"user_id": user_id})
    
    if stats:
        new_completed = stats.get("books_completed", 0) + 1
        stats_service.update(stats.get("_id"), {"books_completed": new_completed})
    
    # Log activity
    book_service = MongoDBService(db, Collections.BOOKS)
    book = book_service.get_by_id(book_id)
    
    activity_service = MongoDBService(db, Collections.USER_ACTIVITY)
    activity_data = {
        "user_id": user_id,
        "activity_type": "completed",
        "book_id": book_id,
        "title": book.get("title") if book else "Unknown"
    }
    activity_service.create(activity_data)
    
    logger.info(f"Book marked as complete: {book_id}")
    
    return {"success": True, "message": "Book marked as completed"}