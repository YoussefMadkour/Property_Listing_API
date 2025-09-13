"""
Pydantic schemas for property image requests and responses.
Handles image upload, metadata, and validation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class PropertyImageBase(BaseModel):
    """Base property image schema with common fields."""
    
    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Original filename of the uploaded image",
        example="apartment_living_room.jpg"
    )
    
    is_primary: bool = Field(
        False,
        description="Whether this is the primary image for the property",
        example=False
    )
    
    display_order: int = Field(
        0,
        ge=0,
        description="Display order for image gallery",
        example=1
    )


class PropertyImageCreate(PropertyImageBase):
    """Schema for creating a new property image (used internally)."""
    
    file_path: str = Field(
        ...,
        description="Relative path to the stored image file",
        example="uploads/properties/123e4567-e89b-12d3-a456-426614174000/image1.jpg"
    )
    
    file_size: int = Field(
        ...,
        gt=0,
        description="File size in bytes",
        example=1024000
    )
    
    mime_type: str = Field(
        ...,
        description="MIME type of the image file",
        example="image/jpeg"
    )
    
    width: Optional[int] = Field(
        None,
        gt=0,
        description="Image width in pixels",
        example=1920
    )
    
    height: Optional[int] = Field(
        None,
        gt=0,
        description="Image height in pixels",
        example=1080
    )
    
    @field_validator('mime_type')
    @classmethod
    def validate_mime_type(cls, v):
        """Validate MIME type."""
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
        if v not in allowed_types:
            raise ValueError(f"MIME type must be one of: {', '.join(allowed_types)}")
        return v
    
    @field_validator('file_size')
    @classmethod
    def validate_file_size(cls, v):
        """Validate file size (max 10MB)."""
        max_size = 10 * 1024 * 1024  # 10MB in bytes
        if v > max_size:
            raise ValueError(f"File size cannot exceed {max_size / (1024 * 1024):.1f}MB")
        return v


class PropertyImageUpdate(BaseModel):
    """Schema for updating property image metadata."""
    
    is_primary: Optional[bool] = Field(
        None,
        description="Whether this is the primary image for the property"
    )
    
    display_order: Optional[int] = Field(
        None,
        ge=0,
        description="Display order for image gallery"
    )


class PropertyImageResponse(BaseModel):
    """Schema for property image response."""
    
    id: str = Field(
        ...,
        description="Image unique identifier",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    property_id: str = Field(
        ...,
        description="ID of the property this image belongs to",
        example="123e4567-e89b-12d3-a456-426614174001"
    )
    
    filename: str = Field(
        ...,
        description="Original filename of the uploaded image",
        example="apartment_living_room.jpg"
    )
    
    file_path: str = Field(
        ...,
        description="Relative path to the stored image file",
        example="uploads/properties/123e4567-e89b-12d3-a456-426614174001/image1.jpg"
    )
    
    file_size: int = Field(
        ...,
        description="File size in bytes",
        example=1024000
    )
    
    file_size_mb: float = Field(
        ...,
        description="File size in megabytes",
        example=1.02
    )
    
    mime_type: str = Field(
        ...,
        description="MIME type of the image file",
        example="image/jpeg"
    )
    
    width: Optional[int] = Field(
        None,
        description="Image width in pixels",
        example=1920
    )
    
    height: Optional[int] = Field(
        None,
        description="Image height in pixels",
        example=1080
    )
    
    aspect_ratio: Optional[float] = Field(
        None,
        description="Image aspect ratio (width/height)",
        example=1.78
    )
    
    is_primary: bool = Field(
        ...,
        description="Whether this is the primary image for the property",
        example=False
    )
    
    display_order: int = Field(
        ...,
        description="Display order for image gallery",
        example=1
    )
    
    upload_date: datetime = Field(
        ...,
        description="When the image was uploaded",
        example="2023-01-01T00:00:00Z"
    )
    
    file_extension: str = Field(
        ...,
        description="File extension",
        example="jpg"
    )
    
    created_at: datetime = Field(
        ...,
        description="Image record creation timestamp",
        example="2023-01-01T00:00:00Z"
    )
    
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp",
        example="2023-01-01T00:00:00Z"
    )
    
    # URL for accessing the image (computed field)
    url: Optional[str] = Field(
        None,
        description="URL for accessing the image",
        example="/api/images/123e4567-e89b-12d3-a456-426614174000"
    )
    
    thumbnail_url: Optional[str] = Field(
        None,
        description="URL for accessing the thumbnail",
        example="/api/images/123e4567-e89b-12d3-a456-426614174000/thumbnail"
    )
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PropertyImageListResponse(BaseModel):
    """Schema for property image list response."""
    
    images: List[PropertyImageResponse] = Field(
        ...,
        description="List of property images"
    )
    
    total: int = Field(
        ...,
        description="Total number of images for the property",
        example=5
    )
    
    primary_image: Optional[PropertyImageResponse] = Field(
        None,
        description="Primary image for the property"
    )


class ImageUploadResponse(BaseModel):
    """Schema for image upload response."""
    
    success: bool = Field(
        ...,
        description="Whether the upload was successful",
        example=True
    )
    
    message: str = Field(
        ...,
        description="Upload result message",
        example="Image uploaded successfully"
    )
    
    image: PropertyImageResponse = Field(
        ...,
        description="Uploaded image information"
    )


class MultipleImageUploadResponse(BaseModel):
    """Schema for multiple image upload response."""
    
    success: bool = Field(
        ...,
        description="Whether all uploads were successful",
        example=True
    )
    
    message: str = Field(
        ...,
        description="Upload result message",
        example="3 images uploaded successfully"
    )
    
    images: List[PropertyImageResponse] = Field(
        ...,
        description="List of uploaded images"
    )
    
    uploaded_count: int = Field(
        ...,
        description="Number of successfully uploaded images",
        example=3
    )
    
    failed_count: int = Field(
        0,
        description="Number of failed uploads",
        example=0
    )
    
    errors: List[str] = Field(
        default_factory=list,
        description="List of error messages for failed uploads"
    )


class ImageValidationError(BaseModel):
    """Schema for image validation error response."""
    
    field: str = Field(
        ...,
        description="Field that failed validation",
        example="file_size"
    )
    
    message: str = Field(
        ...,
        description="Validation error message",
        example="File size exceeds maximum allowed size of 10MB"
    )
    
    value: Optional[str] = Field(
        None,
        description="Value that failed validation",
        example="15728640"
    )


class ImageProcessingStatus(BaseModel):
    """Schema for image processing status."""
    
    status: str = Field(
        ...,
        description="Processing status",
        example="processing"
    )
    
    progress: int = Field(
        ...,
        ge=0,
        le=100,
        description="Processing progress percentage",
        example=75
    )
    
    message: str = Field(
        ...,
        description="Status message",
        example="Generating thumbnails..."
    )
    
    estimated_completion: Optional[datetime] = Field(
        None,
        description="Estimated completion time",
        example="2023-01-01T00:05:00Z"
    )


class ImageFilters(BaseModel):
    """Schema for image filtering and search."""
    
    property_id: Optional[str] = Field(
        None,
        description="Filter by property ID",
        example="123e4567-e89b-12d3-a456-426614174001"
    )
    
    is_primary: Optional[bool] = Field(
        None,
        description="Filter by primary image status",
        example=True
    )
    
    mime_type: Optional[str] = Field(
        None,
        description="Filter by MIME type",
        example="image/jpeg"
    )
    
    min_file_size: Optional[int] = Field(
        None,
        ge=0,
        description="Minimum file size in bytes",
        example=100000
    )
    
    max_file_size: Optional[int] = Field(
        None,
        ge=0,
        description="Maximum file size in bytes",
        example=5000000
    )
    
    min_width: Optional[int] = Field(
        None,
        gt=0,
        description="Minimum image width in pixels",
        example=800
    )
    
    min_height: Optional[int] = Field(
        None,
        gt=0,
        description="Minimum image height in pixels",
        example=600
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
        description="Number of images per page (max 100)",
        example=20
    )
    
    # Sorting
    sort_by: Optional[str] = Field(
        "upload_date",
        description="Sort field (upload_date, file_size, display_order)",
        example="display_order"
    )
    
    sort_order: Optional[str] = Field(
        "desc",
        description="Sort order (asc or desc)",
        example="asc"
    )
    
    @field_validator('sort_by')
    @classmethod
    def validate_sort_by(cls, v):
        """Validate sort field."""
        allowed_fields = ['upload_date', 'file_size', 'display_order', 'filename']
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


class ImageSummary(BaseModel):
    """Schema for image summary (minimal information)."""
    
    id: str = Field(
        ...,
        description="Image unique identifier"
    )
    
    filename: str = Field(
        ...,
        description="Original filename"
    )
    
    is_primary: bool = Field(
        ...,
        description="Whether this is the primary image"
    )
    
    file_size_mb: float = Field(
        ...,
        description="File size in megabytes"
    )
    
    url: Optional[str] = Field(
        None,
        description="URL for accessing the image"
    )
    
    class Config:
        from_attributes = True