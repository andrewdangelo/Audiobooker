"""
Auth Service Configuration Management

Using Pydantic Settings for environment variable management with validation.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional


class Settings(BaseSettings):
    """Base Settings for Authentication Service"""
    
    # Environment
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    PORT: int = Field(default=8003, description="Service port")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    DEBUG: bool = True
    TEST_VERSION: str = Field(default="1.0.0", description="Application version")
    
    # Endpoints
    API_V1_PREFIX: str = "/api/v1/auth"
    
    # MongoDB Configuration
    MONGODB_URL: str = Field(default="mongodb://localhost:27017", description="MongoDB connection URL")
    MONGODB_DB_NAME: str = Field(default="audiobooker_auth", description="MongoDB database name")
    MONGODB_MAX_POOL_SIZE: int = Field(default=10, description="Maximum connection pool size")
    MONGODB_MIN_POOL_SIZE: int = Field(default=1, description="Minimum connection pool size")
    
    # Legacy Database URL (deprecated, kept for compatibility)
    DATABASE_URL: str = Field(default="mongodb://localhost:27017", description="Database connection URL")
    
    # JWT Configuration
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production", description="Secret key for JWT encoding")
    ALGORITHM: str = Field(default="HS256", description="Algorithm for JWT encoding")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Access token expiration time in minutes")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh token expiration time in days")
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str = Field(default="", description="Google OAuth Client ID")
    GOOGLE_CLIENT_SECRET: str = Field(default="", description="Google OAuth Client Secret")
    GOOGLE_REDIRECT_URI: str = Field(default="", description="Google OAuth Redirect URI")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    
    # Email Configuration (optional)
    SMTP_SERVER: Optional[str] = Field(default=None, description="SMTP server for email")
    SMTP_PORT: Optional[int] = Field(default=587, description="SMTP port")
    SMTP_USER: Optional[str] = Field(default=None, description="SMTP user")
    SMTP_PASSWORD: Optional[str] = Field(default=None, description="SMTP password")
    SENDER_EMAIL: Optional[str] = Field(default=None, description="Sender email address")
    
    # Redis Configuration
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
