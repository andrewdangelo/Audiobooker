"""
Authentication Service - Business Logic
"""

from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from app.models.user import User, RefreshToken, AuthProvider
from app.utils.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.utils.google_oauth import google_oauth_manager
import logging
import secrets

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations"""
    
    @staticmethod
    def signup(db: Session, email: str, password: str, first_name: str, last_name: Optional[str] = None, username: Optional[str] = None) -> Tuple[Optional[User], Optional[str]]:
        """Register a new user"""
        try:
            # Check if user exists
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                return None, "Email already registered"
            
            if username:
                existing_username = db.query(User).filter(User.username == username).first()
                if existing_username:
                    return None, "Username already taken"
            
            # Create new user
            new_user = User(
                email=email,
                username=username,
                first_name=first_name,
                last_name=last_name,
                hashed_password=hash_password(password),
                auth_provider=AuthProvider.LOCAL
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            logger.info(f"New user registered: {email}")
            return new_user, None
        
        except Exception as e:
            db.rollback()
            logger.error(f"Error during signup: {str(e)}")
            return None, "Failed to create user account"
    
    @staticmethod
    def login(db: Session, email: str, password: str) -> Tuple[Optional[User], Optional[str]]:
        """Authenticate user with email and password"""
        try:
            user = db.query(User).filter(User.email == email).first()
            
            if not user:
                return None, "Invalid email or password"
            
            if not user.hashed_password:
                return None, "User registered with OAuth provider"
            
            if not verify_password(password, user.hashed_password):
                return None, "Invalid email or password"
            
            if not user.is_active:
                return None, "User account is disabled"
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.commit()
            
            logger.info(f"User logged in: {email}")
            return user, None
        
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return None, "Login failed"
    
    @staticmethod
    async def google_oauth_login(db: Session, code: str) -> Tuple[Optional[User], Optional[str]]:
        """Handle Google OAuth login"""
        try:
            # Exchange code for token
            token_response = await google_oauth_manager.exchange_code_for_token(code)
            if not token_response:
                return None, "Failed to authenticate with Google"
            
            access_token = token_response.get("access_token")
            
            # Get user info
            user_info = await google_oauth_manager.get_user_info(access_token)
            if not user_info:
                return None, "Failed to get user information"
            
            google_id = user_info.get("id")
            email = user_info.get("email")
            
            # Check if user exists
            user = db.query(User).filter(User.google_id == google_id).first()
            
            if user:
                # Update last login
                user.last_login = datetime.utcnow()
                db.commit()
                return user, None
            
            # Check if email exists
            user = db.query(User).filter(User.email == email).first()
            
            if user:
                # Link Google account to existing user
                user.google_id = google_id
                user.auth_provider = AuthProvider.GOOGLE
                user.last_login = datetime.utcnow()
                db.commit()
                return user, None
            
            # Create new user
            new_user = User(
                email=email,
                google_id=google_id,
                first_name=user_info.get("given_name"),
                last_name=user_info.get("family_name"),
                profile_picture_url=user_info.get("picture"),
                is_verified=user_info.get("email_verified", False),
                auth_provider=AuthProvider.GOOGLE,
                last_login=datetime.utcnow()
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            logger.info(f"New user created via Google OAuth: {email}")
            return new_user, None
        
        except Exception as e:
            logger.error(f"Error during Google OAuth login: {str(e)}")
            return None, "Google authentication failed"
    
    @staticmethod
    def create_tokens(user_id: int, db: Session) -> Dict[str, Any]:
        """Create access and refresh tokens"""
        access_token = create_access_token({"sub": str(user_id)})
        refresh_token = create_refresh_token({"sub": str(user_id)})
        
        # Store refresh token
        token_record = RefreshToken(
            user_id=user_id,
            token=refresh_token,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.add(token_record)
        db.commit()
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 30 * 60  # 30 minutes in seconds
        }
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def update_user(db: Session, user_id: int, first_name: Optional[str] = None, last_name: Optional[str] = None, username: Optional[str] = None) -> Optional[User]:
        """Update user information"""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            if username:
                # Check if username is already taken
                existing = db.query(User).filter(User.username == username, User.id != user_id).first()
                if existing:
                    return None
                user.username = username
            
            db.commit()
            db.refresh(user)
            return user
        
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            return None
    
    @staticmethod
    def change_password(db: Session, user_id: int, old_password: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """Change user password"""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False, "User not found"
            
            if not verify_password(old_password, user.hashed_password):
                return False, "Invalid current password"
            
            user.hashed_password = hash_password(new_password)
            db.commit()
            
            logger.info(f"Password changed for user: {user.email}")
            return True, None
        
        except Exception as e:
            logger.error(f"Error changing password: {str(e)}")
            return False, "Failed to change password"
