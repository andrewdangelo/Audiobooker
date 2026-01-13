"""
Configuration settings for API Proxy
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    PORT: int = 8009
    LOG_LEVEL: str = "INFO"
    TEST_VERSION: str = "Check ENV for test version"
    API_V1_PREFIX: str = "/api/v1/audiobooker_proxy"
    
    # CORS Settings
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # Microservices
    PDF_SERVICE_URL: str = "http://localhost:8029/api/v1/pdf"
    TTS_SERVICE_URL: str = "http://localhost:8002/api/v1/tts"
    AUTH_SERVICE_URL: str = "http://localhost:8003/api/v1/auth"
    
    # Queue Configuration
    MAX_CONCURRENT_PDF: int = 5
    MAX_CONCURRENT_TTS: int = 5
    MAX_CONCURRENT_AUTH: int = 10
    
    # Timeouts (seconds)
    REQUEST_TIMEOUT: int = 30
    UPLOAD_TIMEOUT: int = 120
    
    # Rate Limiting
    RATE_LIMIT_PER_HOUR: int = 1000
    RATE_LIMIT_PER_MINUTE: int = 20
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()