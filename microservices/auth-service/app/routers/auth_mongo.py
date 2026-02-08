"""
Authentication Router - Login, Signup, OAuth (MongoDB version)
"""

from fastapi import APIRouter, HTTPException, status
from app.models.schemas import (
    SignupRequest, LoginRequest, GoogleLoginRequest, TokenResponse, 
    AuthResponse, UserResponse, RefreshTokenRequest
)
from app.services.auth_service_mongo import AuthServiceMongo
from app.utils.security import verify_token
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignupRequest):
    """User signup endpoint"""
    user, error = await AuthServiceMongo.signup(
        email=request.email,
        password=request.password,
        first_name=request.first_name,
        last_name=request.last_name,
        username=request.username
    )
    
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    
    user_id = str(user["_id"])
    tokens = await AuthServiceMongo.create_tokens(user_id)
    
    return AuthResponse(
        user=UserResponse.from_mongo(user),
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"]
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """User login endpoint"""
    user, error = await AuthServiceMongo.login(email=request.email, password=request.password)
    
    if error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error)
    
    user_id = str(user["_id"])
    tokens = await AuthServiceMongo.create_tokens(user_id)
    
    return AuthResponse(
        user=UserResponse.from_mongo(user),
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"]
    )


@router.post("/google/callback", response_model=AuthResponse)
async def google_oauth_callback(request: GoogleLoginRequest):
    """Google OAuth callback handler"""
    user, error = await AuthServiceMongo.google_oauth_login(code=request.code)
    
    if error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error)
    
    user_id = str(user["_id"])
    tokens = await AuthServiceMongo.create_tokens(user_id)
    
    return AuthResponse(
        user=UserResponse.from_mongo(user),
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"]
    )


@router.post("/google/auth-url", response_model=dict)
async def get_google_auth_url():
    """Get Google OAuth authorization URL"""
    import secrets
    from app.core.config_settings import settings
    
    state = secrets.token_urlsafe(32)
    
    # In production, store state in Redis with expiration for CSRF protection
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.GOOGLE_CLIENT_ID}&"
        f"redirect_uri={settings.GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"state={state}"
    )
    
    return {"auth_url": auth_url, "state": state}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """Refresh access token"""
    payload = verify_token(request.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    
    # Validate the refresh token in DB
    user = await AuthServiceMongo.validate_refresh_token(request.refresh_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    tokens = await AuthServiceMongo.create_tokens(user_id)
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=tokens["expires_in"]
    )


@router.post("/logout")
async def logout(request: RefreshTokenRequest):
    """Logout user - revoke refresh token"""
    success = await AuthServiceMongo.revoke_refresh_token(request.refresh_token)
    
    if not success:
        logger.warning("Logout called with invalid/already revoked token")
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(token: str = None):
    """Get current user information"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_id = payload.get("sub")
    user = await AuthServiceMongo.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.from_mongo(user)
