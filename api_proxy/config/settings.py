"""
API Proxy Configuration Settings
"""

from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "Audiobooker API Gateway"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    # Microservice URLs
    PDF_PROCESSOR_URL: str = "http://localhost:8001"
    TTS_SERVICE_URL: str = "http://localhost:8002"
    BACKEND_SERVICE_URL: str = "http://localhost:8003"
    STORAGE_SERVICE_URL: str = "http://localhost:8004"
    AUTH_SERVICE_URL: str = "http://localhost:8005"
    
    # Timeouts (seconds)
    REQUEST_TIMEOUT: int = 30
    UPLOAD_TIMEOUT: int = 120
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # seconds
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from environment


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
