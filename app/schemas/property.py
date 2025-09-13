"""
Pydantic schemas for property requests and responses.
Handles property CRUD operations, search filters, and validation.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.models.property import PropertyType
from app.schemas.user import UserResponse
from app.schemas.image import PropertyImageResponse


class PropertyBase(BaseModel):
    """Base property schema with common fields."""
    
    title: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Property listing title",
        example="Beautiful 3BR Apartment in Downtown"
    )
    
    description: str = Field(
        ...,
        min_length=20,
        max_length=5000,
        description="Detailed property description",
        example="Spacious apartment with modern amenities, great location near shopping and transport."
    )
    
    property_type: PropertyType = Field(
        ...,
        description="Property type - rental or sale",
        example="rental"
    )
    
    price: Decimal = Field(
        ...,
        gt=0,
        description="Property price in local currency",
        example=2500.00
    )
    
    bedrooms: int = Field(
        ...,
        ge=0,
        le=50,
        description="Number of bedrooms",
        example=3
    )
    
    bathrooms: int = Field(
        ...,
        ge=0,
        le=50,
        description="Number of bathrooms",
        example=2
    )
    
    area_sqft: int = Field(
        ...,
        gt=0,
        le=1000000,
        description="Property area in square feet",
        example=1200
    )
    
    location: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Property location/address",
        example="Downtown Dubai, UAE"
    )
    
    latitude: Optional[Decimal] = Field(
        None,
        ge=-90,
        le=90,
        description="Property latitude coordinate",
        example=25.2048493
    )
    
    longitude: Optional[Decimal] = Field(
        None,
        ge=-180,
        le=180,
        description="Property longitude coordinate",
        example=55.2707828
    )
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Validate and clean title."""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        """Validate and clean description."""
        if not v or not v.strip():
            raise ValueError("Description cannot be empty")
        return v.strip()
    
    @field_validator('location')
    @classmethod
    def validate_location(cls, v):
        """Validate and clean location."""
        if not v or not v.strip():
            raise ValueError("Location cannot be empty")
        return v.strip()
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v):
        """Validate price value."""
        if v <= 0:
            raise ValueError("Price must be greater than 0")
        if v > Decimal('999999999.99'):
            raise ValueError("Price exceeds maximum allowed value")
        return v
    
    @model_validator(mode='after')
    def validate_coordinates(self):
        """Validate that both coordinates are provided together or both are None."""
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Both latitude and longitude must be provided together, or both must be None")
        return self


class PropertyCreate(PropertyBase):
    """Schema for creating a new property."""
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Beautiful 3BR Apartment in Downtown",
                "description": "Spacious apartment with modern amenities, great location near shopping and transport. Features include hardwood floors, updated kitchen, and balcony with city views.",
                "property_type": "rental",
                "price": 2500.00,
                "bedrooms": 3,
                "bathrooms": 2,
                "area_sqft": 1200,
                "location": "Downtown Dubai, UAE",
                "latitude": 25.2048493,
                "longitude": 55.2707828
            }
        }


