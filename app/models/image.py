"""
PropertyImage model for managing property image uploads.
Handles image metadata, file storage, and property associations.
"""

from sqlalchemy import String, Integer, Boolean, ForeignKey, Index, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from app.database import Base
import uuid
from typing import TYPE_CHECKING, Optional
from datetime import datetime

if TYPE_CHECKING:
    from app.models.property import Property


class PropertyImage(Base):
    """
    PropertyImage model for managing uploaded property images.
    Stores file metadata and maintains relationships with properties.
    """
    
    __tablename__ = "property_images"
    
    # Property relationship
    property_id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID of the property this image belongs to"
    )
    
    # File information
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original filename of the uploaded image"
    )
    
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
        comment="Relative path to the stored image file"
    )
    
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="File size in bytes"
    )
    
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="MIME type of the image file"
    )
    
    # Image metadata
    width: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Image width in pixels"
    )
    
    height: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Image height in pixels"
    )
    
    # Image status and ordering
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether this is the primary image for the property"
    )
    
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Display order for image gallery"
    )
    
    # Upload information  
    upload_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="When the image was uploaded"
    )
    
    # Relationships
    property_rel: Mapped["Property"] = relationship(
        "Property",
        back_populates="images",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        """String representation of the property image."""
        return f"<PropertyImage(id={self.id}, property_id={self.property_id}, filename={self.filename})>"
    
    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes."""
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def file_extension(self) -> str:
        """Get file extension from filename."""
        return self.filename.split('.')[-1].lower() if '.' in self.filename else ''
    
    @property
    def aspect_ratio(self) -> Optional[float]:
        """Calculate aspect ratio if dimensions are available."""
        if self.width and self.height:
            return round(self.width / self.height, 2)
        return None
    
    def validate_file_size(self, max_size_mb: int = 10) -> None:
        """
        Validate file size against maximum allowed size.
        
        Args:
            max_size_mb: Maximum file size in megabytes
            
        Raises:
            ValueError: If file size exceeds limit
        """
        max_size_bytes = max_size_mb * 1024 * 1024
        if self.file_size > max_size_bytes:
            raise ValueError(f"File size ({self.file_size_mb}MB) exceeds maximum allowed size ({max_size_mb}MB)")
    
    def validate_mime_type(self, allowed_types: list = None) -> None:
        """
        Validate MIME type against allowed image types.
        
        Args:
            allowed_types: List of allowed MIME types
            
        Raises:
            ValueError: If MIME type is not allowed
        """
        if allowed_types is None:
            allowed_types = ["image/jpeg", "image/png", "image/webp", "image/jpg"]
        
        if self.mime_type not in allowed_types:
            raise ValueError(f"MIME type '{self.mime_type}' is not allowed. Allowed types: {allowed_types}")
    
    def validate_dimensions(self, min_width: int = 100, min_height: int = 100, 
                          max_width: int = 10000, max_height: int = 10000) -> None:
        """
        Validate image dimensions.
        
        Args:
            min_width: Minimum image width
            min_height: Minimum image height
            max_width: Maximum image width
            max_height: Maximum image height
            
        Raises:
            ValueError: If dimensions are invalid
        """
        if self.width is not None:
            if self.width < min_width:
                raise ValueError(f"Image width ({self.width}px) is below minimum ({min_width}px)")
            if self.width > max_width:
                raise ValueError(f"Image width ({self.width}px) exceeds maximum ({max_width}px)")
        
        if self.height is not None:
            if self.height < min_height:
                raise ValueError(f"Image height ({self.height}px) is below minimum ({min_height}px)")
            if self.height > max_height:
                raise ValueError(f"Image height ({self.height}px) exceeds maximum ({max_height}px)")
    
    def validate_all(self, max_size_mb: int = 10, allowed_types: list = None) -> None:
        """
        Run all validation checks on the image.
        
        Args:
            max_size_mb: Maximum file size in megabytes
            allowed_types: List of allowed MIME types
            
        Raises:
            ValueError: If any validation fails
        """
        self.validate_file_size(max_size_mb)
        self.validate_mime_type(allowed_types)
        self.validate_dimensions()
    
    def to_dict(self, include_property: bool = False) -> dict:
        """
        Convert property image to dictionary.
        
        Args:
            include_property: Whether to include property information
            
        Returns:
            Dictionary representation of property image
        """
        result = {
            "id": str(self.id),
            "property_id": str(self.property_id),
            "filename": self.filename,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "file_size_mb": self.file_size_mb,
            "mime_type": self.mime_type,
            "width": self.width,
            "height": self.height,
            "aspect_ratio": self.aspect_ratio,
            "is_primary": self.is_primary,
            "display_order": self.display_order,
            "upload_date": self.upload_date.isoformat(),
            "file_extension": self.file_extension,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        
        if include_property and self.property_rel:
            result["property"] = self.property_rel.to_dict()
        
        return result


# Database indexes for image management optimization

# Index for finding images by property (most common query)
property_images_index = Index(
    'idx_property_images_property_id',
    PropertyImage.property_id,
    PropertyImage.is_primary.desc(),
    PropertyImage.display_order.asc()
)

# Index for finding primary images quickly
primary_images_index = Index(
    'idx_property_images_primary',
    PropertyImage.property_id,
    PropertyImage.is_primary,
    postgresql_where=PropertyImage.is_primary == True
)

# Index for upload date queries (useful for cleanup operations)
upload_date_index = Index(
    'idx_property_images_upload_date',
    PropertyImage.upload_date.desc(),
    PropertyImage.property_id
)

# Index for file path uniqueness and lookups
file_path_index = Index(
    'idx_property_images_file_path',
    PropertyImage.file_path
)