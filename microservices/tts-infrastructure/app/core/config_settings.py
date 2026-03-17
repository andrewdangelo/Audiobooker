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
    PORT: int = Field(default=8002, description="Service port")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    DEBUG: bool = True
    TEST_VERSION: str = Field(default="Check ENV Version...", description="Application test version")
    API_V1_PREFIX: str = Field(...)
    
    # Database
    # DATABASE_URL: str = "postgresql://audiobooker:password@localhost:5432/audiobooker_db"
    MONGODB_URL: str = Field(..., description="MongoDB URL")
    
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
    
    # Redis Configuration (for production job queue) #TODO should add to env for LATER USE
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password")

    # Processing Configuration
    DEFAULT_CHUNK_SIZE: int = Field(default=1000)
    DEFAULT_CHUNK_OVERLAP: int = Field(default=200)
    MAX_FILE_SIZE_MB: int = Field(default=100)

    ENABLE_LLM_CHUNKING: bool = Field(default=True, description="Huggingface LLM endpoint URL")

    HF_ENDPOINT_URL: str = Field(..., description="Huggingface LLM endpoint URL")
    HF_TOKEN: str = Field(..., description="Huggingface Token")
    HF_WRITE_TOKEN: str = Field(..., description="Huggingface token for writes")
    HF_NAMESPACE: str = Field(..., description="Huggingface namespace for inference endpoints")

    LLM_SERVERLESS: bool = Field(default=True)
    LLM_MODEL: str = Field(default="FruitClamp/qwen-finetuned", description="Huggingface LLM Model name")
    LLM_CONCURRENCY: int = Field(default=10)
    LLM_MAX_CHARS_PER_WINDOW: int = Field(default=20000)
    LLM_DISCOVERY_CHARS: int = Field(default=17000)
    LLM_DELAY_BETWEEN_REQUESTS: float = Field(default=2.0)
    LLM_ENDPOINT_NAME: str = Field(default="qwen-finetuned-001")
    
    TTS_CONCURRENCY: int = Field(default=1)
    # Settings-like values
    # LLM_MAX_TOKENS: int = Field(default=4096)
    # LLM_TEMPERATURE: int = Field(default=0.2)

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