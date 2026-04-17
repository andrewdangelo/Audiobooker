"""
App + env Configuration Management

Using Pydantic Settings, Will Automatically Load from environment variables with validation.
"""

__author__ = "Mohammad Saifan"

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List, Optional
import json
from pathlib import Path


class Settings(BaseSettings):
    """Base Class for Application Settings"""
    
    # Environment
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    PORT: int = Field(default=8002, description="Service port")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    DEBUG: bool = True
    TEST_VERSION: str = Field(default="1.0.0", description="Application version")
    
    # Endpoints:
    API_V1_PREFIX: str = "/api/v1"
    
    # MongoDB Database
    DATABASE_URL: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URL"
    )
    DATABASE_NAME: str = Field(
        default="audiobooker_backend_db",
        description="MongoDB database name"
    )

    # Internal service-to-service auth key (shared with payment service)
    INTERNAL_SERVICE_KEY: str = Field(
        default="change-me-internal-key",
        description="Shared secret used to authenticate inter-service HTTP calls"
    )
    
    # R2 Storage
    R2_ACCOUNT_ID: str = Field(default="", description="Cloudflare account ID")
    R2_ACCESS_KEY_ID: str = Field(default="", description="R2 access key ID")
    R2_SECRET_ACCESS_KEY: str = Field(default="", description="R2 secret access key")
    R2_BUCKET_NAME: str = Field(default="", description="R2 bucket name")
    R2_ENDPOINT_URL: Optional[str] = Field(default=None, description="Custom R2 endpoint")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
        
    # Redis Configuration (for production job queue)
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password")

    # JWT & Auth
    JWT_SECRET_KEY: str = Field(default="change-this-in-production", description="JWT signing secret")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Access token expiry in minutes")

    # File Upload
    MAX_FILE_SIZE_MB: int = Field(default=100, description="Max upload file size in MB")
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment values"""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level"""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v.upper()
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from JSON array string or comma-separated string"""
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    @property
    def redis_url(self) -> str:
        """Construct Redis URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT == "development"
    
    class Config:
        # Locate .env file at the project root (2 levels up from this file)
        env_file = str(Path(__file__).resolve().parent.parent.parent / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Global settings instance
settings = Settings()