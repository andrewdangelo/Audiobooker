"""
Pydantic Schemas for API requests/responses
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from enum import Enum


class AuthProvider(str, Enum):
    """Authentication provider types"""
    LOCAL = "local"
    GOOGLE = "google"


# Request Models
class SignupRequest(BaseModel):
    """User signup request"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    first_name: str = Field(..., min_length=1)
    last_name: Optional[str] = None
    username: Optional[str] = None
    
    @validator('password')
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
    
    @validator('new_password')
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
    id: int
    email: str
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    profile_picture_url: Optional[str]
    is_active: bool
    is_verified: bool
    auth_provider: AuthProvider
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


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
    user_id: int
    two_factor_enabled: bool
    email_notifications: bool
    marketing_emails: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    service: str
