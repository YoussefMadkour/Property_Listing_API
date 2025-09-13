"""
Property model for rental and sale listings.
Handles property data with location, pricing, and relationship management.
"""

from sqlalchemy import String, Text, Integer, Numeric, Boolean, Enum as SQLEnum, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from app.database import Base
from decimal import Decimal
import enum
import uuid
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.image import PropertyImage


class PropertyType(str, enum.Enum):
    """Property type enumeration for rental or sale listings."""
    RENTAL = "rental"
    SALE = "sale"


class Property(Base):
    """
    Property model for managing rental and sale listings.
    Includes comprehensive property details, location data, and search optimization.
    """
    
    __tablename__ = "properties"
    
    # Basic property information
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Property listing title"
    )
    
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Detailed property description"
    )
    
    property_type: Mapped[PropertyType] = mapped_column(
        SQLEnum(PropertyType),
        nullable=False,
        index=True,
        comment="Property type - rental or sale"
    )
    
    # Pricing information
    price: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=False,
        index=True,
        comment="Property price in local currency"
    )
    
    # Property specifications
    bedrooms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Number of bedrooms"
    )
    
    bathrooms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of bathrooms"
    )
    
    area_sqft: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Property area in square feet"
    )
    
    # Location information
    location: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Property location/address"
    )
    
    latitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=10, scale=8),
        nullable=True,
        comment="Property latitude coordinate"
    )
    
    longitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=11, scale=8),
        nullable=True,
        comment="Property longitude coordinate"
    )
    
    # Status and ownership
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether the property listing is active"
    )
    
    # Foreign key to user (agent)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID of the agent who owns this property"
    )
    
    # Relationships
    agent: Mapped["User"] = relationship(
        "User",
        back_populates="properties",
        lazy="selectin"
    )
    
    images: Mapped[List["PropertyImage"]] = relationship(
        "PropertyImage",
        back_populates="property_rel",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="PropertyImage.is_primary.desc(), PropertyImage.upload_date.asc()"
    )
    
    def __repr__(self) -> str:
        """String representation of the property."""
        return f"<Property(id={self.id}, title={self.title[:30]}..., price={self.price})>"
    
    @property
    def primary_image(self) -> Optional["PropertyImage"]:
        """Get the primary image for this property."""
        for image in self.images:
            if image.is_primary:
                return image
        # Return first image if no primary is set
        return self.images[0] if self.images else None
    
    @property
    def image_count(self) -> int:
        """Get the number of images associated with this property."""
        return len(self.images)
    
    def validate_price(self) -> None:
        """
        Validate property price.
        
        Raises:
            ValueError: If price is invalid
        """
        if self.price <= 0:
            raise ValueError("Property price must be greater than 0")
        
        if self.price > Decimal('999999999.99'):
            raise ValueError("Property price exceeds maximum allowed value")
    
    def validate_bedrooms(self) -> None:
        """
        Validate number of bedrooms.
        
        Raises:
            ValueError: If bedroom count is invalid
        """
        if self.bedrooms < 0:
            raise ValueError("Number of bedrooms cannot be negative")
        
        if self.bedrooms > 50:
            raise ValueError("Number of bedrooms exceeds reasonable limit")
    
    def validate_bathrooms(self) -> None:
        """
        Validate number of bathrooms.
        
        Raises:
            ValueError: If bathroom count is invalid
        """
        if self.bathrooms < 0:
            raise ValueError("Number of bathrooms cannot be negative")
        
        if self.bathrooms > 50:
            raise ValueError("Number of bathrooms exceeds reasonable limit")
    
    def validate_area(self) -> None:
        """
        Validate property area.
        
        Raises:
            ValueError: If area is invalid
        """
        if self.area_sqft <= 0:
            raise ValueError("Property area must be greater than 0")
        
        if self.area_sqft > 1000000:  # 1 million sqft limit
            raise ValueError("Property area exceeds reasonable limit")
    
    def validate_coordinates(self) -> None:
        """
        Validate latitude and longitude coordinates.
        
        Raises:
            ValueError: If coordinates are invalid
        """
        if self.latitude is not None:
            if not (-90 <= self.latitude <= 90):
                raise ValueError("Latitude must be between -90 and 90 degrees")
        
        if self.longitude is not None:
            if not (-180 <= self.longitude <= 180):
                raise ValueError("Longitude must be between -180 and 180 degrees")
    
    def validate_all(self) -> None:
        """
        Run all validation checks on the property.
        
        Raises:
            ValueError: If any validation fails
        """
        self.validate_price()
        self.validate_bedrooms()
        self.validate_bathrooms()
        self.validate_area()
        self.validate_coordinates()
    
    def to_dict(self, include_agent: bool = False, include_images: bool = False) -> dict:
        """
        Convert property to dictionary.
        
        Args:
            include_agent: Whether to include agent information
            include_images: Whether to include image information
            
        Returns:
            Dictionary representation of property
        """
        result = {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "property_type": self.property_type.value,
            "price": float(self.price),
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "area_sqft": self.area_sqft,
            "location": self.location,
            "latitude": float(self.latitude) if self.latitude else None,
            "longitude": float(self.longitude) if self.longitude else None,
            "is_active": self.is_active,
            "agent_id": str(self.agent_id),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        
        if include_agent and self.agent:
            result["agent"] = self.agent.to_dict()
        
        if include_images:
            result["images"] = [image.to_dict() for image in self.images]
            result["image_count"] = self.image_count
            result["primary_image"] = self.primary_image.to_dict() if self.primary_image else None
        
        return result


# Database indexes for search optimization
# These indexes are created to optimize common search patterns

# Composite index for location-based searches with price filtering
location_price_index = Index(
    'idx_properties_location_price',
    Property.location,
    Property.price,
    Property.is_active
)

# Composite index for bedroom filtering with price
bedrooms_price_index = Index(
    'idx_properties_bedrooms_price',
    Property.bedrooms,
    Property.price,
    Property.is_active
)

# Composite index for property type filtering
type_active_index = Index(
    'idx_properties_type_active',
    Property.property_type,
    Property.is_active,
    Property.created_at.desc()
)

# Composite index for agent's properties
agent_active_index = Index(
    'idx_properties_agent_active',
    Property.agent_id,
    Property.is_active,
    Property.updated_at.desc()
)

# Composite index for comprehensive search (location, price, bedrooms)
search_optimization_index = Index(
    'idx_properties_search_optimization',
    Property.location,
    Property.price,
    Property.bedrooms,
    Property.property_type,
    Property.is_active
)

# Geographic index for coordinate-based searches (if using PostGIS in future)
# This would be useful for radius-based searches
coordinates_index = Index(
    'idx_properties_coordinates',
    Property.latitude,
    Property.longitude,
    postgresql_where=Property.latitude.isnot(None) & Property.longitude.isnot(None)
)