"""
Authentication service for user login, token management, and authorization.
Handles JWT token generation, validation, and user authentication flows.
"""

from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User, UserRole
from app.utils.auth import (
    create_access_token,
    create_refresh_token,
    verify_token,
    TokenPayload
)
from app.utils.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    InactiveUserError,
    NotFoundError
)
from jose import JWTError
import uuid


class AuthService:
    """Authentication service for managing user authentication and authorization."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def authenticate_user(self, email: str, password: str) -> User:
        """
        Authenticate user with email and password.
        
        Args:
            email: User's email address
            password: Plain text password
            
        Returns:
            Authenticated User object
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
            InactiveUserError: If user account is inactive
        """
        # Normalize email
        email = email.lower().strip()
        
        # Find user by email
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        # Check if user exists and password is correct
        if not user or not user.verify_password(password):
            raise InvalidCredentialsError()
        
        # Check if user account is active
        if not user.is_active:
            raise InactiveUserError()
        
        return user
    
    async def create_tokens(self, user: User) -> Tuple[str, str]:
        """
        Create access and refresh tokens for user.
        
        Args:
            user: User object
            
        Returns:
            Tuple of (access_token, refresh_token)
        """
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role
        )
        
        refresh_token = create_refresh_token(
            user_id=user.id,
            email=user.email
        )
        
        return access_token, refresh_token
    
    async def login(self, email: str, password: str) -> Tuple[User, str, str]:
        """
        Authenticate user and create tokens.
        
        Args:
            email: User's email address
            password: Plain text password
            
        Returns:
            Tuple of (user, access_token, refresh_token)
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
            InactiveUserError: If user account is inactive
        """
        user = await self.authenticate_user(email, password)
        access_token, refresh_token = await self.create_tokens(user)
        
        return user, access_token, refresh_token
    
    async def refresh_access_token(self, refresh_token: str) -> str:
        """
        Create new access token from refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New access token
            
        Raises:
            InvalidTokenError: If refresh token is invalid
            TokenExpiredError: If refresh token is expired
            NotFoundError: If user not found
            InactiveUserError: If user account is inactive
        """
        try:
            # Verify refresh token
            token_payload = verify_token(refresh_token, token_type="refresh")
            
            # Get user from database
            user = await self.get_user_by_id(uuid.UUID(token_payload.user_id))
            
            # Check if user account is still active
            if not user.is_active:
                raise InactiveUserError()
            
            # Create new access token
            access_token = create_access_token(
                user_id=user.id,
                email=user.email,
                role=user.role
            )
            
            return access_token
            
        except JWTError as e:
            if "expired" in str(e).lower():
                raise TokenExpiredError()
            raise InvalidTokenError(str(e))
    
    async def get_current_user(self, token: str) -> User:
        """
        Get current user from access token.
        
        Args:
            token: JWT access token
            
        Returns:
            Current User object
            
        Raises:
            InvalidTokenError: If token is invalid
            TokenExpiredError: If token is expired
            NotFoundError: If user not found
            InactiveUserError: If user account is inactive
        """
        try:
            # Verify access token
            token_payload = verify_token(token, token_type="access")
            
            # Get user from database
            user = await self.get_user_by_id(uuid.UUID(token_payload.user_id))
            
            # Check if user account is still active
            if not user.is_active:
                raise InactiveUserError()
            
            return user
            
        except JWTError as e:
            if "expired" in str(e).lower():
                raise TokenExpiredError()
            raise InvalidTokenError(str(e))
    
    async def get_user_by_id(self, user_id: uuid.UUID) -> User:
        """
        Get user by ID.
        
        Args:
            user_id: User's UUID
            
        Returns:
            User object
            
        Raises:
            NotFoundError: If user not found
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise NotFoundError("User", str(user_id))
        
        return user
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: User's email address
            
        Returns:
            User object if found, None otherwise
        """
        email = email.lower().strip()
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    def verify_user_permissions(self, user: User, required_role: UserRole) -> bool:
        """
        Verify if user has required role permissions.
        
        Args:
            user: User object
            required_role: Required role for access
            
        Returns:
            True if user has required permissions, False otherwise
        """
        # Admin users have access to everything
        if user.role == UserRole.ADMIN:
            return True
        
        # Check if user has the required role
        return user.role == required_role
    
    def can_manage_resource(self, user: User, resource_owner_id: uuid.UUID) -> bool:
        """
        Check if user can manage a specific resource.
        
        Args:
            user: User object
            resource_owner_id: UUID of the resource owner
            
        Returns:
            True if user can manage the resource, False otherwise
        """
        # Admin users can manage all resources
        if user.role == UserRole.ADMIN:
            return True
        
        # Users can only manage their own resources
        return user.id == resource_owner_id