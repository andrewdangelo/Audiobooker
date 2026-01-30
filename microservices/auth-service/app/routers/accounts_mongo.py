"""
Account Management Router (MongoDB version)
"""

from fastapi import APIRouter, HTTPException, status, Header
from typing import Optional
from bson import ObjectId
from datetime import datetime

from app.models.schemas import (
    UserResponse, UpdateAccountRequest, ChangePasswordRequest,
    UpdateAccountSettingsRequest, AccountSettingsResponse
)
from app.services.auth_service_mongo import AuthServiceMongo
from app.database.mongodb import get_users_collection, get_account_settings_collection
from app.utils.security import verify_token
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Account Management"])


async def get_current_user_id(authorization: str = Header(None)) -> str:
    """Extract and verify user ID from authorization header"""
    logger.info(f"Authorization header received: {authorization}")
    
    if not authorization:
        logger.warning("No authorization header provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        token = authorization.replace("Bearer ", "")
        logger.info(f"Token extracted (first 20 chars): {token[:20]}...")
        payload = verify_token(token)
        
        if not payload:
            logger.warning("Token verification returned None")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        logger.info(f"Token verified for user: {payload.get('sub')}")
        return payload.get("sub")
    
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@router.get("/profile", response_model=UserResponse)
async def get_profile(authorization: str = Header(None)):
    """Get user profile"""
    user_id = await get_current_user_id(authorization)
    user = await AuthServiceMongo.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return UserResponse.from_mongo(user)


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    request: UpdateAccountRequest,
    authorization: str = Header(None)
):
    """Update user profile"""
    user_id = await get_current_user_id(authorization)
    
    user = await AuthServiceMongo.update_user(
        user_id=user_id,
        first_name=request.first_name,
        last_name=request.last_name,
        username=request.username
    )
    
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update profile")
    
    return UserResponse.from_mongo(user)


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    authorization: str = Header(None)
):
    """Change user password"""
    user_id = await get_current_user_id(authorization)
    
    success, error = await AuthServiceMongo.change_password(
        user_id=user_id,
        old_password=request.old_password,
        new_password=request.new_password
    )
    
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    
    return {"message": "Password changed successfully"}


@router.get("/settings", response_model=AccountSettingsResponse)
async def get_settings(authorization: str = Header(None)):
    """Get account settings"""
    user_id = await get_current_user_id(authorization)
    
    settings_collection = get_account_settings_collection()
    settings = await settings_collection.find_one({"user_id": user_id})
    
    if not settings:
        # Create default settings if not exists
        default_settings = {
            "user_id": user_id,
            "two_factor_enabled": False,
            "email_notifications": True,
            "marketing_emails": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await settings_collection.insert_one(default_settings)
        settings = await settings_collection.find_one({"user_id": user_id})
    
    return AccountSettingsResponse(
        user_id=settings.get("user_id"),
        two_factor_enabled=settings.get("two_factor_enabled", False),
        email_notifications=settings.get("email_notifications", True),
        marketing_emails=settings.get("marketing_emails", False),
        created_at=settings.get("created_at"),
        updated_at=settings.get("updated_at")
    )


@router.put("/settings", response_model=AccountSettingsResponse)
async def update_settings(
    request: UpdateAccountSettingsRequest,
    authorization: str = Header(None)
):
    """Update account settings"""
    user_id = await get_current_user_id(authorization)
    
    settings_collection = get_account_settings_collection()
    
    # Build update document
    update_fields = {"updated_at": datetime.utcnow()}
    if request.two_factor_enabled is not None:
        update_fields["two_factor_enabled"] = request.two_factor_enabled
    if request.email_notifications is not None:
        update_fields["email_notifications"] = request.email_notifications
    if request.marketing_emails is not None:
        update_fields["marketing_emails"] = request.marketing_emails
    
    # Upsert settings
    await settings_collection.update_one(
        {"user_id": user_id},
        {
            "$set": update_fields,
            "$setOnInsert": {"created_at": datetime.utcnow()}
        },
        upsert=True
    )
    
    settings = await settings_collection.find_one({"user_id": user_id})
    
    return AccountSettingsResponse(
        user_id=settings.get("user_id"),
        two_factor_enabled=settings.get("two_factor_enabled", False),
        email_notifications=settings.get("email_notifications", True),
        marketing_emails=settings.get("marketing_emails", False),
        created_at=settings.get("created_at"),
        updated_at=settings.get("updated_at")
    )


@router.delete("/account")
async def delete_account(authorization: str = Header(None)):
    """Delete user account (soft delete - deactivate)"""
    user_id = await get_current_user_id(authorization)
    
    users = get_users_collection()
    user = await users.find_one({"_id": ObjectId(user_id)})
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Soft delete - set is_active to False
    await users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )
    
    return {"message": "Account deactivated successfully"}


