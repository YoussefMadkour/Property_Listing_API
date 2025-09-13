"""
Pydantic schemas for request/response validation.
"""

# Authentication schemas
from .auth import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    AccessTokenResponse,
    CurrentUserResponse,
    LoginResponse,
    TokenValidationResponse
)

# User schemas
from .user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    UserFilters,
    UserSummary,
    PasswordChangeRequest,
    UserStatsResponse
)

# Property schemas
from .property import (
    PropertyBase,
    PropertyCreate,
    PropertyUpdate,
    PropertyResponse,
    PropertyListResponse,
    PropertySearchFilters,
    PropertySummary
)

# Image schemas
from .image import (
    PropertyImageBase,
    PropertyImageCreate,
    PropertyImageUpdate,
    PropertyImageResponse,
    PropertyImageListResponse,
    ImageUploadResponse,
    MultipleImageUploadResponse,
    ImageValidationError,
    ImageProcessingStatus,
    ImageFilters,
    ImageSummary
)

__all__ = [
    # Authentication
    "LoginRequest",
    "TokenResponse", 
    "RefreshTokenRequest",
    "AccessTokenResponse",
    "CurrentUserResponse",
    "LoginResponse",
    "TokenValidationResponse",
    
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserListResponse",
    "UserFilters",
    "UserSummary",
    "PasswordChangeRequest",
    "UserStatsResponse",
    
    # Property
    "PropertyBase",
    "PropertyCreate",
    "PropertyUpdate",
    "PropertyResponse",
    "PropertyListResponse",
    "PropertySearchFilters",
    "PropertySummary",
    
    # Image
    "PropertyImageBase",
    "PropertyImageCreate",
    "PropertyImageUpdate",
    "PropertyImageResponse",
    "PropertyImageListResponse",
    "ImageUploadResponse",
    "MultipleImageUploadResponse",
    "ImageValidationError",
    "ImageProcessingStatus",
    "ImageFilters",
    "ImageSummary"
]