class PropertyUpdate(BaseModel):
    """Schema for updating an existing property."""
    
    title: Optional[str] = Field(
        None,
        min_length=5,
        max_length=255,
        description="Property listing title"
    )
    
    description: Optional[str] = Field(
        None,
        min_length=20,
        max_length=5000,
        description="Detailed property description"
    )
    
    property_type: Optional[PropertyType] = Field(
        None,
        description="Property type - rental or sale"
    )
    
    price: Optional[Decimal] = Field(
        None,
        gt=0,
        description="Property price in local currency"
    )
    
    bedrooms: Optional[int] = Field(
        None,
        ge=0,
        le=50,
        description="Number of bedrooms"
    )
    
    bathrooms: Optional[int] = Field(
        None,
        ge=0,
        le=50,
        description="Number of bathrooms"
    )
    
    area_sqft: Optional[int] = Field(
        None,
        gt=0,
        le=1000000,
        description="Property area in square feet"
    )
    
    location: Optional[str] = Field(
        None,
        min_length=5,
        max_length=255,
        description="Property location/address"
    )
    
    latitude: Optional[Decimal] = Field(
        None,
        ge=-90,
        le=90,
        description="Property latitude coordinate"
    )
    
    longitude: Optional[Decimal] = Field(
        None,
        ge=-180,
        le=180,
        description="Property longitude coordinate"
    )
    
    is_active: Optional[bool] = Field(
        None,
        description="Whether the property listing is active"
    )
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Validate and clean title."""
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Title cannot be empty")
            return v.strip()
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        """Validate and clean description."""
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Description cannot be empty")
            return v.strip()
        return v
    
    @field_validator('location')
    @classmethod
    def validate_location(cls, v):
        """Validate and clean location."""
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Location cannot be empty")
            return v.strip()
        return v
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v):
        """Validate price value."""
        if v is not None:
            if v <= 0:
                raise ValueError("Price must be greater than 0")
            if v > Decimal('999999999.99'):
                raise ValueError("Price exceeds maximum allowed value")
        return v
    
    @model_validator(mode='after')
    def validate_coordinates(self):
        """Validate that both coordinates are provided together or both are None."""
        # Only validate if at least one coordinate is provided
        if self.latitude is not None or self.longitude is not None:
            if (self.latitude is None) != (self.longitude is None):
                raise ValueError("Both latitude and longitude must be provided together, or both must be None")
        return self
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Updated Beautiful 3BR Apartment",
                "price": 2750.00,
                "is_active": True
            }
        }


class PropertyResponse(PropertyBase):
    """Schema for property response with additional metadata."""
    
    id: str = Field(
        ...,
        description="Property unique identifier",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    agent_id: str = Field(
        ...,
        description="ID of the agent who owns this property",
        example="123e4567-e89b-12d3-a456-426614174001"
    )
    
    is_active: bool = Field(
        ...,
        description="Whether the property listing is active",
        example=True
    )
    
    created_at: datetime = Field(
        ...,
        description="Property creation timestamp",
        example="2023-01-01T00:00:00Z"
    )
    
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp",
        example="2023-01-01T00:00:00Z"
    )
    
    # Optional related data
    agent: Optional[UserResponse] = Field(
        None,
        description="Agent information (if included)"
    )
    
    images: Optional[List[PropertyImageResponse]] = Field(
        default_factory=list,
        description="Property images (if included)"
    )
    
    image_count: Optional[int] = Field(
        None,
        description="Total number of images for this property"
    )
    
    primary_image: Optional[PropertyImageResponse] = Field(
        None,
        description="Primary image for this property"
    )
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


class PropertyListResponse(BaseModel):
    """Schema for paginated property list response."""
    
    properties: List[PropertyResponse] = Field(
        ...,
        description="List of properties"
    )
    
    total: int = Field(
        ...,
        description="Total number of properties matching the criteria",
        example=150
    )
    
    page: int = Field(
        ...,
        description="Current page number",
        example=1
    )
    
    page_size: int = Field(
        ...,
        description="Number of properties per page",
        example=20
    )
    
    total_pages: int = Field(
        ...,
        description="Total number of pages",
        example=8
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


class PropertySearchFilters(BaseModel):
    """Schema for property search filters with optional parameters."""
    
    # Search query
    query: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Search query for title and description",
        example="apartment downtown"
    )
    
    # Location filters
    location: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Location filter",
        example="Dubai"
    )
    
    # Price filters
    min_price: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Minimum price filter",
        example=1000.00
    )
    
    max_price: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Maximum price filter",
        example=5000.00
    )
    
    # Property specification filters
    bedrooms: Optional[int] = Field(
        None,
        ge=0,
        le=50,
        description="Minimum number of bedrooms",
        example=2
    )
    
    bathrooms: Optional[int] = Field(
        None,
        ge=0,
        le=50,
        description="Minimum number of bathrooms",
        example=1
    )
    
    min_area: Optional[int] = Field(
        None,
        gt=0,
        le=1000000,
        description="Minimum area in square feet",
        example=800
    )
    
    max_area: Optional[int] = Field(
        None,
        gt=0,
        le=1000000,
        description="Maximum area in square feet",
        example=2000
    )
    
    # Property type filter
    property_type: Optional[PropertyType] = Field(
        None,
        description="Property type filter",
        example="rental"
    )
    
    # Status filter
    is_active: Optional[bool] = Field(
        True,
        description="Filter by active status (default: True)",
        example=True
    )
    
    # Agent filter (for admin users)
    agent_id: Optional[str] = Field(
        None,
        description="Filter by agent ID (admin only)",
        example="123e4567-e89b-12d3-a456-426614174001"
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
        description="Number of properties per page (max 100)",
        example=20
    )
    
    # Sorting
    sort_by: Optional[str] = Field(
        "created_at",
        description="Sort field (created_at, updated_at, price, bedrooms, area_sqft)",
        example="price"
    )
    
    sort_order: Optional[str] = Field(
        "desc",
        description="Sort order (asc or desc)",
        example="asc"
    )
    
    @field_validator('min_price', 'max_price')
    @classmethod
    def validate_prices(cls, v):
        """Validate price values."""
        if v is not None and v < 0:
            raise ValueError("Price cannot be negative")
        return v
    
    @field_validator('sort_by')
    @classmethod
    def validate_sort_by(cls, v):
        """Validate sort field."""
        allowed_fields = ['created_at', 'updated_at', 'price', 'bedrooms', 'bathrooms', 'area_sqft', 'title']
        if v not in allowed_fields:
            raise ValueError(f"Sort field must be one of: {', '.join(allowed_fields)}")
        return v
    
    @field_validator('sort_order')
    @classmethod
    def validate_sort_order(cls, v):
        """Validate sort order."""
        if v.lower() not in ['asc', 'desc']:
            raise ValueError("Sort order must be 'asc' or 'desc'")
        return v.lower()
    
    @model_validator(mode='after')
    def validate_ranges(self):
        """Validate price and area ranges."""
        # Validate price range
        if self.min_price is not None and self.max_price is not None:
            if self.min_price > self.max_price:
                raise ValueError("Minimum price cannot be greater than maximum price")
        
        # Validate area range
        if self.min_area is not None and self.max_area is not None:
            if self.min_area > self.max_area:
                raise ValueError("Minimum area cannot be greater than maximum area")
        
        return self
    
    class Config:
        json_schema_extra = {
            "example": {
                "location": "Dubai",
                "min_price": 1000.00,
                "max_price": 5000.00,
                "bedrooms": 2,
                "property_type": "rental",
                "page": 1,
                "page_size": 20,
                "sort_by": "price",
                "sort_order": "asc"
            }
        }


class PropertySummary(BaseModel):
    """Schema for property summary (minimal information)."""
    
    id: str = Field(
        ...,
        description="Property unique identifier"
    )
    
    title: str = Field(
        ...,
        description="Property listing title"
    )
    
    property_type: PropertyType = Field(
        ...,
        description="Property type"
    )
    
    price: Decimal = Field(
        ...,
        description="Property price"
    )
    
    bedrooms: int = Field(
        ...,
        description="Number of bedrooms"
    )
    
    bathrooms: int = Field(
        ...,
        description="Number of bathrooms"
    )
    
    location: str = Field(
        ...,
        description="Property location"
    )
    
    is_active: bool = Field(
        ...,
        description="Whether the property is active"
    )
    
    primary_image_url: Optional[str] = Field(
        None,
        description="URL of the primary image"
    )
    
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)
        }