@router.get("/credits")
async def get_user_credits(authorization: str = Header(None)):
    """Get user's current credit balance (basic and premium)"""
    user_id = await get_current_user_id(authorization)
    
    users = get_users_collection()
    user = await users.find_one(
        {"_id": ObjectId(user_id)}, 
        {"credits": 1, "basic_credits": 1, "premium_credits": 1}
    )
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return {
        "user_id": user_id,
        "credits": user.get("credits", 0),  # Legacy total
        "basic_credits": user.get("basic_credits", 0),
        "premium_credits": user.get("premium_credits", 0),
        "total_credits": user.get("basic_credits", 0) + user.get("premium_credits", 0)
    }


@router.get("/subscription")
async def get_subscription_status(authorization: str = Header(None)):
    """Get user's current subscription status"""
    user_id = await get_current_user_id(authorization)
    
    users = get_users_collection()
    user = await users.find_one(
        {"_id": ObjectId(user_id)}, 
        {
            "subscription_plan": 1, 
            "subscription_status": 1,
            "subscription_billing_cycle": 1,
            "subscription_start_date": 1,
            "subscription_end_date": 1,
            "subscription_cancelled_at": 1,
            "subscription_discount_applied": 1,
            "subscription_discount_end_date": 1,
            "stripe_subscription_id": 1
        }
    )
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return {
        "user_id": user_id,
        "subscription_plan": user.get("subscription_plan", "none"),
        "subscription_status": user.get("subscription_status", "none"),
        "subscription_billing_cycle": user.get("subscription_billing_cycle"),
        "subscription_start_date": user.get("subscription_start_date"),
        "subscription_end_date": user.get("subscription_end_date"),
        "subscription_cancelled_at": user.get("subscription_cancelled_at"),
        "subscription_discount_applied": user.get("subscription_discount_applied", False),
        "subscription_discount_end_date": user.get("subscription_discount_end_date"),
        "is_subscribed": user.get("subscription_status") in ["active", "pending_cancellation"]
    }


@router.put("/subscription")
async def update_subscription(
    subscription_data: dict,
    authorization: str = Header(None)
):
    """Update user's subscription (internal use - called by payment service)"""
    user_id = await get_current_user_id(authorization)
    
    users = get_users_collection()
    
    # Build update document
    update_fields = {"updated_at": datetime.utcnow()}
    
    allowed_fields = [
        "subscription_plan", "subscription_status", "subscription_billing_cycle",
        "subscription_start_date", "subscription_end_date", "subscription_cancelled_at",
        "subscription_discount_applied", "subscription_discount_end_date",
        "stripe_customer_id", "stripe_subscription_id"
    ]
    
    for field in allowed_fields:
        if field in subscription_data:
            update_fields[field] = subscription_data[field]
    
    result = await users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_fields}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update subscription")
    
    # Return updated subscription info
    user = await users.find_one({"_id": ObjectId(user_id)})
    
    return {
        "user_id": user_id,
        "subscription_plan": user.get("subscription_plan", "none"),
        "subscription_status": user.get("subscription_status", "none"),
        "subscription_billing_cycle": user.get("subscription_billing_cycle"),
        "subscription_end_date": user.get("subscription_end_date"),
        "message": "Subscription updated successfully"
    }

