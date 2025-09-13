"""
Database models for the Property Listing API.
Includes User, Property, and PropertyImage models with relationships and validation.
"""

from app.models.user import User, UserRole
from app.models.property import Property, PropertyType
from app.models.image import PropertyImage

# Export all models for easy importing
__all__ = [
    "User",
    "UserRole", 
    "Property",
    "PropertyType",
    "PropertyImage",
]