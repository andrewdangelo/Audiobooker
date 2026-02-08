"""
App + env Configuration Management

Using Pydantic Settings, Will Automatically Load from environment variables with validation.
"""

__author__ = "Mohammad Saifan"

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional
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
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        """Validate environment values"""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level"""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v.upper()
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
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


# Global settings instance
settings = Settings()