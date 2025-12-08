# app/routers/auth.py

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from config.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import Token
from app.services.auth_service import create_user, authenticate_user
from app.services.auth_dependencies import get_current_active_user
from app.core.security import create_access_token

router = APIRouter(tags=["Auth"])  # no prefix here

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(
    user_in: UserCreate,
    db: Session = Depends(get_db),
):
    user = create_user(db, user_in)
    return user

@router.post("/login", response_model=Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(subject=user.id, expires_delta=access_token_expires)

    return Token(access_token=access_token)

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user = Depends(get_current_active_user),
):
    return current_user
