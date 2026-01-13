"""
Account Management Router
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional
from app.database.database import get_db
from app.models.schemas import (
    UserResponse, UpdateAccountRequest, ChangePasswordRequest,
    UpdateAccountSettingsRequest, AccountSettingsResponse
)
from app.services.auth_service import AuthService
from app.services.account_service import AccountService
from app.utils.security import verify_token
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Account Management"])


def get_current_user_id(authorization: str = Header(None)) -> int:
    """Extract and verify user ID from authorization header"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        token = authorization.replace("Bearer ", "")
        payload = verify_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        return int(payload.get("sub"))
    
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@router.get("/profile", response_model=UserResponse)
async def get_profile(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Get user profile"""
    user = AuthService.get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return UserResponse.from_orm(user)


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    request: UpdateAccountRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    user = AuthService.update_user(
        db=db,
        user_id=user_id,
        first_name=request.first_name,
        last_name=request.last_name,
        username=request.username
    )
    
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update profile")
    
    return UserResponse.from_orm(user)


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Change user password"""
    success, error = AuthService.change_password(
        db=db,
        user_id=user_id,
        old_password=request.old_password,
        new_password=request.new_password
    )
    
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    
    return {"message": "Password changed successfully"}


@router.get("/settings", response_model=AccountSettingsResponse)
async def get_settings(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get account settings"""
    settings = AccountService.get_account_settings(db, user_id)
    
    if not settings:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings not found")
    
    return AccountSettingsResponse.from_orm(settings)


@router.put("/settings", response_model=AccountSettingsResponse)
async def update_settings(
    request: UpdateAccountSettingsRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Update account settings"""
    settings = AccountService.update_account_settings(
        db=db,
        user_id=user_id,
        two_factor_enabled=request.two_factor_enabled,
        email_notifications=request.email_notifications,
        marketing_emails=request.marketing_emails
    )
    
    if not settings:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update settings")
    
    return AccountSettingsResponse.from_orm(settings)


@router.delete("/account")
async def delete_account(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Delete user account"""
    user = AuthService.get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    user.is_active = False
    db.commit()
    
    logger.info(f"Account deleted for user: {user.email}")
    return {"message": "Account deleted successfully"}
