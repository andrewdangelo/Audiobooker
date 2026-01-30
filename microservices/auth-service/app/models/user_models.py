"""
MongoDB User Models using Pydantic

Models for MongoDB documents with ObjectId support.
"""

from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, Any
from datetime import datetime
from enum import Enum
from bson import ObjectId


class PyObjectId(str):
    """Custom ObjectId type for Pydantic models"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v, info=None):
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str):
            if ObjectId.is_valid(v):
                return v
            raise ValueError("Invalid ObjectId")
        raise ValueError("ObjectId required")
    
    @classmethod
    def __get_pydantic_json_schema__(cls, schema: Any, handler: Any) -> dict:
        return {"type": "string"}


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
    PENDING_CANCELLATION = "pending_cancellation"  # Will cancel at period end


class UserDocument(BaseModel):
    """MongoDB User document model"""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    email: EmailStr
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    hashed_password: Optional[str] = None  # NULL for OAuth users
    profile_picture_url: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    auth_provider: AuthProvider = AuthProvider.LOCAL
    google_id: Optional[str] = None
    credits: int = Field(default=3, description="Total credits (deprecated - use basic_credits + premium_credits)")
    basic_credits: int = Field(default=3, description="Basic credits for single voice narration")
    premium_credits: int = Field(default=0, description="Premium credits for multiple character voices")
    # Subscription fields
    subscription_plan: SubscriptionPlan = Field(default=SubscriptionPlan.NONE, description="Current subscription plan")
    subscription_status: SubscriptionStatus = Field(default=SubscriptionStatus.NONE, description="Subscription status")
    subscription_billing_cycle: Optional[str] = Field(default=None, description="monthly or annual")
    subscription_start_date: Optional[datetime] = Field(default=None, description="When subscription started")
    subscription_end_date: Optional[datetime] = Field(default=None, description="When subscription ends/renews")
    subscription_cancelled_at: Optional[datetime] = Field(default=None, description="When cancellation was requested")
    subscription_discount_applied: bool = Field(default=False, description="Whether retention discount was applied")
    subscription_discount_end_date: Optional[datetime] = Field(default=None, description="When discount period ends")
    stripe_customer_id: Optional[str] = Field(default=None, description="Stripe customer ID")
    stripe_subscription_id: Optional[str] = Field(default=None, description="Stripe subscription ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }
    
    def to_dict(self) -> dict:
        """Convert to dictionary for MongoDB insertion"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if "_id" in data and data["_id"] is None:
            del data["_id"]
        # Convert enums to string
        if "auth_provider" in data:
            data["auth_provider"] = data["auth_provider"].value if isinstance(data["auth_provider"], AuthProvider) else data["auth_provider"]
        if "subscription_plan" in data:
            data["subscription_plan"] = data["subscription_plan"].value if isinstance(data["subscription_plan"], SubscriptionPlan) else data["subscription_plan"]
        if "subscription_status" in data:
            data["subscription_status"] = data["subscription_status"].value if isinstance(data["subscription_status"], SubscriptionStatus) else data["subscription_status"]
        return data


class UserCreate(BaseModel):
    """Model for creating a new user"""
    email: EmailStr
    password: str = Field(..., min_length=8)
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


class RefreshTokenDocument(BaseModel):
    """MongoDB Refresh Token document model"""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: str
    token: str
    is_revoked: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }
    
    def to_dict(self) -> dict:
        """Convert to dictionary for MongoDB insertion"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if "_id" in data and data["_id"] is None:
            del data["_id"]
        return data


class AccountSettingsDocument(BaseModel):
    """MongoDB Account Settings document model"""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: str
    two_factor_enabled: bool = False
    email_notifications: bool = True
    marketing_emails: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }
    
    def to_dict(self) -> dict:
        """Convert to dictionary for MongoDB insertion"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if "_id" in data and data["_id"] is None:
            del data["_id"]
        return data
