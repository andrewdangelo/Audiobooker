"""
Authentication Service - MongoDB Business Logic

Async service for authentication operations using MongoDB.
"""

from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from bson import ObjectId
import logging
import secrets

from app.database.mongodb import get_users_collection, get_refresh_tokens_collection
from app.models.user_models import UserDocument, RefreshTokenDocument, AuthProvider
from app.utils.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.config_settings import settings

logger = logging.getLogger(__name__)


class AuthServiceMongo:
    """Async service for authentication operations using MongoDB"""
    
    @staticmethod
    async def signup(
        email: str, 
        password: str, 
        first_name: str, 
        last_name: Optional[str] = None, 
        username: Optional[str] = None
    ) -> Tuple[Optional[dict], Optional[str]]:
        """Register a new user"""
        try:
            users = get_users_collection()
            
            # Check if user exists by email
            existing_user = await users.find_one({"email": email})
            if existing_user:
                return None, "Email already registered"
            
            # Check if username is taken
            if username:
                existing_username = await users.find_one({"username": username})
                if existing_username:
                    return None, "Username already taken"
            
            # Create new user document
            user_doc = UserDocument(
                email=email,
                username=username,
                first_name=first_name,
                last_name=last_name,
                hashed_password=hash_password(password),
                auth_provider=AuthProvider.LOCAL,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Insert into MongoDB
            result = await users.insert_one(user_doc.to_dict())
            
            # Fetch the created user
            new_user = await users.find_one({"_id": result.inserted_id})
            
            logger.info(f"New user registered: {email}")
            return new_user, None
        
        except Exception as e:
            logger.error(f"Error during signup: {str(e)}")
            return None, "Failed to create user account"
    
    @staticmethod
    async def login(email: str, password: str) -> Tuple[Optional[dict], Optional[str]]:
        """Authenticate user with email and password"""
        try:
            users = get_users_collection()
            
            # Find user by email
            user = await users.find_one({"email": email})
            
            if not user:
                return None, "Invalid email or password"
            
            if not user.get("hashed_password"):
                return None, "User registered with OAuth provider"
            
            if not verify_password(password, user["hashed_password"]):
                return None, "Invalid email or password"
            
            if not user.get("is_active", True):
                return None, "User account is disabled"
            
            # Update last login
            await users.update_one(
                {"_id": user["_id"]},
                {"$set": {"last_login": datetime.utcnow(), "updated_at": datetime.utcnow()}}
            )
            
            # Refetch user with updated data
            user = await users.find_one({"_id": user["_id"]})
            
            logger.info(f"User logged in: {email}")
            return user, None
        
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return None, "Login failed"
    
    @staticmethod
    async def google_oauth_login(code: str) -> Tuple[Optional[dict], Optional[str]]:
        """Handle Google OAuth login"""
        try:
            from app.utils.google_oauth import google_oauth_manager
            
            users = get_users_collection()
            
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
            
            # Check if user exists by google_id
            user = await users.find_one({"google_id": google_id})
            
            if user:
                # Update last login
                await users.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"last_login": datetime.utcnow(), "updated_at": datetime.utcnow()}}
                )
                user = await users.find_one({"_id": user["_id"]})
                return user, None
            
            # Check if email exists
            user = await users.find_one({"email": email})
            
            if user:
                # Link Google account to existing user
                await users.update_one(
                    {"_id": user["_id"]},
                    {
                        "$set": {
                            "google_id": google_id,
                            "auth_provider": AuthProvider.GOOGLE.value,
                            "last_login": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                user = await users.find_one({"_id": user["_id"]})
                return user, None
            
            # Create new user
            new_user_doc = UserDocument(
                email=email,
                google_id=google_id,
                first_name=user_info.get("given_name"),
                last_name=user_info.get("family_name"),
                profile_picture_url=user_info.get("picture"),
                is_verified=user_info.get("email_verified", False),
                auth_provider=AuthProvider.GOOGLE,
                last_login=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            result = await users.insert_one(new_user_doc.to_dict())
            new_user = await users.find_one({"_id": result.inserted_id})
            
            logger.info(f"New user created via Google OAuth: {email}")
            return new_user, None
        
        except Exception as e:
            logger.error(f"Error during Google OAuth login: {str(e)}")
            return None, "Google authentication failed"
    
    @staticmethod
    async def create_tokens(user_id: str) -> Dict[str, Any]:
        """Create access and refresh tokens"""
        access_token = create_access_token({"sub": user_id})
        refresh_token = create_refresh_token({"sub": user_id})
        
        # Store refresh token in MongoDB
        refresh_tokens = get_refresh_tokens_collection()
        
        token_doc = RefreshTokenDocument(
            user_id=user_id,
            token=refresh_token,
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        
        await refresh_tokens.insert_one(token_doc.to_dict())
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # in seconds
        }
    
    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[dict]:
        """Get user by ID"""
        try:
            users = get_users_collection()
            return await users.find_one({"_id": ObjectId(user_id)})
        except Exception as e:
            logger.error(f"Error getting user by ID: {str(e)}")
            return None
    
    @staticmethod
    async def get_user_by_email(email: str) -> Optional[dict]:
        """Get user by email"""
        users = get_users_collection()
        return await users.find_one({"email": email})
    
    @staticmethod
    async def update_user(
        user_id: str, 
        first_name: Optional[str] = None, 
        last_name: Optional[str] = None, 
        username: Optional[str] = None
    ) -> Optional[dict]:
        """Update user information"""
        try:
            users = get_users_collection()
            
            # Check if username is already taken by another user
            if username:
                existing = await users.find_one({
                    "username": username,
                    "_id": {"$ne": ObjectId(user_id)}
                })
                if existing:
                    return None
            
            # Build update document
            update_fields = {"updated_at": datetime.utcnow()}
            if first_name is not None:
                update_fields["first_name"] = first_name
            if last_name is not None:
                update_fields["last_name"] = last_name
            if username is not None:
                update_fields["username"] = username
            
            await users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_fields}
            )
            
            return await users.find_one({"_id": ObjectId(user_id)})
        
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            return None
    
    @staticmethod
    async def change_password(user_id: str, old_password: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """Change user password"""
        try:
            users = get_users_collection()
            
            user = await users.find_one({"_id": ObjectId(user_id)})
            if not user:
                return False, "User not found"
            
            if not verify_password(old_password, user.get("hashed_password", "")):
                return False, "Invalid current password"
            
            await users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "hashed_password": hash_password(new_password),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"Password changed for user: {user['email']}")
            return True, None
        
        except Exception as e:
            logger.error(f"Error changing password: {str(e)}")
            return False, "Failed to change password"
    
    @staticmethod
    async def revoke_refresh_token(token: str) -> bool:
        """Revoke a refresh token"""
        try:
            refresh_tokens = get_refresh_tokens_collection()
            
            result = await refresh_tokens.update_one(
                {"token": token},
                {"$set": {"is_revoked": True}}
            )
            
            return result.modified_count > 0
        
        except Exception as e:
            logger.error(f"Error revoking refresh token: {str(e)}")
            return False
    
    @staticmethod
    async def validate_refresh_token(token: str) -> Optional[dict]:
        """Validate a refresh token and return the associated user"""
        try:
            refresh_tokens = get_refresh_tokens_collection()
            
            token_doc = await refresh_tokens.find_one({
                "token": token,
                "is_revoked": False,
                "expires_at": {"$gt": datetime.utcnow()}
            })
            
            if not token_doc:
                return None
            
            users = get_users_collection()
            return await users.find_one({"_id": ObjectId(token_doc["user_id"])})
        
        except Exception as e:
            logger.error(f"Error validating refresh token: {str(e)}")
            return None
