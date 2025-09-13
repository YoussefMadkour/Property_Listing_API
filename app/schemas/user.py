"""
Pydantic schemas for user requests and responses.
Handles user creation, updates, and validation with email validation.
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from app.models.user import UserRole


class UserBase(BaseModel):
    """Base user schema with common fields."""
    
    email: EmailStr = Field(
        ...,
        description="User's email address",
        example="agent@example.com"
    )
    
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="User's full name",
        example="John Doe"
    )
    
    @validator('email')
    def normalize_email(cls, v):
        """Normalize email to lowercase."""
        return v.lower().strip()
    
    @validator('full_name')
    def validate_full_name(cls, v):
        """Validate and clean full name."""
        if not v or not v.strip():
            raise ValueError("Full name cannot be empty")
        
        # Check for minimum meaningful content
        name_parts = v.strip().split()
        if len(name_parts) < 2:
            raise ValueError("Full name must include at least first and last name")
        
        return v.strip()


class UserCreate(UserBase):
    """Schema for creating a new user."""
    
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User's password (minimum 8 characters)",
        example="securepassword123"
    )
    
    role: Optional[UserRole] = Field(
        UserRole.AGENT,
        description="User's role (default: agent)",
        example="agent"
    )
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Check for at least one letter and one number
        has_letter = any(c.isalpha() for c in v)
        has_number = any(c.isdigit() for c in v)
        
        if not has_letter:
            raise ValueError("Password must contain at least one letter")
        
        if not has_number:
            raise ValueError("Password must contain at least one number")
        
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "email": "agent@example.com",
                "full_name": "John Doe",
                "password": "securepassword123",
                "role": "agent"
            }
        }


class UserUpdate(BaseModel):
    """Schema for updating an existing user."""
    
    email: Optional[EmailStr] = Field(
        None,
        description="User's email address"
    )
    
    full_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=255,
        description="User's full name"
    )
    
    password: Optional[str] = Field(
        None,
        min_length=8,
        max_length=128,
        description="User's new password (minimum 8 characters)"
    )
    
    role: Optional[UserRole] = Field(
        None,
        description="User's role (admin only)"
    )
    
    is_active: Optional[bool] = Field(
        None,
        description="Whether the user account is active (admin only)"
    )
    
    @validator('email')
    def normalize_email(cls, v):
        """Normalize email to lowercase."""
        if v is not None:
            return v.lower().strip()
        return v
    
    @validator('full_name')
    def validate_full_name(cls, v):
        """Validate and clean full name."""
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Full name cannot be empty")
            
            # Check for minimum meaningful content
            name_parts = v.strip().split()
            if len(name_parts) < 2:
                raise ValueError("Full name must include at least first and last name")
            
            return v.strip()
        return v
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if v is not None:
            if len(v) < 8:
                raise ValueError("Password must be at least 8 characters long")
            
            # Check for at least one letter and one number
            has_letter = any(c.isalpha() for c in v)
            has_number = any(c.isdigit() for c in v)
            
            if not has_letter:
                raise ValueError("Password must contain at least one letter")
            
            if not has_number:
                raise ValueError("Password must contain at least one number")
        
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "full_name": "John Smith",
                "email": "johnsmith@example.com"
            }
        }


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


class UserListResponse(BaseModel):
    """Schema for paginated user list response."""
    
    users: List[UserResponse] = Field(
        ...,
        description="List of users"
    )
    
    total: int = Field(
        ...,
        description="Total number of users matching the criteria",
        example=50
    )
    
    page: int = Field(
        ...,
        description="Current page number",
        example=1
    )
    
    page_size: int = Field(
        ...,
        description="Number of users per page",
        example=20
    )
    
    total_pages: int = Field(
        ...,
        description="Total number of pages",
        example=3
    )
    
    has_next: bool = Field(
        ...,
        description="Whether there are more pages",
        example=True
    )
    
    has_previous: bool = Field(
        ...,
        description="Whether there are previous pages",
        example=False
    )


class UserFilters(BaseModel):
    """Schema for user search and filtering."""
    
    # Search query
    query: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Search query for name and email",
        example="john"
    )
    
    # Role filter
    role: Optional[UserRole] = Field(
        None,
        description="Filter by user role",
        example="agent"
    )
    
    # Status filter
    is_active: Optional[bool] = Field(
        None,
        description="Filter by active status",
        example=True
    )
    
    # Pagination
    page: int = Field(
        1,
        ge=1,
        description="Page number (starts from 1)",
        example=1
    )
    
    page_size: int = Field(
        20,
        ge=1,
        le=100,
        description="Number of users per page (max 100)",
        example=20
    )
    
    # Sorting
    sort_by: Optional[str] = Field(
        "created_at",
        description="Sort field (created_at, updated_at, email, full_name)",
        example="email"
    )
    
    sort_order: Optional[str] = Field(
        "desc",
        description="Sort order (asc or desc)",
        example="asc"
    )
    
    @validator('sort_by')
    def validate_sort_by(cls, v):
        """Validate sort field."""
        allowed_fields = ['created_at', 'updated_at', 'email', 'full_name', 'role']
        if v not in allowed_fields:
            raise ValueError(f"Sort field must be one of: {', '.join(allowed_fields)}")
        return v
    
    @validator('sort_order')
    def validate_sort_order(cls, v):
        """Validate sort order."""
        if v.lower() not in ['asc', 'desc']:
            raise ValueError("Sort order must be 'asc' or 'desc'")
        return v.lower()
    
    class Config:
        schema_extra = {
            "example": {
                "role": "agent",
                "is_active": True,
                "page": 1,
                "page_size": 20,
                "sort_by": "email",
                "sort_order": "asc"
            }
        }


class UserSummary(BaseModel):
    """Schema for user summary (minimal information)."""
    
    id: str = Field(
        ...,
        description="User's unique identifier"
    )
    
    email: EmailStr = Field(
        ...,
        description="User's email address"
    )
    
    full_name: str = Field(
        ...,
        description="User's full name"
    )
    
    role: UserRole = Field(
        ...,
        description="User's role"
    )
    
    is_active: bool = Field(
        ...,
        description="Whether the user is active"
    )
    
    class Config:
        from_attributes = True


class PasswordChangeRequest(BaseModel):
    """Schema for password change request."""
    
    current_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Current password",
        example="currentpassword123"
    )
    
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (minimum 8 characters)",
        example="newpassword123"
    )
    
    confirm_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Confirm new password",
        example="newpassword123"
    )
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Check for at least one letter and one number
        has_letter = any(c.isalpha() for c in v)
        has_number = any(c.isdigit() for c in v)
        
        if not has_letter:
            raise ValueError("Password must contain at least one letter")
        
        if not has_number:
            raise ValueError("Password must contain at least one number")
        
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Validate that passwords match."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError("Passwords do not match")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "current_password": "currentpassword123",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123"
            }
        }


class UserStatsResponse(BaseModel):
    """Schema for user statistics response."""
    
    total_users: int = Field(
        ...,
        description="Total number of users",
        example=100
    )
    
    active_users: int = Field(
        ...,
        description="Number of active users",
        example=95
    )
    
    agents_count: int = Field(
        ...,
        description="Number of agent users",
        example=85
    )
    
    admins_count: int = Field(
        ...,
        description="Number of admin users",
        example=15
    )
    
    recent_registrations: int = Field(
        ...,
        description="Number of users registered in the last 30 days",
        example=10
    )