"""
Search & Discovery Endpoints
"""

__author__ = "Mohammad Saifan"

from fastapi import APIRouter, Depends, HTTPException, Query
import logging

from app.database.database import get_db
from app.database.db_engine import MongoDBService
from app.models.db_models import Collections

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/search")
async def search_audiobooks(user_id: str = Query(..., description="User ID"), q: str = Query(..., description="Search query"), 
                            scope: str = Query("all", regex="^(all|library|store)$"), limit: int = Query(20, ge=1, le=100), db = Depends(get_db())):
    """Search audiobooks across library and store"""
    results = []
    
    book_service = MongoDBService(db, Collections.BOOKS)
    
    # Search in store
    if scope in ["all", "store"]:
        # MongoDB text search (requires text index on title and author fields)
        # For now, using regex search
        store_books = book_service.collection.find({
            "is_store_item": True,
            "$or": [
                {"title": {"$regex": q, "$options": "i"}},
                {"author": {"$regex": q, "$options": "i"}}
            ]
        }).limit(limit)
        
        for book in store_books:
            results.append({
                "id": book.get("_id"),
                "title": book.get("title"),
                "author": book.get("author"),
                "type": "store",
                "coverImage": book.get("cover_image_url")
            })
    
    # Search in user's library
    if scope in ["all", "library"]:
        library_service = MongoDBService(db, Collections.USER_LIBRARY)
        library_items = library_service.find_many({"user_id": user_id})
        
        book_ids = [item.get("book_id") for item in library_items]
        
        if book_ids:
            library_books = book_service.collection.find({
                "id": {"$in": book_ids},
                "$or": [
                    {"title": {"$regex": q, "$options": "i"}},
                    {"author": {"$regex": q, "$options": "i"}}
                ]
            }).limit(limit)
            
            for book in library_books:
                results.append({
                    "id": book.get("_id"),
                    "title": book.get("title"),
                    "author": book.get("author"),
                    "type": "library",
                    "coverImage": book.get("cover_image_url")
                })
    
    return {
        "results": results[:limit],
        "total": len(results)
    }


@router.get("/recommendations")
async def get_recommendations(user_id: str = Query(..., description="User ID"), db = Depends(get_db())):
    """Get personalized audiobook recommendations"""
    # Get user's stats to determine favorite genre
    stats_service = MongoDBService(db, Collections.USER_STATS)
    stats = stats_service.find_one({"user_id": user_id})
    
    favorite_genre = stats.get("favorite_genre") if stats else None
    
    # Get recommendations based on favorite genre
    book_service = MongoDBService(db, Collections.BOOKS)
    
    filter_query = {"is_store_item": True}
    if favorite_genre:
        filter_query["genre"] = favorite_genre
    
    books = book_service.find_many(filter_query, limit=10)
    
    # Sort by rating
    books = sorted(books, key=lambda x: x.get("rating", 0), reverse=True)
    
    recommendations = [
        {
            "id": book.get("_id"),
            "title": book.get("title"),
            "author": book.get("author"),
            "coverImage": book.get("cover_image_url"),
            "reason": f"Based on your interest in {favorite_genre}" if favorite_genre else "Popular in the store"
        }
        for book in books
    ]
    
    return {"recommendations": recommendations}