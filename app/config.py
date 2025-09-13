"""
Configuration management using Pydantic settings.
Handles database URL, JWT secrets, and environment variables for Docker deployment.
"""

from pydantic import validator
from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings with Docker environment variable support."""
    
    # Application configuration
    app_name: str = "Property Listing API"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    testing: bool = False
    
    # Database configuration - Docker-compatible defaults
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/property_listings"
    
    # Individual database components for flexibility
    postgres_db: str = "property_listings"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_host: str = "db"
    postgres_port: int = 5432
    
    # Test database configuration
    test_postgres_db: str = "property_listings_test"
    test_postgres_user: str = "postgres"
    test_postgres_password: str = "postgres"
    test_postgres_host: str = "test_db"
    test_postgres_port: int = 5432
    
    # JWT configuration
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    
    # File upload configuration - Docker volume compatible
    upload_dir: str = "./uploads"
    test_upload_dir: str = "./test_uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_types: List[str] = ["image/jpeg", "image/png", "image/webp"]
    
    # API configuration
    api_v1_prefix: str = "/api/v1"
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080", "http://localhost:8000"]
    
    # Pagination defaults
    default_page_size: int = 20
    max_page_size: int = 100
    
    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    
    @validator("database_url", pre=True)
    def validate_database_url(cls, v, values):
        """Build database URL from components if not provided directly."""
        if not v or v == "postgresql+asyncpg://postgres:postgres@db:5432/property_listings":
            # Build from individual components
            user = values.get("postgres_user", "postgres")
            password = values.get("postgres_password", "postgres")
            host = values.get("postgres_host", "db")
            port = values.get("postgres_port", 5432)
            db = values.get("postgres_db", "property_listings")
            return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
        
        # Ensure async driver is used
        if v and not v.startswith(("postgresql+asyncpg://", "sqlite+aiosqlite://")):
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    
    @validator("jwt_secret_key", pre=True)
    def validate_jwt_secret_key(cls, v):
        """Validate JWT secret key strength."""
        if not v:
            raise ValueError("JWT_SECRET_KEY is required")
        if len(v) < 32 and v != "your-secret-key-change-in-production":
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        return v
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment setting."""
        allowed_envs = ["development", "testing", "staging", "production"]
        if v not in allowed_envs:
            raise ValueError(f"Environment must be one of: {allowed_envs}")
        return v
    
    @validator("upload_dir", "test_upload_dir", pre=True)
    def create_upload_directories(cls, v):
        """Ensure upload directories exist."""
        if v and not os.path.exists(v):
            os.makedirs(v, exist_ok=True)
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.environment == "testing" or self.testing
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"
    
    @property
    def test_database_url(self) -> str:
        """Get test database URL."""
        return f"postgresql+asyncpg://{self.test_postgres_user}:{self.test_postgres_password}@{self.test_postgres_host}:{self.test_postgres_port}/{self.test_postgres_db}"
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    This ensures we only create one instance of settings throughout the app lifecycle.
    """
    return Settings()


# Global settings instance
settings = get_settings()