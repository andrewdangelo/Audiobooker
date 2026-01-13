"""
Account Management Service
"""

from sqlalchemy.orm import Session
from typing import Optional
from app.models.user import AccountSettings
from app.services.auth_service import AuthService
import logging

logger = logging.getLogger(__name__)


class AccountService:
    """Service for account management operations"""
    
    @staticmethod
    def get_account_settings(db: Session, user_id: int) -> Optional[AccountSettings]:
        """Get account settings for user"""
        try:
            settings = db.query(AccountSettings).filter(AccountSettings.user_id == user_id).first()
            
            if not settings:
                # Create default settings if they don't exist
                settings = AccountSettings(user_id=user_id)
                db.add(settings)
                db.commit()
                db.refresh(settings)
            
            return settings
        
        except Exception as e:
            logger.error(f"Error getting account settings: {str(e)}")
            return None
    
    @staticmethod
    def update_account_settings(db: Session, user_id: int, two_factor_enabled: Optional[bool] = None, email_notifications: Optional[bool] = None, marketing_emails: Optional[bool] = None) -> Optional[AccountSettings]:
        """Update account settings"""
        try:
            settings = AccountService.get_account_settings(db, user_id)
            
            if not settings:
                return None
            
            if two_factor_enabled is not None:
                settings.two_factor_enabled = two_factor_enabled
            if email_notifications is not None:
                settings.email_notifications = email_notifications
            if marketing_emails is not None:
                settings.marketing_emails = marketing_emails
            
            db.commit()
            db.refresh(settings)
            
            logger.info(f"Account settings updated for user: {user_id}")
            return settings
        
        except Exception as e:
            logger.error(f"Error updating account settings: {str(e)}")
            return None
    
    @staticmethod
    def get_user_profile(db: Session, user_id: int):
        """Get complete user profile"""
        try:
            user = AuthService.get_user_by_id(db, user_id)
            if not user:
                return None
            
            settings = AccountService.get_account_settings(db, user_id)
            
            return {
                "user": user,
                "settings": settings
            }
        
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return None
