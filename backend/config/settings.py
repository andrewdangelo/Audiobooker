"""
Application Settings
"""

from pydantic_settings import BaseSettings
from typing import Union
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production"
    API_V1_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql://audiobooker:password@localhost:5432/audiobooker_db"
    
    # Cloudflare R2
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "audiobooker-storage"
    R2_ENDPOINT_URL: str = ""
    
    # CORS
    CORS_ORIGINS: Union[list[str], str] = "http://localhost:5173,http://localhost:5175,http://localhost:3000"
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB
    ALLOWED_EXTENSIONS: Union[list[str], str] = ".pdf"
    UPLOAD_DIR: str = "uploads"
    
    @field_validator('ALLOWED_EXTENSIONS', mode='before')
    @classmethod
    def parse_allowed_extensions(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(',')]
        return v
    
    # TTS
    TTS_PROVIDER: str = "openai"
    TTS_API_KEY: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
