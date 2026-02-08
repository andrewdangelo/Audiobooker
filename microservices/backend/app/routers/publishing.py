"""
Publishing & Listings Endpoints
"""

__author__ = "Mohammad Saifan"

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
import logging
import uuid
import math

from app.database.database import get_db
from app.database.db_engine import MongoDBService
from app.models.db_models import Collections

logger = logging.getLogger(__name__)
router = APIRouter()


def check_permission(permission: str) -> bool:
    """Check if user has permission"""
    # TODO: Implement actual permission checking
    return True


@router.post("/store/listings", status_code=201)
async def create_listing(user_id: str = Query(..., description="User ID"), request: dict = None, db = Depends(get_db())):
    """Create new store listing (publish audiobook)"""
    if not check_permission("PUBLISH_AUDIOBOOK"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    book_id = request.get("audiobookId")
    
    # Create listing
    listing_service = MongoDBService(db, Collections.STORE_LISTINGS)
    listing_data = {
        "user_id": user_id,
        "book_id": book_id,
        "title": request.get("title"),
        "price": request.get("price"),
        "status": "pending_review"
    }
    
    listing = listing_service.create(listing_data)
    
    logger.info(f"Listing created: {listing.get('id')}")
    
    return {
        "id": listing.get("_id"),
        "status": listing.get("status"),
        "message": "Listing submitted for review"
    }


@router.get("/store/listings/my-listings")
async def get_my_listings(user_id: str = Query(..., description="User ID"), status: str = Query("all"), page: int = Query(1, ge=1), 
                        limit: int = Query(20, ge=1, le=100), db = Depends(get_db())):
    """Get current user's store listings"""
    if not check_permission("PUBLISH_AUDIOBOOK"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    skip = (page - 1) * limit
    
    listing_service = MongoDBService(db, Collections.STORE_LISTINGS)
    
    filter_query = {"user_id": user_id}
    if status != "all":
        filter_query["status"] = status
    
    total = listing_service.count(filter_query)
    listings = listing_service.get_all(skip=skip, limit=limit, filter_query=filter_query)
    
    listing_data = [
        {
            "id": listing.get("_id"),
            "title": listing.get("title"),
            "status": listing.get("status"),
            "price": listing.get("price"),
            "totalSales": listing.get("total_sales", 0),
            "rating": listing.get("rating", 0.0),
            "publishedAt": listing.get("published_at").isoformat() if listing.get("published_at") else None
        }
        for listing in listings
    ]
    
    return {
        "listings": listing_data,
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1
    }


@router.get("/store/listings/{listing_id}")
async def get_listing_details(listing_id: str, user_id: str = Query(..., description="User ID"), db = Depends(get_db())):
    """Get specific listing details"""
    if not check_permission("PUBLISH_AUDIOBOOK"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    listing_service = MongoDBService(db, Collections.STORE_LISTINGS)
    listing = listing_service.find_one({
        "id": listing_id,
        "user_id": user_id
    })
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    return {
        "id": listing.get("_id"),
        "audiobookId": listing.get("book_id"),
        "title": listing.get("title"),
        "status": listing.get("status"),
        "price": listing.get("price"),
        "totalSales": listing.get("total_sales", 0),
        "revenue": listing.get("revenue", 0.0),
        "rating": listing.get("rating", 0.0)
    }


@router.patch("/store/listings/{listing_id}")
async def update_listing(listing_id: str, user_id: str = Query(..., description="User ID"), request: dict = None, db = Depends(get_db())):
    """Update listing information"""
    if not check_permission("PUBLISH_AUDIOBOOK"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    listing_service = MongoDBService(db, Collections.STORE_LISTINGS)
    listing = listing_service.find_one({
        "id": listing_id,
        "user_id": user_id
    })
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Update fields
    update_data = {}
    if "price" in request:
        update_data["price"] = request["price"]
    if "description" in request:
        update_data["description"] = request["description"]
    
    updated_listing = listing_service.update(listing_id, update_data)
    
    return {"success": True, "listing": {"id": updated_listing.get("_id")}}


@router.delete("/store/listings/{listing_id}", status_code=204)
async def delete_listing(listing_id: str, user_id: str = Query(..., description="User ID"), db = Depends(get_db())):
    """Delete/unlist a store listing"""
    if not check_permission("PUBLISH_AUDIOBOOK"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    listing_service = MongoDBService(db, Collections.STORE_LISTINGS)
    listing = listing_service.find_one({
        "id": listing_id,
        "user_id": user_id
    })
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    listing_service.delete(listing_id)
    
    logger.info(f"Listing deleted: {listing_id}")
    return None


@router.post("/store/listings/{listing_id}/cover")
async def upload_listing_cover(listing_id: str, user_id: str = Query(..., description="User ID"), file: UploadFile = File(...), db = Depends(get_db())):
    """Upload cover image for listing"""
    if not check_permission("PUBLISH_AUDIOBOOK"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Validate file
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # TODO: Upload to R2 storage
    cover_url = f"https://cdn.example.com/covers/{listing_id}.jpg"
    
    # Update listing
    listing_service = MongoDBService(db, Collections.STORE_LISTINGS)
    listing_service.update(listing_id, {"cover_image_url": cover_url})
    
    return {"coverImageUrl": cover_url}