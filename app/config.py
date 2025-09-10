"""
Configuration management using Pydantic settings.
Handles database URL, JWT secrets, and environment variables.
"""

from pydantic import BaseSettings, validator
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Database configuration
    database_url: str = "postgresql+asyncpg://user:password@localhost/property_listing_db"
    database_url_sync: str = "postgresql://user:password@localhost/property_listing_db"
    
    # JWT configuration
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    
    # Application configuration
    app_name: str = "Property Listing API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # File upload configuration
    upload_directory: str = "uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_image_types: list = ["image/jpeg", "image/png", "image/webp"]
    
    # API configuration
    api_v1_prefix: str = "/api/v1"
    cors_origins: list = ["http://localhost:3000", "http://localhost:8080"]
    
    # Pagination defaults
    default_page_size: int = 20
    max_page_size: int = 100
    
    @validator("database_url", pre=True)
    def validate_database_url(cls, v):
        """Ensure database URL is properly formatted for async operations."""
        if v and not v.startswith(("postgresql+asyncpg://", "sqlite+aiosqlite://")):
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    
    @validator("upload_directory", pre=True)
    def create_upload_directory(cls, v):
        """Ensure upload directory exists."""
        if v and not os.path.exists(v):
            os.makedirs(v, exist_ok=True)
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()