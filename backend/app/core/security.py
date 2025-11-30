# app/core/security.py

from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from pwdlib import PasswordHash

from config.settings import settings  # your existing settings

password_hash = PasswordHash.recommended()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def get_secret_key() -> str:
    # use SECRET_KEY from settings, fallback if needed
    return settings.SECRET_KEY or "change-me-in-production"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return password_hash.hash(password)

def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = {"sub": subject}
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
    return payload
