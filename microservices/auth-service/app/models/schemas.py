"""
Pydantic Schemas for API requests/responses
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum


class AuthProvider(str, Enum):
    """Authentication provider types"""
    LOCAL = "local"
    GOOGLE = "google"


class SubscriptionPlan(str, Enum):
    """Subscription plan types"""
    NONE = "none"
    BASIC = "basic"
    PREMIUM = "premium"


class SubscriptionStatus(str, Enum):
    """Subscription status types"""
    NONE = "none"
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING_CANCELLATION = "pending_cancellation"


# Request Models
class SignupRequest(BaseModel):
    """User signup request"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    first_name: str = Field(..., min_length=1)
    last_name: Optional[str] = None
    username: Optional[str] = None
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        return v


class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class GoogleLoginRequest(BaseModel):
    """Google OAuth login request"""
    code: str = Field(..., description="Authorization code from Google")
    state: str = Field(..., description="CSRF protection state")


class GoogleTokenRequest(BaseModel):
    """Google token request"""
    id_token: str = Field(..., description="Google ID token")


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


class UpdateAccountRequest(BaseModel):
    """Update user account request"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    """Change password request"""
    old_password: str
    new_password: str = Field(..., min_length=8)
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UpdateAccountSettingsRequest(BaseModel):
    """Update account settings request"""
    two_factor_enabled: Optional[bool] = None
    email_notifications: Optional[bool] = None
    marketing_emails: Optional[bool] = None


# Response Models
class UserResponse(BaseModel):
    """User response model"""
    id: str  # MongoDB ObjectId as string
    email: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_picture_url: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    auth_provider: AuthProvider = AuthProvider.LOCAL
    credits: int = 0  # Total credits (deprecated)
    basic_credits: int = 0
    premium_credits: int = 0
    # Subscription fields
    subscription_plan: SubscriptionPlan = SubscriptionPlan.NONE
    subscription_status: SubscriptionStatus = SubscriptionStatus.NONE
    subscription_billing_cycle: Optional[str] = None
    subscription_end_date: Optional[datetime] = None
    subscription_discount_applied: bool = False
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    premium_credits: int = 0
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    model_config = {
        "from_attributes": True
    }
    
    @classmethod
    def from_mongo(cls, user_doc: dict) -> "UserResponse":
        """Create UserResponse from MongoDB document"""
        return cls(
            id=str(user_doc.get("_id", "")),
            email=user_doc.get("email", ""),
            username=user_doc.get("username"),
            first_name=user_doc.get("first_name"),
            last_name=user_doc.get("last_name"),
            profile_picture_url=user_doc.get("profile_picture_url"),
            is_active=user_doc.get("is_active", True),
            is_verified=user_doc.get("is_verified", False),
            auth_provider=user_doc.get("auth_provider", AuthProvider.LOCAL),
            credits=user_doc.get("credits", 0),
            basic_credits=user_doc.get("basic_credits", 0),
            premium_credits=user_doc.get("premium_credits", 0),
            subscription_plan=user_doc.get("subscription_plan", SubscriptionPlan.NONE),
            subscription_status=user_doc.get("subscription_status", SubscriptionStatus.NONE),
            subscription_billing_cycle=user_doc.get("subscription_billing_cycle"),
            subscription_end_date=user_doc.get("subscription_end_date"),
            subscription_discount_applied=user_doc.get("subscription_discount_applied", False),
            created_at=user_doc.get("created_at"),
            last_login=user_doc.get("last_login")
        )


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Expiration time in seconds")


class AuthResponse(BaseModel):
    """Authentication response"""
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccountSettingsResponse(BaseModel):
    """Account settings response"""
    user_id: str  # MongoDB ObjectId as string
    two_factor_enabled: bool = False
    email_notifications: bool = True
    marketing_emails: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = {
        "from_attributes": True
    }


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    service: str
