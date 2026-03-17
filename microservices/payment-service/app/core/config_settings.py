"""
Payment Service Configuration Management

Using Pydantic Settings for environment variable management with validation.
Supports both development (Stripe sandbox) and production modes.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List, Optional
from pathlib import Path

# Get the directory where this config file is located
CONFIG_DIR = Path(__file__).resolve().parent
# Go up to payment-service root
SERVICE_DIR = CONFIG_DIR.parent.parent


class Settings(BaseSettings):
    """Base Settings for Payment Service"""
    
    model_config = SettingsConfigDict(
        env_file=str(SERVICE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # Environment
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    PORT: int = Field(default=8004, description="Service port")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    DEBUG: bool = True
    TEST_VERSION: str = Field(default="1.0.0", description="Application version")
    
    # Endpoints
    API_V1_PREFIX: str = "/api/v1/payment"
    
    # MongoDB Configuration - Payment database
    MONGODB_URL: str = Field(default="mongodb://localhost:27017", description="MongoDB connection URL")
    MONGODB_DB_NAME: str = Field(default="audiobooker_payment", description="MongoDB database name for payments")
    MONGODB_MAX_POOL_SIZE: int = Field(default=10, description="Maximum connection pool size")
    MONGODB_MIN_POOL_SIZE: int = Field(default=1, description="Minimum connection pool size")
    
    # Auth Service MongoDB (for user lookups)
    AUTH_MONGODB_URL: str = Field(default="mongodb://localhost:27017", description="Auth MongoDB connection URL")
    AUTH_MONGODB_DB_NAME: str = Field(default="audiobooker_auth", description="Auth MongoDB database name")
    
    # Stripe Configuration
    # In development, use test keys from Stripe dashboard (sk_test_*, pk_test_*)
    # In production, use live keys (sk_live_*, pk_live_*)
    STRIPE_SECRET_KEY: str = Field(default="", description="Stripe Secret Key (sk_test_* for sandbox, sk_live_* for production)")
    STRIPE_PUBLISHABLE_KEY: str = Field(default="", description="Stripe Publishable Key (pk_test_* for sandbox, pk_live_* for production)")
    STRIPE_WEBHOOK_SECRET: str = Field(default="", description="Stripe Webhook Signing Secret (whsec_*)")
    
    # Stripe Settings
    STRIPE_API_VERSION: str = Field(default="2023-10-16", description="Stripe API version")
    STRIPE_CURRENCY: str = Field(default="usd", description="Default currency for payments")
    
    # Payment Settings
    PAYMENT_SUCCESS_URL: str = Field(default="http://localhost:5173/checkout/success", description="URL to redirect after successful payment")
    PAYMENT_CANCEL_URL: str = Field(default="http://localhost:5173/checkout/cancel", description="URL to redirect after cancelled payment")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    
    # JWT Configuration (for validating tokens from auth service)
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production", description="Secret key for JWT verification")
    ALGORITHM: str = Field(default="HS256", description="Algorithm for JWT verification")
    
    # Auth Service URL (for user validation)
    AUTH_SERVICE_URL: str = Field(default="http://localhost:8003/api/v1/auth", description="Auth Service URL")
    
    # Redis Configuration (optional, for caching)
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.ENVIRONMENT.lower() in ("development", "dev", "local")
    
    @property
    def is_sandbox_mode(self) -> bool:
        """Check if Stripe is in sandbox/test mode"""
        if not self.STRIPE_SECRET_KEY:
            return True
        return self.STRIPE_SECRET_KEY.startswith("sk_test_")
    
    def validate_stripe_keys(self) -> bool:
        """Validate that Stripe keys match the environment"""
        if not self.STRIPE_SECRET_KEY or not self.STRIPE_PUBLISHABLE_KEY:
            return False
        
        # Both keys should be either test or live
        secret_is_test = self.STRIPE_SECRET_KEY.startswith("sk_test_")
        publish_is_test = self.STRIPE_PUBLISHABLE_KEY.startswith("pk_test_")
        
        return secret_is_test == publish_is_test


settings = Settings()
