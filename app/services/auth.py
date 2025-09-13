"""
Authentication service for user login, token management, and authorization.
Handles JWT token generation, validation, user authentication flows, and business logic validation.
"""

from typing import Optional, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user import UserRepository
from app.models.user import User, UserRole
from app.schemas.user import UserCreate
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
    NotFoundError,
    ForbiddenError,
    ValidationError,
    BadRequestError,
    InsufficientPermissionsError
)
from jose import JWTError
import uuid
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """
    Authentication service for managing user authentication, authorization, and business logic validation.
    Handles user authentication flows, token management, and role-based access control.
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.user_repo = UserRepository(db_session)
    
    async def authenticate_user(self, email: str, password: str) -> User:
        """
        Authenticate user with email and password with comprehensive validation.
        
        Args:
            email: User's email address
            password: Plain text password
            
        Returns:
            Authenticated User object
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
            InactiveUserError: If user account is inactive
            ValidationError: If input validation fails
        """
        try:
            # Validate input parameters
            if not email or not email.strip():
                raise ValidationError("Email is required")
            
            if not password or not password.strip():
                raise ValidationError("Password is required")
            
            # Use repository for authentication
            user = await self.user_repo.authenticate_user(email, password)
            
            if not user:
                # Log failed authentication attempt
                logger.warning(f"Failed authentication attempt for email: {email}")
                raise InvalidCredentialsError()
            
            # Additional business rule validation
            await self._validate_user_authentication_rules(user)
            
            logger.info(f"User authenticated successfully: {user.email}")
            return user
            
        except ValidationError:
            raise
        except InvalidCredentialsError:
            raise
        except InactiveUserError:
            raise
        except Exception as e:
            logger.error(f"Authentication error for {email}: {e}")
            raise InvalidCredentialsError()
    
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
        Get user by ID with validation.
        
        Args:
            user_id: User's UUID
            
        Returns:
            User object
            
        Raises:
            NotFoundError: If user not found
            ValidationError: If user_id is invalid
        """
        try:
            if not user_id:
                raise ValidationError("User ID is required")
            
            user = await self.user_repo.get_by_id(user_id)
            
            if not user:
                raise NotFoundError("User", str(user_id))
            
            return user
            
        except ValidationError:
            raise
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get user by ID {user_id}: {e}")
            raise BadRequestError(f"Failed to retrieve user: {str(e)}")
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address with validation.
        
        Args:
            email: User's email address
            
        Returns:
            User object if found, None otherwise
            
        Raises:
            ValidationError: If email format is invalid
        """
        try:
            if not email or not email.strip():
                raise ValidationError("Email is required")
            
            return await self.user_repo.get_by_email(email)
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            return None
    
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
    
    async def create_user(self, user_data: UserCreate, current_user: Optional[User] = None) -> User:
        """
        Create a new user with business logic validation.
        
        Args:
            user_data: User creation data
            current_user: Optional current user for permission checks
            
        Returns:
            Created user instance
            
        Raises:
            ForbiddenError: If user doesn't have permission to create users
            ValidationError: If user data is invalid
            BadRequestError: If business rules are violated
        """
        try:
            # Validate permissions (only admins can create users)
            if current_user and not self._can_create_user(current_user):
                raise InsufficientPermissionsError("create users")
            
            # Validate business rules
            await self._validate_user_creation_rules(user_data, current_user)
            
            # Create user using repository
            create_data = user_data.model_dump()
            user = await self.user_repo.create_user(create_data)
            
            logger.info(f"User created: {user.email} (ID: {user.id})")
            return user
            
        except ValidationError:
            raise
        except ForbiddenError:
            raise
        except BadRequestError:
            raise
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise BadRequestError(f"Failed to create user: {str(e)}")
    
    async def update_user_role(
        self,
        user_id: uuid.UUID,
        new_role: UserRole,
        current_user: User
    ) -> User:
        """
        Update user role with permission validation.
        
        Args:
            user_id: UUID of the user to update
            new_role: New user role
            current_user: User making the request
            
        Returns:
            Updated user instance
            
        Raises:
            NotFoundError: If user doesn't exist
            ForbiddenError: If user doesn't have permission
        """
        try:
            # Only admins can update user roles
            if not self._can_manage_users(current_user):
                raise InsufficientPermissionsError("update user roles")
            
            # Get target user
            target_user = await self.get_user_by_id(user_id)
            
            # Validate business rules
            await self._validate_role_update_rules(target_user, new_role, current_user)
            
            # Update role
            updated_user = await self.user_repo.update_user_role(user_id, new_role)
            
            if not updated_user:
                raise NotFoundError("User", str(user_id))
            
            logger.info(f"User role updated by {current_user.email}: {user_id} -> {new_role.value}")
            return updated_user
            
        except NotFoundError:
            raise
        except ForbiddenError:
            raise
        except Exception as e:
            logger.error(f"Failed to update user role {user_id}: {e}")
            raise BadRequestError(f"Failed to update user role: {str(e)}")
    
    async def update_user_status(
        self,
        user_id: uuid.UUID,
        is_active: bool,
        current_user: User
    ) -> User:
        """
        Update user active status with permission validation.
        
        Args:
            user_id: UUID of the user to update
            is_active: New active status
            current_user: User making the request
            
        Returns:
            Updated user instance
            
        Raises:
            NotFoundError: If user doesn't exist
            ForbiddenError: If user doesn't have permission
        """
        try:
            # Only admins can update user status
            if not self._can_manage_users(current_user):
                raise InsufficientPermissionsError("update user status")
            
            # Get target user
            target_user = await self.get_user_by_id(user_id)
            
            # Validate business rules
            await self._validate_status_update_rules(target_user, is_active, current_user)
            
            # Update status
            updated_user = await self.user_repo.update_user_status(user_id, is_active)
            
            if not updated_user:
                raise NotFoundError("User", str(user_id))
            
            status_text = "activated" if is_active else "deactivated"
            logger.info(f"User {status_text} by {current_user.email}: {user_id}")
            return updated_user
            
        except NotFoundError:
            raise
        except ForbiddenError:
            raise
        except Exception as e:
            logger.error(f"Failed to update user status {user_id}: {e}")
            raise BadRequestError(f"Failed to update user status: {str(e)}")
    
    async def change_password(
        self,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str,
        current_user: User
    ) -> User:
        """
        Change user password with validation.
        
        Args:
            user_id: UUID of the user
            current_password: Current password for verification
            new_password: New password
            current_user: User making the request
            
        Returns:
            Updated user instance
            
        Raises:
            NotFoundError: If user doesn't exist
            ForbiddenError: If user doesn't have permission
            InvalidCredentialsError: If current password is incorrect
        """
        try:
            # Get target user
            target_user = await self.get_user_by_id(user_id)
            
            # Check permissions (users can change their own password, admins can change any)
            if not self._can_change_password(target_user, current_user):
                raise InsufficientPermissionsError("change this password")
            
            # For non-admin users, verify current password
            if current_user.role != UserRole.ADMIN and current_user.id == user_id:
                if not target_user.verify_password(current_password):
                    raise InvalidCredentialsError("Current password is incorrect")
            
            # Validate new password
            if not new_password or len(new_password) < 8:
                raise ValidationError("New password must be at least 8 characters long")
            
            # Update password
            updated_user = await self.user_repo.update_password(user_id, new_password)
            
            if not updated_user:
                raise NotFoundError("User", str(user_id))
            
            logger.info(f"Password changed for user: {user_id}")
            return updated_user
            
        except NotFoundError:
            raise
        except ForbiddenError:
            raise
        except InvalidCredentialsError:
            raise
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to change password for user {user_id}: {e}")
            raise BadRequestError(f"Failed to change password: {str(e)}")
    
    # Private helper methods for business logic validation
    
    def _can_create_user(self, user: User) -> bool:
        """Check if user can create new users."""
        return user.role == UserRole.ADMIN and user.is_active
    
    def _can_manage_users(self, user: User) -> bool:
        """Check if user can manage other users."""
        return user.role == UserRole.ADMIN and user.is_active
    
    def _can_change_password(self, target_user: User, current_user: User) -> bool:
        """Check if user can change password."""
        # Admins can change any password
        if current_user.role == UserRole.ADMIN:
            return True
        
        # Users can change their own password
        return target_user.id == current_user.id
    
    async def _validate_user_authentication_rules(self, user: User) -> None:
        """Validate business rules for user authentication."""
        if not user.is_active:
            raise InactiveUserError()
        
        # Add any additional authentication business rules here
        # For example: check for account lockout, two-factor authentication, etc.
    
    async def _validate_user_creation_rules(
        self,
        user_data: UserCreate,
        current_user: Optional[User]
    ) -> None:
        """Validate business rules for user creation."""
        # Check email availability
        is_available = await self.user_repo.check_email_availability(user_data.email)
        if not is_available:
            raise ValidationError(f"Email {user_data.email} is already registered")
        
        # Validate role assignment (only admins can create admin users)
        if hasattr(user_data, 'role') and user_data.role == UserRole.ADMIN:
            if not current_user or current_user.role != UserRole.ADMIN:
                raise ForbiddenError("Only administrators can create admin users")
    
    async def _validate_role_update_rules(
        self,
        target_user: User,
        new_role: UserRole,
        current_user: User
    ) -> None:
        """Validate business rules for role updates."""
        # Prevent users from changing their own role
        if target_user.id == current_user.id:
            raise ForbiddenError("Users cannot change their own role")
        
        # Add any additional role update business rules here
    
    async def _validate_status_update_rules(
        self,
        target_user: User,
        is_active: bool,
        current_user: User
    ) -> None:
        """Validate business rules for status updates."""
        # Prevent users from deactivating themselves
        if target_user.id == current_user.id and not is_active:
            raise ForbiddenError("Users cannot deactivate their own account")
        
        # Add any additional status update business rules here