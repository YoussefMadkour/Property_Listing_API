"""
User repository for authentication and user management operations.
Provides secure user operations with password handling and role-based access.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload
from app.repositories.base import BaseRepository
from app.models.user import User, UserRole
from app.models.property import Property
from typing import Optional, List, Dict, Any, Tuple
import uuid
import logging

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User]):
    """
    Repository for user management with authentication and authorization support.
    Handles secure user operations and role-based access control.
    """
    
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)
    
    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """
        Create a new user with email validation and password hashing.
        
        Args:
            user_data: Dictionary containing user information
                      Must include: email, password, full_name
                      Optional: role (defaults to AGENT)
            
        Returns:
            Created user instance
            
        Raises:
            ValueError: If validation fails
            Exception: If database operation fails
        """
        try:
            # Validate and normalize email
            email = User.validate_email_format(user_data["email"])
            
            # Check if email already exists
            existing_user = await self.get_by_email(email)
            if existing_user:
                raise ValueError(f"User with email {email} already exists")
            
            # Hash password
            password = user_data.pop("password")
            hashed_password = User.hash_password(password)
            
            # Prepare user data
            create_data = {
                **user_data,
                "email": email,
                "hashed_password": hashed_password,
                "role": user_data.get("role", UserRole.AGENT),
                "is_active": user_data.get("is_active", True)
            }
            
            # Create user
            created_user = await self.create(create_data)
            logger.info(f"Created user: {created_user.email} (ID: {created_user.id})")
            return created_user
        except ValueError as e:
            logger.error(f"User validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise
    
    async def get_by_email(self, email: str, load_relationships: bool = False) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: Email address to search for
            load_relationships: Whether to load user's properties
            
        Returns:
            User instance if found, None otherwise
        """
        try:
            # Normalize email for search
            normalized_email = email.lower().strip()
            
            query = select(User).where(User.email == normalized_email)
            
            if load_relationships:
                query = query.options(selectinload(User.properties))
            
            result = await self.db.execute(query)
            user = result.scalar_one_or_none()
            
            if user:
                logger.debug(f"Retrieved user by email: {email}")
            else:
                logger.debug(f"User with email {email} not found")
            
            return user
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            raise
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate user with email and password.
        
        Args:
            email: User's email address
            password: Plain text password
            
        Returns:
            User instance if authentication successful, None otherwise
        """
        try:
            user = await self.get_by_email(email)
            
            if not user:
                logger.debug(f"Authentication failed: user {email} not found")
                return None
            
            if not user.is_active:
                logger.debug(f"Authentication failed: user {email} is inactive")
                return None
            
            if not user.verify_password(password):
                logger.debug(f"Authentication failed: invalid password for {email}")
                return None
            
            logger.info(f"User authenticated successfully: {email}")
            return user
        except Exception as e:
            logger.error(f"Failed to authenticate user {email}: {e}")
            raise
    
    async def update_password(self, user_id: uuid.UUID, new_password: str) -> Optional[User]:
        """
        Update user's password with proper hashing.
        
        Args:
            user_id: UUID of the user
            new_password: New plain text password
            
        Returns:
            Updated user instance or None if not found
            
        Raises:
            ValueError: If password validation fails
        """
        try:
            # Hash the new password
            hashed_password = User.hash_password(new_password)
            
            # Update user
            updated_user = await self.update(user_id, {"hashed_password": hashed_password})
            
            if updated_user:
                logger.info(f"Password updated for user: {updated_user.email}")
            
            return updated_user
        except ValueError as e:
            logger.error(f"Password validation failed for user {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to update password for user {user_id}: {e}")
            raise
    
    async def update_user_status(self, user_id: uuid.UUID, is_active: bool) -> Optional[User]:
        """
        Update user's active status.
        
        Args:
            user_id: UUID of the user
            is_active: New active status
            
        Returns:
            Updated user instance or None if not found
        """
        try:
            updated_user = await self.update(user_id, {"is_active": is_active})
            
            if updated_user:
                status = "activated" if is_active else "deactivated"
                logger.info(f"User {updated_user.email} {status}")
            
            return updated_user
        except Exception as e:
            logger.error(f"Failed to update user status {user_id}: {e}")
            raise
    
    async def update_user_role(self, user_id: uuid.UUID, new_role: UserRole) -> Optional[User]:
        """
        Update user's role.
        
        Args:
            user_id: UUID of the user
            new_role: New user role
            
        Returns:
            Updated user instance or None if not found
        """
        try:
            updated_user = await self.update(user_id, {"role": new_role})
            
            if updated_user:
                logger.info(f"User {updated_user.email} role updated to {new_role.value}")
            
            return updated_user
        except Exception as e:
            logger.error(f"Failed to update user role {user_id}: {e}")
            raise
    
    async def get_users_by_role(
        self,
        role: UserRole,
        skip: int = 0,
        limit: int = 50,
        include_inactive: bool = False
    ) -> Tuple[List[User], int]:
        """
        Get users by role with pagination.
        
        Args:
            role: User role to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_inactive: Whether to include inactive users
            
        Returns:
            Tuple of (users list, total count)
        """
        try:
            query = select(User).where(User.role == role)
            count_query = select(func.count(User.id)).where(User.role == role)
            
            if not include_inactive:
                query = query.where(User.is_active == True)
                count_query = count_query.where(User.is_active == True)
            
            # Get total count
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()
            
            # Apply pagination and ordering
            query = query.order_by(desc(User.created_at)).offset(skip).limit(limit)
            
            result = await self.db.execute(query)
            users = result.scalars().all()
            
            logger.debug(f"Retrieved {len(users)} users with role {role.value}")
            return list(users), total_count
        except Exception as e:
            logger.error(f"Failed to get users by role {role.value}: {e}")
            raise
    
    async def get_user_with_properties(self, user_id: uuid.UUID) -> Optional[User]:
        """
        Get user with all their properties loaded.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            User with properties loaded or None if not found
        """
        try:
            query = (
                select(User)
                .options(selectinload(User.properties))
                .where(User.id == user_id)
            )
            
            result = await self.db.execute(query)
            user = result.scalar_one_or_none()
            
            if user:
                logger.debug(f"Retrieved user with properties: {user.email}")
            
            return user
        except Exception as e:
            logger.error(f"Failed to get user with properties {user_id}: {e}")
            raise
    
    async def get_active_agents(self, limit: int = 100) -> List[User]:
        """
        Get all active agents (users with agent role).
        
        Args:
            limit: Maximum number of agents to return
            
        Returns:
            List of active agent users
        """
        try:
            query = (
                select(User)
                .where(
                    and_(
                        User.role == UserRole.AGENT,
                        User.is_active == True
                    )
                )
                .order_by(User.full_name)
                .limit(limit)
            )
            
            result = await self.db.execute(query)
            agents = result.scalars().all()
            
            logger.debug(f"Retrieved {len(agents)} active agents")
            return list(agents)
        except Exception as e:
            logger.error(f"Failed to get active agents: {e}")
            raise
    
    async def get_user_statistics(self) -> Dict[str, Any]:
        """
        Get user statistics for admin dashboard.
        
        Returns:
            Dictionary with user statistics
        """
        try:
            # Total users
            total_query = select(func.count(User.id))
            total_result = await self.db.execute(total_query)
            total_users = total_result.scalar()
            
            # Active users
            active_query = select(func.count(User.id)).where(User.is_active == True)
            active_result = await self.db.execute(active_query)
            active_users = active_result.scalar()
            
            # Users by role
            role_query = (
                select(User.role, func.count(User.id))
                .where(User.is_active == True)
                .group_by(User.role)
            )
            role_result = await self.db.execute(role_query)
            users_by_role = {row[0].value: row[1] for row in role_result.all()}
            
            # Recent registrations (last 30 days)
            recent_query = (
                select(func.count(User.id))
                .where(
                    and_(
                        User.created_at >= func.now() - func.interval('30 days'),
                        User.is_active == True
                    )
                )
            )
            recent_result = await self.db.execute(recent_query)
            recent_registrations = recent_result.scalar()
            
            statistics = {
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": total_users - active_users,
                "users_by_role": users_by_role,
                "recent_registrations": recent_registrations
            }
            
            logger.debug("Generated user statistics")
            return statistics
        except Exception as e:
            logger.error(f"Failed to get user statistics: {e}")
            raise
    
    async def search_users(
        self,
        search_term: str,
        role: Optional[UserRole] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[User], int]:
        """
        Search users by email or full name.
        
        Args:
            search_term: Term to search for in email or full name
            role: Optional role filter
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            Tuple of (users list, total count)
        """
        try:
            search_pattern = f"%{search_term}%"
            
            # Build base conditions
            conditions = [
                User.is_active == True,
                (User.email.ilike(search_pattern) | User.full_name.ilike(search_pattern))
            ]
            
            if role:
                conditions.append(User.role == role)
            
            query = select(User).where(and_(*conditions))
            count_query = select(func.count(User.id)).where(and_(*conditions))
            
            # Get total count
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()
            
            # Apply pagination and ordering
            query = query.order_by(User.full_name).offset(skip).limit(limit)
            
            result = await self.db.execute(query)
            users = result.scalars().all()
            
            logger.debug(f"User search for '{search_term}' returned {len(users)} results")
            return list(users), total_count
        except Exception as e:
            logger.error(f"Failed to search users with term '{search_term}': {e}")
            raise
    
    async def check_email_availability(self, email: str, exclude_user_id: Optional[uuid.UUID] = None) -> bool:
        """
        Check if email address is available for registration or update.
        
        Args:
            email: Email address to check
            exclude_user_id: Optional user ID to exclude from check (for updates)
            
        Returns:
            True if email is available, False if taken
        """
        try:
            normalized_email = User.validate_email_format(email)
            
            query = select(func.count(User.id)).where(User.email == normalized_email)
            
            if exclude_user_id:
                query = query.where(User.id != exclude_user_id)
            
            result = await self.db.execute(query)
            count = result.scalar()
            
            is_available = count == 0
            logger.debug(f"Email {email} availability: {is_available}")
            return is_available
        except ValueError as e:
            logger.error(f"Invalid email format: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to check email availability: {e}")
            raise
    
    async def get_agents_with_property_counts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get agents with their property counts for admin dashboard.
        
        Args:
            limit: Maximum number of agents to return
            
        Returns:
            List of dictionaries with agent info and property counts
        """
        try:
            query = (
                select(
                    User,
                    func.count(Property.id).label('property_count'),
                    func.count(
                        func.case([(Property.is_active == True, Property.id)])
                    ).label('active_property_count')
                )
                .outerjoin(Property, User.id == Property.agent_id)
                .where(
                    and_(
                        User.role == UserRole.AGENT,
                        User.is_active == True
                    )
                )
                .group_by(User.id)
                .order_by(desc('property_count'))
                .limit(limit)
            )
            
            result = await self.db.execute(query)
            rows = result.all()
            
            agents_with_counts = []
            for row in rows:
                user = row[0]
                agent_data = user.to_dict()
                agent_data.update({
                    'total_properties': row[1],
                    'active_properties': row[2]
                })
                agents_with_counts.append(agent_data)
            
            logger.debug(f"Retrieved {len(agents_with_counts)} agents with property counts")
            return agents_with_counts
        except Exception as e:
            logger.error(f"Failed to get agents with property counts: {e}")
            raise
    
    async def delete_user_with_properties(self, user_id: uuid.UUID) -> bool:
        """
        Delete user and all associated properties.
        Uses CASCADE delete configured in the model.
        
        Args:
            user_id: UUID of the user to delete
            
        Returns:
            True if user was deleted, False if not found
        """
        try:
            # The CASCADE delete in the model will handle property deletion
            deleted = await self.delete(user_id)
            if deleted:
                logger.info(f"Deleted user {user_id} with all associated properties")
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete user with properties {user_id}: {e}")
            raise