"""
Cart & Checkout Endpoints
"""

__author__ = "Mohammad Saifan"

from fastapi import APIRouter, Depends, HTTPException, Query, status
import logging
import uuid

from app.database.database import get_db
from app.database.db_engine import MongoDBService
from app.models.db_models import Collections

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/cart", response_model=dict)
async def get_cart(user_id: str = Query(..., description="User ID"), db = Depends(get_db())):
    """Get user's shopping cart"""
    cart_service = MongoDBService(db, Collections.CART_ITEMS)
    cart_items = cart_service.find_many({"user_id": user_id})
    
    items = []
    subtotal = 0.0
    
    book_service = MongoDBService(db, Collections.BOOKS)
    for item in cart_items:
        book = book_service.get_by_id(item.get("book_id"))
        if book:
            item_price = book.get("price", 0) * item.get("quantity", 1) if book.get("price") else 0.0
            subtotal += item_price
            
            items.append({
                "bookId": book.get("_id"),
                "title": book.get("title"),
                "price": book.get("price"),
                "credits": book.get("credits_required", 1),
                "quantity": item.get("quantity", 1),
                "coverImage": book.get("cover_image_url")
            })
    
    tax = subtotal * 0.06625  # 6.625% tax #TODO - make this configurable
    total = subtotal + tax
    
    return {
        "items": items,
        "subtotal": round(subtotal, 2),
        "tax": round(tax, 2),
        "total": round(total, 2)
    }


@router.post("/cart/items", status_code=201)
async def add_to_cart(user_id: str = Query(..., description="User ID"), request: dict = None, db = Depends(get_db())):
    """Add item to cart"""
    book_id = request.get("bookId")
    quantity = request.get("quantity", 1)
    
    # Check if book exists
    book_service = MongoDBService(db, Collections.BOOKS)
    book = book_service.get_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Check if item already in cart
    cart_service = MongoDBService(db, Collections.CART_ITEMS)
    existing = cart_service.find_one({
        "user_id": user_id,
        "book_id": book_id
    })
    
    if existing:
        new_quantity = existing.get("quantity", 1) + quantity
        cart_service.update(existing.get("_id"), {"quantity": new_quantity})
    else:
        cart_data = {
            "user_id": user_id,
            "book_id": book_id,
            "quantity": quantity
        }
        cart_service.create(cart_data)
    
    logger.info(f"Item added to cart: {book_id}")
    
    return {"success": True, "bookId": book_id}


@router.delete("/cart/items/{book_id}", status_code=204)
async def remove_from_cart(book_id: str, user_id: str = Query(..., description="User ID"), db = Depends(get_db())):
    """Remove item from cart"""
    cart_service = MongoDBService(db, Collections.CART_ITEMS)
    deleted = cart_service.delete_many({
        "user_id": user_id,
        "book_id": book_id
    })
    
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Item not found in cart")
    
    logger.info(f"Item removed from cart: {book_id}")
    return None


@router.patch("/cart/items/{book_id}")
async def update_cart_item(book_id: str, user_id: str = Query(..., description="User ID"), request: dict = None, db = Depends(get_db())):
    """Update cart item quantity"""
    quantity = request.get("quantity", 1)
    
    cart_service = MongoDBService(db, Collections.CART_ITEMS)
    cart_item = cart_service.find_one({
        "user_id": user_id,
        "book_id": book_id
    })
    
    if not cart_item:
        raise HTTPException(status_code=404, detail="Item not found in cart")
    
    cart_service.update(cart_item.get("_id"), {"quantity": quantity})
    
    return {"success": True, "bookId": book_id, "quantity": quantity}


@router.post("/cart/sync")
async def sync_cart(user_id: str = Query(..., description="User ID"), request: dict = None, db = Depends(get_db())):
    """Sync cart across devices"""
    items = request.get("items", [])
    
    cart_service = MongoDBService(db, Collections.CART_ITEMS)
    
    # Clear existing cart
    cart_service.delete_many({"user_id": user_id})
    
    # Add new items
    for item in items:
        cart_data = {
            "user_id": user_id,
            "book_id": item.get("bookId"),
            "quantity": item.get("quantity", 1)
        }
        cart_service.create(cart_data)
    
    return {"success": True, "itemCount": len(items)}


@router.post("/cart/validate")
async def validate_cart(user_id: str = Query(..., description="User ID"), db = Depends(get_db())):
    """Validate cart items availability and pricing"""
    cart_service = MongoDBService(db, Collections.CART_ITEMS)
    cart_items = cart_service.find_many({"user_id": user_id})
    
    valid = True
    issues = []
    updated_prices = []
    
    book_service = MongoDBService(db, Collections.BOOKS)
    for item in cart_items:
        book = book_service.get_by_id(item.get("book_id"))
        if not book:
            valid = False
            issues.append(f"Book {item.get('book_id')} no longer available")
    
    return {
        "valid": valid,
        "issues": issues,
        "updatedPrices": updated_prices
    }


@router.delete("/cart", status_code=204)
async def clear_cart(user_id: str = Query(..., description="User ID"), db = Depends(get_db())):
    """Clear entire cart"""
    cart_service = MongoDBService(db, Collections.CART_ITEMS)
    cart_service.delete_many({"user_id": user_id})
    
    logger.info(f"Cart cleared for user {user_id}")
    return None


@router.post("/checkout")
async def process_checkout(user_id: str = Query(..., description="User ID"), request: dict = None, db = Depends(get_db())):
    """Process checkout and complete purchase"""
    payment_method = request.get("paymentMethod")
    payment_intent_id = request.get("paymentIntentId")
    
    # Get cart items
    cart_service = MongoDBService(db, Collections.CART_ITEMS)
    cart_items = cart_service.find_many({"user_id": user_id})
    
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Process each item
    book_service = MongoDBService(db, Collections.BOOKS)
    library_service = MongoDBService(db, Collections.USER_LIBRARY)
    
    for item in cart_items:
        book = book_service.get_by_id(item.get("book_id"))
        if book:
            # Add to library
            library_data = {
                "user_id": user_id,
                "book_id": book.get("_id"),
                "progress": 0.0
            }
            library_service.create(library_data)
    
    # Clear cart
    cart_service.delete_many({"user_id": user_id})
    
    logger.info(f"Checkout completed for user {user_id}")
    
    return {
        "success": True,
        "orderId": str(uuid.uuid4()),
        "message": "Purchase completed successfully"
    }