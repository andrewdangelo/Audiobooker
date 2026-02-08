"""
Book Library and Store Endpoints
"""

__author__ = "Mohammad Saifan"

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import logging
import uuid
import math

from app.database.database import get_db
from app.database.db_engine import MongoDBService
from app.models.db_models import Collections
from app.models.schemas import (
    BookListResponse,
    BookBasic,
    BookDetailed,
    ChapterInfo,
    BookCreateRequest,
    BookUpdateRequest,
    StoreCatalogResponse,
    StoreBookBasic,
    StoreBookDetailed, 
    PurchaseResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============== Library Endpoints ==============

@router.get("/audiobooks", response_model=BookListResponse)
async def get_user_audiobooks(user_id: str = Query(..., description="User ID"), page: int = Query(1, ge=1), 
                            limit: int = Query(20, ge=1, le=100), sort: str = Query("recent", regex="^(recent|title|author)$"), db = Depends(get_db())):
    """Get user's audiobook library with pagination"""
    skip = (page - 1) * limit
    
    # Get user's library items
    library_service = MongoDBService(db, Collections.USER_LIBRARY)
    library_items = library_service.find_many(
        {"user_id": user_id},
        skip=skip,
        limit=limit
    )
    
    # Sort by last_played_at if sort is "recent" do by title, author later #TODO
    if sort == "recent":
        library_items = sorted(
            library_items,
            key=lambda x: x.get("last_played_at") or "",
            reverse=True
        )
    
    total = library_service.count({"user_id": user_id})
    
    # Get book details
    book_service = MongoDBService(db, Collections.BOOKS)
    books = []
    for item in library_items:
        book = book_service.get_by_id(item.get("book_id"))
        if book:
            books.append(
                BookBasic(
                    id=book.get("_id"),
                    title=book.get("title"),
                    author=book.get("author"),
                    duration=book.get("duration"),
                    cover_image_url=book.get("cover_image_url"),
                    progress=item.get("progress", 0.0)
                )
            )
    
    pages = math.ceil(total / limit) if total > 0 else 1
    
    return BookListResponse(
        books=books,
        total=total,
        page=page,
        pages=pages
    )


@router.get("/audiobooks/{book_id}", response_model=BookDetailed)
async def get_audiobook_details(book_id: str, user_id: str = Query(..., description="User ID"), db = Depends(get_db())):
    """Get detailed audiobook information"""
    book_service = MongoDBService(db, Collections.BOOKS)
    book = book_service.get_by_id(book_id)
    
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Get user's progress
    library_service = MongoDBService(db, Collections.USER_LIBRARY)
    library_item = library_service.find_one({
        "user_id": user_id,
        "book_id": book_id
    })
    
    progress = library_item.get("progress", 0.0) if library_item else 0.0
    
    # Get chapters from embedded document
    chapters = book.get("chapters", [])
    chapter_list = [
        ChapterInfo(
            id=ch.get("_id"),
            title=ch.get("title"),
            start_time=ch.get("start_time"),
            duration=ch.get("duration"),
            chapter_number=ch.get("chapter_number")
        )
        for ch in chapters
    ]
    
    return BookDetailed(
        id=book.get("_id"),
        title=book.get("title"),
        author=book.get("author"),
        narrator=book.get("narrator"),
        duration=book.get("duration"),
        chapters=chapter_list,
        cover_image_url=book.get("cover_image_url"),
        audio_url=book.get("audio_url"),
        progress=progress,
        description=book.get("description")
    )


@router.post("/audiobooks", status_code=201)
async def create_audiobook(user_id: str = Query(..., description="User ID"), request: BookCreateRequest = None, db = Depends(get_db())):
    """Create new audiobook from upload"""
    # TODO: Implement book creation from file upload
    
    book_id = str(uuid.uuid4())
    
    # Create book record
    book_service = MongoDBService(db, Collections.BOOKS)
    book_data = {
        "user_id": user_id,
        "title": request.title,
        "author": "Unknown",  #TODO Extract from metadata
        "duration": 0,  #TODO Calculate from tts audio file
        "is_store_item": False,
        "chapters": []
    }
    book_service.create(book_data)
    
    # Add to user's library
    library_service = MongoDBService(db, Collections.USER_LIBRARY)
    library_data = {
        "user_id": user_id,
        "book_id": book_id,
        "progress": 0.0
    }
    library_service.create(library_data)
    
    logger.info(f"Book created: {book_id}")
    
    return {"id": book_id, "title": request.title}


@router.patch("/audiobooks/{book_id}", response_model=BookDetailed)
async def update_audiobook(book_id: str, user_id: str = Query(..., description="User ID"), update_data: BookUpdateRequest = None, db = Depends(get_db())):
    """Update audiobook metadata"""
    book_service = MongoDBService(db, Collections.BOOKS)
    
    update_dict = update_data.model_dump(exclude_unset=True)
    book = book_service.update(book_id, update_dict)
    
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Get chapters
    chapters = book.get("chapters", [])
    chapter_list = [
        ChapterInfo(
            id=ch.get("_id"),
            title=ch.get("title"),
            start_time=ch.get("start_time"),
            duration=ch.get("duration"),
            chapter_number=ch.get("chapter_number")
        )
        for ch in chapters
    ]
    
    return BookDetailed(
        id=book.get("_id"),
        title=book.get("title"),
        author=book.get("author"),
        narrator=book.get("narrator"),
        duration=book.get("duration"),
        chapters=chapter_list,
        cover_image_url=book.get("cover_image_url"),
        audio_url=book.get("audio_url"),
        progress=0.0,
        description=book.get("description")
    )


@router.delete("/audiobooks/{book_id}", status_code=204)
async def delete_audiobook(book_id: str, user_id: str = Query(..., description="User ID"), db = Depends(get_db())):
    """Delete audiobook from library"""
    # Delete from user's library
    library_service = MongoDBService(db, Collections.USER_LIBRARY)
    deleted = library_service.delete_many({
        "user_id": user_id,
        "book_id": book_id
    })
    
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Book not found in library")
    
    logger.info(f"Book removed from library: {book_id}")
    return None


# ============== Store Endpoints ==============

@router.get("/store/catalog", response_model=StoreCatalogResponse)
async def get_store_catalog(genre: Optional[str] = None, sort: str = Query("popular", regex="^(popular|recent|rating)$"), 
                                    page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), db = Depends(get_db())):
    """Get all audiobooks available for purchase"""
    skip = (page - 1) * limit
    
    # Build filter query
    filter_query = {"is_store_item": True}
    if genre:
        filter_query["genre"] = genre
    
    book_service = MongoDBService(db, Collections.BOOKS)
    books = book_service.get_all(skip=skip, limit=limit, filter_query=filter_query)
    
    # Sort results
    if sort == "popular":
        books = sorted(books, key=lambda x: x.get("review_count", 0), reverse=True)
    elif sort == "recent":
        books = sorted(books, key=lambda x: x.get("created_at", ""), reverse=True)
    elif sort == "rating":
        books = sorted(books, key=lambda x: x.get("rating", 0), reverse=True)
    
    total = book_service.count(filter_query)
    
    book_list = [
        StoreBookBasic(
            id=book.get("_id"),
            title=book.get("title"),
            author=book.get("author"),
            price=book.get("price"),
            credits=book.get("credits_required", 1),
            genre=book.get("genre"),
            rating=book.get("rating", 0.0),
            cover_image_url=book.get("cover_image_url")
        )
        for book in books
    ]
    
    return StoreCatalogResponse(
        books=book_list,
        total=total,
        page=page
    )


