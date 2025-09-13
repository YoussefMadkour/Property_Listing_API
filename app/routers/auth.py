"""
Authentication API endpoints for user login, token management, and user information.
Provides JWT-based authentication with role-based access control.
"""

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.services.auth import AuthService
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    AccessTokenResponse,
    CurrentUserResponse,
    TokenValidationResponse
)
from app.utils.dependencies import (
    get_auth_service,
    get_current_active_user,
    security
)
from app.utils.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    InactiveUserError,
    UnauthorizedError
)
from app.config import settings
from typing import Optional


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticate user with email and password, returns JWT tokens"
)
async def login(
    login_data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> LoginResponse:
    """
    Authenticate user and return JWT tokens.
    
    Args:
        login_data: Login credentials (email and password)
        auth_service: Authentication service
        
    Returns:
        Login response with user info and JWT tokens
        
    Raises:
        InvalidCredentialsError: If credentials are invalid
        InactiveUserError: If user account is inactive
    """
    try:
        # Authenticate user and create tokens
        user, access_token, refresh_token = await auth_service.login(
            email=login_data.email,
            password=login_data.password
        )
        
        # Create user response with permissions
        user_response = CurrentUserResponse.model_validate(user.to_dict())
        
        return LoginResponse(
            user=user_response,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60
        )
        
    except (InvalidCredentialsError, InactiveUserError):
        raise
    except Exception as e:
        raise InvalidCredentialsError()


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Generate new access token using refresh token"
)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> AccessTokenResponse:
    """
    Create new access token from refresh token.
    
    Args:
        refresh_data: Refresh token request
        auth_service: Authentication service
        
    Returns:
        New access token response
        
    Raises:
        InvalidTokenError: If refresh token is invalid
        TokenExpiredError: If refresh token is expired
        InactiveUserError: If user account is inactive
    """
    try:
        # Generate new access token
        access_token = await auth_service.refresh_access_token(
            refresh_token=refresh_data.refresh_token
        )
        
        return AccessTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60
        )
        
    except (InvalidTokenError, TokenExpiredError, InactiveUserError):
        raise
    except Exception as e:
        raise InvalidTokenError("Failed to refresh token")


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get current authenticated user information"
)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> CurrentUserResponse:
    """
    Get current authenticated user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user information with permissions
    """
    return CurrentUserResponse.model_validate(current_user.to_dict())


@router.post(
    "/validate",
    response_model=TokenValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate token",
    description="Validate JWT token and return token information"
)
async def validate_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> TokenValidationResponse:
    """
    Validate JWT token and return token information.
    
    Args:
        credentials: HTTP Bearer credentials
        auth_service: Authentication service
        
    Returns:
        Token validation response
    """
    if not credentials:
        return TokenValidationResponse(valid=False)
    
    try:
        # Get user from token
        user = await auth_service.get_current_user(credentials.credentials)
        
        # Get token payload for expiration info
        from app.utils.auth import verify_token
        token_payload = verify_token(credentials.credentials, token_type="access")
        
        return TokenValidationResponse(
            valid=True,
            user_id=str(user.id),
            email=user.email,
            role=user.role,
            expires_at=token_payload.exp
        )
        
    except Exception:
        return TokenValidationResponse(valid=False)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="User logout",
    description="Logout user (client-side token removal)"
)
async def logout(
    current_user: User = Depends(get_current_active_user)
) -> None:
    """
    Logout user.
    
    Note: Since JWT tokens are stateless, actual logout is handled client-side
    by removing the tokens. This endpoint serves as a confirmation that the
    user was authenticated and can be used for logging purposes.
    
    Args:
        current_user: Current authenticated user
    """
    # In a stateless JWT system, logout is primarily client-side
    # This endpoint confirms the user was authenticated and can be used for logging
    pass