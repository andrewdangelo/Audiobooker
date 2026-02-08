"""
Authentication Router - Login, Signup, OAuth
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.models.schemas import (
    SignupRequest, LoginRequest, GoogleLoginRequest, TokenResponse, 
    AuthResponse, UserResponse, RefreshTokenRequest
)
from app.services.auth_service import AuthService
from app.utils.security import verify_token
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """User signup endpoint"""
    user, error = AuthService.signup(
        db=db,
        email=request.email,
        password=request.password,
        first_name=request.first_name,
        last_name=request.last_name,
        username=request.username
    )
    
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    
    tokens = AuthService.create_tokens(user.id, db)
    
    return AuthResponse(
        user=UserResponse.from_orm(user),
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"]
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """User login endpoint"""
    user, error = AuthService.login(db=db, email=request.email, password=request.password)
    
    if error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error)
    
    tokens = AuthService.create_tokens(user.id, db)
    
    return AuthResponse(
        user=UserResponse.from_orm(user),
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"]
    )


@router.post("/google/callback", response_model=AuthResponse)
async def google_oauth_callback(request: GoogleLoginRequest, db: Session = Depends(get_db)):
    """Google OAuth callback handler"""
    user, error = await AuthService.google_oauth_login(db=db, code=request.code)
    
    if error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error)
    
    tokens = AuthService.create_tokens(user.id, db)
    
    return AuthResponse(
        user=UserResponse.from_orm(user),
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"]
    )


@router.post("/google/auth-url", response_model=dict)
async def get_google_auth_url():
    """Get Google OAuth authorization URL"""
    import secrets
    state = secrets.token_urlsafe(32)
    
    # In production, store state in Redis with expiration for CSRF protection
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&response_type=code&scope=openid%20email%20profile&state={state}"
    
    return {"auth_url": auth_url, "state": state}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Refresh access token"""
    payload = verify_token(request.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = int(payload.get("sub"))
    tokens = AuthService.create_tokens(user_id, db)
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=tokens["expires_in"]
    )


@router.post("/logout")
async def logout(refresh_token: str, db: Session = Depends(get_db)):
    """Logout user - revoke refresh token"""
    from app.models.user import RefreshToken as RefreshTokenModel
    
    token_record = db.query(RefreshTokenModel).filter(
        RefreshTokenModel.token == refresh_token
    ).first()
    
    if token_record:
        token_record.is_revoked = True
        db.commit()
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(token: str = None, db: Session = Depends(get_db)):
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
    
    user_id = int(payload.get("sub"))
    user = AuthService.get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return UserResponse.from_orm(user)
