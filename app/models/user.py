"""
User model with authentication and role management.
Handles user accounts for property agents and administrators.
"""

from sqlalchemy import String, Boolean, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from app.database import Base
from passlib.context import CryptContext
from email_validator import validate_email, EmailNotValidError
import enum
import uuid
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.property import Property

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRole(str, enum.Enum):
    """User role enumeration for role-based access control."""
    AGENT = "agent"
    ADMIN = "admin"


class User(Base):
    """
    User model for authentication and authorization.
    Supports property agents and administrators with role-based permissions.
    """
    
    __tablename__ = "users"
    
    # User identification and authentication
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User email address - must be unique and valid"
    )
    
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt hashed password"
    )
    
    # User profile information
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User's full name"
    )
    
    # Role and status
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole),
        nullable=False,
        default=UserRole.AGENT,
        index=True,
        comment="User role for access control"
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether the user account is active"
    )
    
    # Relationships
    properties: Mapped[List["Property"]] = relationship(
        "Property",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        """String representation of the user."""
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    @classmethod
    def validate_email_format(cls, email: str) -> str:
        """
        Validate email format using email-validator.
        
        Args:
            email: Email address to validate
            
        Returns:
            Normalized email address
            
        Raises:
            ValueError: If email format is invalid
        """
        try:
            # Validate and normalize email
            valid_email = validate_email(email)
            return valid_email.email.lower()
        except EmailNotValidError as e:
            raise ValueError(f"Invalid email format: {str(e)}")
    
    @classmethod
    def hash_password(cls, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        return pwd_context.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """
        Verify a password against the stored hash.
        
        Args:
            password: Plain text password to verify
            
        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(password, self.hashed_password)
    
    def set_password(self, password: str) -> None:
        """
        Set a new password for the user.
        
        Args:
            password: Plain text password
        """
        self.hashed_password = self.hash_password(password)
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN
    
    @property
    def is_agent(self) -> bool:
        """Check if user has agent role."""
        return self.role == UserRole.AGENT
    
    def can_manage_property(self, property_agent_id: uuid.UUID) -> bool:
        """
        Check if user can manage a specific property.
        
        Args:
            property_agent_id: UUID of the property's agent
            
        Returns:
            True if user can manage the property, False otherwise
        """
        # Admins can manage all properties
        if self.is_admin:
            return True
        
        # Agents can only manage their own properties
        return self.id == property_agent_id
    
    def to_dict(self) -> dict:
        """
        Convert user to dictionary (excluding sensitive data).
        
        Returns:
            Dictionary representation of user
        """
        return {
            "id": str(self.id),
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }