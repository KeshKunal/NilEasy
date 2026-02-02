"""
app/core/config.py

Purpose: Application configuration

- Loads environment variables
- Centralizes config values (DB URI, secrets, etc.)
- Validates configuration on startup
- Environment-specific settings
"""

from pydantic import Field, validator
from pydantic_settings import BaseSettings
from typing import Optional, Literal


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Validates all required configs on startup.
    """
    
    # Environment
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    
    # MongoDB
    MONGODB_URL: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URI"
    )
    MONGODB_DB_NAME: str = Field(
        default="nileasy",
        description="MongoDB database name"
    )
    
    # WhatsApp/AiSensy
    AISENSY_API_KEY: Optional[str] = Field(
        default=None,
        description="AiSensy API key for WhatsApp integration"
    )
    AISENSY_WEBHOOK_SECRET: Optional[str] = Field(
        default=None,
        description="Webhook signature verification secret"
    )
    AISENSY_BASE_URL: str = Field(
        default="https://backend.aisensy.com",
        description="AiSensy API base URL"
    )
    
    # GST Verification Service (Your existing tool)
    GST_SERVICE_URL: str = Field(
        default="http://localhost:5001",
        description="GST verification service base URL"
    )
    GST_SERVICE_TIMEOUT: int = Field(
        default=30,
        description="GST service request timeout in seconds"
    )
    
    # SMS Short Link Service
    SMS_SHORTLINK_API_URL: str = Field(
        default="https://sm-snacc.vercel.app",
        description="SMS short link service URL"
    )
    APP_URL: str = Field(
        default="http://localhost:8000",
        description="Your FastAPI app base URL (for OTP callback redirects)"
    )
    
    # Session Management
    SESSION_TIMEOUT_MINUTES: int = Field(
        default=30,
        description="User session timeout in minutes"
    )
    MAX_RETRY_ATTEMPTS: int = Field(
        default=3,
        description="Maximum retry attempts per step"
    )
    
    # Rate Limiting
    RATE_LIMIT_MESSAGES_PER_MINUTE: int = Field(
        default=5,
        description="Maximum messages per user per minute"
    )
    RATE_LIMIT_GSTIN_LOOKUPS_PER_HOUR: int = Field(
        default=10,
        description="Maximum GSTIN lookups per user per hour"
    )
    
    # Application
    DEBUG: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    API_PREFIX: str = Field(
        default="/api/v1",
        description="API route prefix"
    )
    CORS_ORIGINS: list = Field(
        default=["*"],
        description="Allowed CORS origins"
    )
    
    # Security
    SECRET_KEY: str = Field(
        default="change-me-in-production",
        description="Application secret key for encryption"
    )
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v, values):
        """Ensure secret key is changed in production."""
        if values.get("ENVIRONMENT") == "production" and v == "change-me-in-production":
            raise ValueError("SECRET_KEY must be changed in production environment")
        return v
    
    @validator("AISENSY_API_KEY")
    def validate_aisensy_key(cls, v, values):
        """Ensure AiSensy key is set in production."""
        if values.get("ENVIRONMENT") == "production" and not v:
            raise ValueError("AISENSY_API_KEY is required in production environment")
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT == "production"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()


def validate_settings():
    """
    Validates critical settings on application startup.
    Raises ValueError if any required setting is missing or invalid.
    """
    errors = []
    
    # Validate MongoDB URI
    if not settings.MONGODB_URI:
        errors.append("MONGODB_URI is required")
    
    # Validate GST service URL
    if not settings.GST_SERVICE_URL:
        errors.append("GST_SERVICE_URL is required")
    
    # Production-specific validations
    if settings.is_production:
        if not settings.AISENSY_API_KEY:
            errors.append("AISENSY_API_KEY is required in production")
        if not settings.AISENSY_WEBHOOK_SECRET:
            errors.append("AISENSY_WEBHOOK_SECRET is required in production")
    
    if errors:
        raise ValueError(f"Configuration validation failed: {', '.join(errors)}")
    
    return True
