"""
Configuration settings for API Proxy
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    ENVIRONMENT: str = "development"
    PORT: int = 8009
    LOG_LEVEL: str = "INFO"
    TEST_VERSION: str = "Check ENV for test version"
    API_V1_PREFIX: str = "/api/v1/audiobooker_proxy"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # Microservices
    PDF_SERVICE_URL: str = "http://localhost:8029/api/v1/pdf"
    TTS_SERVICE_URL: str = "http://localhost:8002/api/v1/tts"
    
    # Queue Configuration
    MAX_CONCURRENT_PDF: int = 5
    MAX_CONCURRENT_TTS: int = 5
    
    # Rate Limiting
    RATE_LIMIT_PER_HOUR: int = 1000
    RATE_LIMIT_PER_MINUTE: int = 20
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()