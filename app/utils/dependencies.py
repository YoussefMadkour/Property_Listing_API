"""
FastAPI dependency injection utilities for authentication and database sessions.
Provides reusable dependencies for route protection and user extraction.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User, UserRole
from app.services.auth import AuthService
from app.services.property import PropertyService
from app.utils.exceptions import (
    UnauthorizedError,
    InvalidTokenError,
    TokenExpiredError,
    InactiveUserError,
    ForbiddenError,
    InsufficientPermissionsError
)
from jose import JWTError


# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """
    Get authentication service instance.
    
    Args:
        db: Database session
        
    Returns:
        AuthService instance
    """
    return AuthService(db)


async def get_property_service(db: AsyncSession = Depends(get_db)) -> PropertyService:
    """
    Get property service instance.
    
    Args:
        db: Database session
        
    Returns:
        PropertyService instance
    """
    return PropertyService(db)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
        auth_service: Authentication service
        
    Returns:
        Current User object
        
    Raises:
        UnauthorizedError: If no token provided or token is invalid
        TokenExpiredError: If token is expired
        InactiveUserError: If user account is inactive
    """
    if not credentials:
        raise UnauthorizedError("Authentication token required")
    
    try:
        user = await auth_service.get_current_user(credentials.credentials)
        return user
    except (InvalidTokenError, TokenExpiredError, InactiveUserError):
        raise
    except Exception as e:
        raise UnauthorizedError(f"Authentication failed: {str(e)}")


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (additional check for user status).
    
    Args:
        current_user: Current user from token
        
    Returns:
        Active User object
        
    Raises:
        InactiveUserError: If user account is inactive
    """
    if not current_user.is_active:
        raise InactiveUserError()
    
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current user with admin role.
    
    Args:
        current_user: Current active user
        
    Returns:
        Admin User object
        
    Raises:
        ForbiddenError: If user is not an admin
    """
    if current_user.role != UserRole.ADMIN:
        raise InsufficientPermissionsError("access admin resources")
    
    return current_user


async def get_current_agent_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current user with agent role (or admin).
    
    Args:
        current_user: Current active user
        
    Returns:
        Agent User object
        
    Raises:
        ForbiddenError: If user is not an agent or admin
    """
    if current_user.role not in [UserRole.AGENT, UserRole.ADMIN]:
        raise InsufficientPermissionsError("access agent resources")
    
    return current_user


def require_role(required_role: UserRole):
    """
    Create a dependency that requires a specific user role.
    
    Args:
        required_role: Required user role
        
    Returns:
        Dependency function
    """
    async def role_dependency(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.role != required_role and current_user.role != UserRole.ADMIN:
            raise InsufficientPermissionsError(f"access {required_role.value} resources")
        return current_user
    
    return role_dependency


def require_resource_ownership(get_resource_owner_id):
    """
    Create a dependency that requires resource ownership or admin role.
    
    Args:
        get_resource_owner_id: Function to get resource owner ID
        
    Returns:
        Dependency function
    """
    async def ownership_dependency(
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthService = Depends(get_auth_service)
    ) -> User:
        # Admin users can access all resources
        if current_user.role == UserRole.ADMIN:
            return current_user
        
        # Get resource owner ID
        resource_owner_id = await get_resource_owner_id()
        
        # Check if user owns the resource
        if not auth_service.can_manage_resource(current_user, resource_owner_id):
            raise InsufficientPermissionsError("access this resource")
        
        return current_user
    
    return ownership_dependency


# Optional authentication dependency (for public endpoints that can benefit from user context)
async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> Optional[User]:
    """
    Get current user if token is provided and valid, otherwise return None.
    
    Args:
        credentials: HTTP Bearer credentials (optional)
        auth_service: Authentication service
        
    Returns:
        User object if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        user = await auth_service.get_current_user(credentials.credentials)
        return user if user.is_active else None
    except Exception:
        # Silently ignore authentication errors for optional auth
        return None