@router.get("/store/books/{book_id}", response_model=StoreBookDetailed)
async def get_store_book_details(book_id: str, db = Depends(get_db())):
    """Get detailed store book information"""
    book_service = MongoDBService(db, Collections.BOOKS)
    book = book_service.find_one({
        "_id": book_id,
        "is_store_item": True
    })
    
    if not book:
        raise HTTPException(status_code=404, detail="Store book not found")
    
    # Get chapters
    chapters = book.get("chapters", [])
    chapter_list = [
        ChapterInfo(
            id=ch.get("_id"),
            title=ch.get("title"),
            start_time=ch.get("start_time"),
            duration=ch.get("duration"),
            chapter_number=ch.get("chapter_number")
        )
        for ch in chapters
    ]
    
    return StoreBookDetailed(
        id=book.get("_id"),
        title=book.get("title"),
        author=book.get("author"),
        narrator=book.get("narrator"),
        description=book.get("description"),
        synopsis=book.get("synopsis"),
        duration=book.get("duration"),
        chapters=chapter_list,
        price=book.get("price"),
        credits=book.get("credits_required", 1),
        genre=book.get("genre"),
        categories=book.get("categories"),
        rating=book.get("rating", 0.0),
        review_count=book.get("review_count", 0),
        sample_audio_url=book.get("sample_audio_url"),
        cover_image_url=book.get("cover_image_url")
    )


@router.get("/store/featured", response_model=StoreCatalogResponse)
async def get_featured_books(db = Depends(get_db())):
    """Get featured audiobooks for store homepage"""
    book_service = MongoDBService(db, Collections.BOOKS)
    books = book_service.find_many(
        {"is_store_item": True, "rating": {"$gte": 4.5}},
        limit=20
    )
    
    # Sort by rating
    books = sorted(books, key=lambda x: x.get("rating", 0), reverse=True)
    
    book_list = [
        StoreBookBasic(
            id=book.get("_id"),
            title=book.get("title"),
            author=book.get("author"),
            price=book.get("price"),
            credits=book.get("credits_required", 1),
            genre=book.get("genre"),
            rating=book.get("rating", 0.0),
            cover_image_url=book.get("cover_image_url")
        )
        for book in books
    ]
    
    return StoreCatalogResponse(
        books=book_list,
        total=len(book_list),
        page=1
    )


