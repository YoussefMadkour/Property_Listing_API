"""
Pydantic schemas for authentication requests and responses.
Handles login, token refresh, and user authentication data validation.
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from app.models.user import UserRole
from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    """Login request schema."""
    
    email: EmailStr = Field(
        ...,
        description="User's email address",
        example="agent@example.com"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User's password (minimum 8 characters)",
        example="securepassword123"
    )
    
    @validator('email')
    def normalize_email(cls, v):
        """Normalize email to lowercase."""
        return v.lower().strip()


class TokenResponse(BaseModel):
    """Token response schema."""
    
    access_token: str = Field(
        ...,
        description="JWT access token",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    token_type: str = Field(
        default="bearer",
        description="Token type",
        example="bearer"
    )
    expires_in: int = Field(
        ...,
        description="Access token expiration time in seconds",
        example=1800
    )


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    
    refresh_token: str = Field(
        ...,
        description="Valid refresh token",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )


class AccessTokenResponse(BaseModel):
    """Access token response schema."""
    
    access_token: str = Field(
        ...,
        description="New JWT access token",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    token_type: str = Field(
        default="bearer",
        description="Token type",
        example="bearer"
    )
    expires_in: int = Field(
        ...,
        description="Access token expiration time in seconds",
        example=1800
    )


class UserResponse(BaseModel):
    """User response schema (excluding sensitive data)."""
    
    id: str = Field(
        ...,
        description="User's unique identifier",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    email: EmailStr = Field(
        ...,
        description="User's email address",
        example="agent@example.com"
    )
    full_name: str = Field(
        ...,
        description="User's full name",
        example="John Doe"
    )
    role: UserRole = Field(
        ...,
        description="User's role",
        example="agent"
    )
    is_active: bool = Field(
        ...,
        description="Whether the user account is active",
        example=True
    )
    created_at: datetime = Field(
        ...,
        description="Account creation timestamp",
        example="2023-01-01T00:00:00Z"
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp",
        example="2023-01-01T00:00:00Z"
    )
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CurrentUserResponse(UserResponse):
    """Current user response with additional context."""
    
    permissions: list[str] = Field(
        default_factory=list,
        description="User's permissions based on role",
        example=["create_property", "update_own_property", "delete_own_property"]
    )
    
    @validator('permissions', pre=True, always=True)
    def set_permissions(cls, v, values):
        """Set permissions based on user role."""
        role = values.get('role')
        if role == UserRole.ADMIN:
            return [
                "create_property",
                "update_any_property",
                "delete_any_property",
                "manage_users",
                "view_all_properties"
            ]
        elif role == UserRole.AGENT:
            return [
                "create_property",
                "update_own_property",
                "delete_own_property",
                "view_own_properties"
            ]
        return []


class LoginResponse(BaseModel):
    """Complete login response schema."""
    
    user: CurrentUserResponse = Field(
        ...,
        description="Authenticated user information"
    )
    access_token: str = Field(
        ...,
        description="JWT access token",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    token_type: str = Field(
        default="bearer",
        description="Token type",
        example="bearer"
    )
    expires_in: int = Field(
        ...,
        description="Access token expiration time in seconds",
        example=1800
    )


class TokenValidationResponse(BaseModel):
    """Token validation response schema."""
    
    valid: bool = Field(
        ...,
        description="Whether the token is valid",
        example=True
    )
    user_id: Optional[str] = Field(
        None,
        description="User ID if token is valid",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    email: Optional[EmailStr] = Field(
        None,
        description="User email if token is valid",
        example="agent@example.com"
    )
    role: Optional[UserRole] = Field(
        None,
        description="User role if token is valid",
        example="agent"
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Token expiration time",
        example="2023-01-01T01:00:00Z"
    )