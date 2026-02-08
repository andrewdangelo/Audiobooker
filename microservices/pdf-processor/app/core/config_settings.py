"""
App + env Configuration Management

Using Pydantic Settings, Will Automatically Load from environment variables with validation.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional
from pathlib import Path


class Settings(BaseSettings):
    """Base Clase for Application Settings"""
    
    # Environment
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    PORT: int = Field(default=8001, description="Service port")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    DEBUG: bool = True
    TEST_VERSION: str = Field(default="Check ENV Version...", description="Application test version")
    
    # Endpoints:
    API_V1_PREFIX: str = "/api/v1/pdf"
    
    # MongoDB Database
    DATABASE_URL: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URL"
    )
    DATABASE_NAME: str = Field(
        default="audiobooker_pdf_processing_db",
        description="MongoDB database name"
    )
    
    # R2 Storage
    R2_ACCOUNT_ID: str = Field(..., description="Cloudflare account ID")
    R2_ACCESS_KEY_ID: str = Field(..., description="R2 access key ID")
    R2_SECRET_ACCESS_KEY: str = Field(..., description="R2 secret access key")
    R2_BUCKET_NAME: str = Field(..., description="R2 bucket name")
    R2_ENDPOINT_URL: Optional[str] = Field(default=None, description="Custom R2 endpoint")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    
    # Processing Configuration
    DEFAULT_CHUNK_SIZE: int = Field(default=1000, description="Default text chunk size")
    DEFAULT_CHUNK_OVERLAP: int = Field(default=200, description="Default chunk overlap")
    MAX_FILE_SIZE_MB: int = Field(default=100, description="Maximum file size in MB")
    
    # Redis Configuration (for production job queue) #TODO should add to env for LATER USE
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password")
    
    # LLM Configuration (for speaker chunking)
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key for LLM chunking")
    LLM_MODEL: str = Field(default="gpt-4o", description="OpenAI model for speaker chunking")
    LLM_CONCURRENCY: int = Field(default=1, description="Number of concurrent LLM requests (1 recommended for rate limits)")
    LLM_MAX_CHARS_PER_WINDOW: int = Field(default=15000, description="Maximum characters per LLM processing window (reduced for rate limits)")
    LLM_DISCOVERY_CHARS: int = Field(default=20000, description="Characters to use for character discovery")
    LLM_DELAY_BETWEEN_REQUESTS: float = Field(default=3.0, description="Seconds to wait between LLM requests")
    ENABLE_LLM_CHUNKING: bool = Field(default=False, description="Enable automatic LLM-based speaker chunking")
    
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
    
    @validator("MAX_FILE_SIZE_MB")
    def validate_max_file_size(cls, v):
        """Validate maximum file size"""
        if v <= 0 or v > 500:
            raise ValueError("MAX_FILE_SIZE_MB must be between 1 and 500")
        return v
    
    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes"""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
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