@router.get("/store/new-releases", response_model=StoreCatalogResponse)
async def get_new_releases(db = Depends(get_db())):
    """Get newest audiobook releases"""
    book_service = MongoDBService(db, Collections.BOOKS)
    books = book_service.find_many(
        {"is_store_item": True},
        limit=20
    )
    
    # Sort by created_at
    books = sorted(books, key=lambda x: x.get("created_at", ""), reverse=True)
    
    book_list = [
        StoreBookBasic(
            id=book.get("_id"),
            title=book.get("title"),
            author=book.get("author"),
            price=book.get("price"),
            credits=book.get("credits_required", 1),
            genre=book.get("genre"),
            rating=book.get("rating", 0.0),
            cover_image_url=book.get("cover_image_url")
        )
        for book in books
    ]
    
    return StoreCatalogResponse(
        books=book_list,
        total=len(book_list),
        page=1
    )


@router.get("/store/bestsellers", response_model=StoreCatalogResponse)
async def get_bestsellers(db = Depends(get_db())):
    """Get bestselling audiobooks"""
    book_service = MongoDBService(db, Collections.BOOKS)
    books = book_service.find_many(
        {"is_store_item": True},
        limit=20
    )
    
    # Sort by review_count
    books = sorted(books, key=lambda x: x.get("review_count", 0), reverse=True)
    
    book_list = [
        StoreBookBasic(
            id=book.get("_id"),
            title=book.get("title"),
            author=book.get("author"),
            price=book.get("price"),
            credits=book.get("credits_required", 1),
            genre=book.get("genre"),
            rating=book.get("rating", 0.0),
            cover_image_url=book.get("cover_image_url")
        )
        for book in books
    ]
    
    return StoreCatalogResponse(
        books=book_list,
        total=len(book_list),
        page=1
    )


@router.get("/store/books/{book_id}/related", response_model=StoreCatalogResponse)
async def get_related_books(book_id: str, db = Depends(get_db())):
    """Get related/recommended audiobooks"""
    book_service = MongoDBService(db, Collections.BOOKS)
    source_book = book_service.get_by_id(book_id)
    
    if not source_book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Get related books by genre
    books = book_service.find_many(
        {
            "is_store_item": True,
            "genre": source_book.get("genre"),
            "_id": {"$ne": book_id}
        },
        limit=10
    )
    
    # Sort by rating
    books = sorted(books, key=lambda x: x.get("rating", 0), reverse=True)
    
    book_list = [
        StoreBookBasic(
            id=book.get("_id"),
            title=book.get("title"),
            author=book.get("author"),
            price=book.get("price"),
            credits=book.get("credits_required", 1),
            genre=book.get("genre"),
            rating=book.get("rating", 0.0),
            cover_image_url=book.get("cover_image_url")
        )
        for book in books
    ]
    
    return StoreCatalogResponse(
        books=book_list,
        total=len(book_list),
        page=1
    )


@router.post("/store/purchase")
async def purchase_book(user_id: str = Query(..., description="User ID"), purchase_data: PurchaseResponse = None, db = Depends(get_db())):
    """Purchase a store audiobook"""
    book_id = purchase_data.get("bookId")
    payment_method = purchase_data.get("paymentMethod")
    
    # Get the book
    book_service = MongoDBService(db, Collections.BOOKS)
    book = book_service.find_one({
        "user_id": user_id,
    })
    
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Check if user already owns it
    library_service = MongoDBService(db, Collections.USER_LIBRARY)
    existing = library_service.find_one({
        "user_id": user_id,
        "book_id": book_id
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="You already own this book")
    
    # Handle payment based on method
    if payment_method == "credits":
        # Check user credits
        credits_service = MongoDBService(db, Collections.USER_CREDITS)
        user_credits = credits_service.find_one({"user_id": user_id})
        
        if not user_credits or user_credits.get("credits", 0) < book.get("credits_required", 1):
            raise HTTPException(status_code=400, detail="Insufficient credits")
        
        # Deduct credits
        new_credits = user_credits.get("credits") - book.get("credits_required", 1)
        new_credits_used = user_credits.get("credits_used", 0) + book.get("credits_required", 1)
        credits_service.update(user_credits.get("_id"), {
            "credits": new_credits,
            "credits_used": new_credits_used
        })
    
    # Add to user's library
    library_data = {
        "user_id": user_id,
        "book_id": book_id,
        "progress": 0.0
    }
    library_service.create(library_data)
    
    # Log activity
    activity_service = MongoDBService(db, Collections.USER_ACTIVITY)
    activity_data = {
        "user_id": user_id,
        "activity_type": "purchased",
        "book_id": book_id,
        "title": book.get("title")
    }
    activity_service.create(activity_data)
    
    logger.info(f"Book purchased: {book_id} by user {user_id}")
    
    return {"success": True, "bookId": book_id, "message": "Purchase successful"}