"""
Property service for managing property listings with business logic validation.
Handles CRUD operations, ownership validation, search functionality, and business rules.
"""

from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.property import PropertyRepository, PropertySearchFilters
from app.repositories.user import UserRepository
from app.models.property import Property, PropertyType
from app.models.user import User, UserRole
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertySearchFilters as PropertySearchSchema
from app.utils.exceptions import (
    NotFoundError,
    ForbiddenError,
    ValidationError,
    BadRequestError,
    InsufficientPermissionsError
)
import uuid
import logging

logger = logging.getLogger(__name__)


class PropertyService:
    """
    Property service for managing property listings with comprehensive business logic.
    Handles CRUD operations, ownership validation, search functionality, and business rules.
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.property_repo = PropertyRepository(db_session)
        self.user_repo = UserRepository(db_session)
    
    async def create_property(self, property_data: PropertyCreate, current_user: User) -> Property:
        """
        Create a new property listing with ownership and permission validation.
        
        Args:
            property_data: Property creation data
            current_user: User creating the property
            
        Returns:
            Created property instance
            
        Raises:
            ForbiddenError: If user doesn't have permission to create properties
            ValidationError: If property data is invalid
            BadRequestError: If business rules are violated
        """
        try:
            # Validate user permissions
            if not self._can_create_property(current_user):
                raise InsufficientPermissionsError("create properties")
            
            # Validate user is active
            if not current_user.is_active:
                raise ForbiddenError("Inactive users cannot create properties")
            
            # Prepare property data with agent assignment
            create_data = property_data.model_dump()
            create_data["agent_id"] = current_user.id
            
            # Validate business rules
            await self._validate_property_business_rules(create_data, current_user)
            
            # Create property
            property_obj = await self.property_repo.create_property(create_data)
            
            logger.info(f"Property created by user {current_user.email}: {property_obj.title} (ID: {property_obj.id})")
            return property_obj
            
        except ValidationError:
            raise
        except ForbiddenError:
            raise
        except BadRequestError:
            raise
        except Exception as e:
            logger.error(f"Failed to create property for user {current_user.id}: {e}")
            raise BadRequestError(f"Failed to create property: {str(e)}")
    
    async def get_property(self, property_id: uuid.UUID, current_user: Optional[User] = None) -> Property:
        """
        Get property by ID with permission validation.
        
        Args:
            property_id: UUID of the property
            current_user: Optional current user for permission checks
            
        Returns:
            Property instance with details
            
        Raises:
            NotFoundError: If property doesn't exist
            ForbiddenError: If user doesn't have permission to view property
        """
        try:
            # Get property with details
            property_obj = await self.property_repo.get_property_with_details(property_id)
            
            if not property_obj:
                raise NotFoundError("Property", str(property_id))
            
            # Check view permissions
            if current_user and not self._can_view_property(property_obj, current_user):
                raise ForbiddenError("You don't have permission to view this property")
            
            # If no user provided, only return active properties
            if not current_user and not property_obj.is_active:
                raise NotFoundError("Property", str(property_id))
            
            logger.debug(f"Retrieved property: {property_id}")
            return property_obj
            
        except NotFoundError:
            raise
        except ForbiddenError:
            raise
        except Exception as e:
            logger.error(f"Failed to get property {property_id}: {e}")
            raise BadRequestError(f"Failed to retrieve property: {str(e)}")
    
    async def update_property(
        self,
        property_id: uuid.UUID,
        property_data: PropertyUpdate,
        current_user: User
    ) -> Property:
        """
        Update property with ownership and permission validation.
        
        Args:
            property_id: UUID of the property to update
            property_data: Property update data
            current_user: User updating the property
            
        Returns:
            Updated property instance
            
        Raises:
            NotFoundError: If property doesn't exist
            ForbiddenError: If user doesn't have permission to update property
            ValidationError: If update data is invalid
        """
        try:
            # Get existing property
            existing_property = await self.property_repo.get_property_with_details(property_id)
            
            if not existing_property:
                raise NotFoundError("Property", str(property_id))
            
            # Check update permissions
            if not self._can_manage_property(existing_property, current_user):
                raise InsufficientPermissionsError("update this property")
            
            # Validate user is active
            if not current_user.is_active:
                raise ForbiddenError("Inactive users cannot update properties")
            
            # Prepare update data (exclude None values)
            update_data = {k: v for k, v in property_data.model_dump().items() if v is not None}
            
            if not update_data:
                raise ValidationError("No valid fields provided for update")
            
            # Validate business rules for updates
            await self._validate_property_update_rules(existing_property, update_data, current_user)
            
            # Update property
            updated_property = await self.property_repo.update(property_id, update_data)
            
            if not updated_property:
                raise NotFoundError("Property", str(property_id))
            
            logger.info(f"Property updated by user {current_user.email}: {property_id}")
            return updated_property
            
        except NotFoundError:
            raise
        except ForbiddenError:
            raise
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to update property {property_id}: {e}")
            raise BadRequestError(f"Failed to update property: {str(e)}")
    
    async def delete_property(self, property_id: uuid.UUID, current_user: User) -> bool:
        """
        Delete property with ownership and permission validation.
        
        Args:
            property_id: UUID of the property to delete
            current_user: User deleting the property
            
        Returns:
            True if property was deleted
            
        Raises:
            NotFoundError: If property doesn't exist
            ForbiddenError: If user doesn't have permission to delete property
        """
        try:
            # Get existing property
            existing_property = await self.property_repo.get_property_with_details(property_id)
            
            if not existing_property:
                raise NotFoundError("Property", str(property_id))
            
            # Check delete permissions
            if not self._can_manage_property(existing_property, current_user):
                raise InsufficientPermissionsError("delete this property")
            
            # Validate user is active
            if not current_user.is_active:
                raise ForbiddenError("Inactive users cannot delete properties")
            
            # Validate business rules for deletion
            await self._validate_property_deletion_rules(existing_property, current_user)
            
            # Delete associated images first (files and database records)
            from app.services.image import ImageService
            image_service = ImageService(self.db_session)
            deleted_images_count = await image_service.delete_property_images(property_id)
            
            # Delete property (database record)
            deleted = await self.property_repo.delete(property_id)
            
            if deleted:
                logger.info(f"Property deleted by user {current_user.email}: {property_id} (with {deleted_images_count} images)")
            
            return deleted
            
        except NotFoundError:
            raise
        except ForbiddenError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete property {property_id}: {e}")
            raise BadRequestError(f"Failed to delete property: {str(e)}")
    
    async def search_properties(
        self,
        search_filters: PropertySearchSchema,
        current_user: Optional[User] = None
    ) -> Tuple[List[Property], int]:
        """
        Search properties with filtering, pagination, and permission validation.
        
        Args:
            search_filters: Search filters and pagination parameters
            current_user: Optional current user for permission-based filtering
            
        Returns:
            Tuple of (properties list, total count)
            
        Raises:
            ValidationError: If search parameters are invalid
            ForbiddenError: If user doesn't have permission for certain filters
        """
        try:
            # Validate search parameters
            self._validate_search_filters(search_filters, current_user)
            
            # Convert schema to repository filter format
            repo_filters = self._convert_search_filters(search_filters, current_user)
            
            # Calculate pagination
            skip = (search_filters.page - 1) * search_filters.page_size
            
            # Perform search
            properties, total_count = await self.property_repo.search_properties(
                filters=repo_filters,
                skip=skip,
                limit=search_filters.page_size,
                order_by=search_filters.sort_by,
                order_direction=search_filters.sort_order
            )
            
            logger.debug(f"Property search returned {len(properties)} of {total_count} results")
            return properties, total_count
            
        except ValidationError:
            raise
        except ForbiddenError:
            raise
        except Exception as e:
            logger.error(f"Failed to search properties: {e}")
            raise BadRequestError(f"Failed to search properties: {str(e)}")
    
    async def get_user_properties(
        self,
        user_id: uuid.UUID,
        current_user: User,
        skip: int = 0,
        limit: int = 20,
        include_inactive: bool = False
    ) -> Tuple[List[Property], int]:
        """
        Get properties owned by a specific user with permission validation.
        
        Args:
            user_id: UUID of the property owner
            current_user: User making the request
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_inactive: Whether to include inactive properties
            
        Returns:
            Tuple of (properties list, total count)
            
        Raises:
            ForbiddenError: If user doesn't have permission to view these properties
            NotFoundError: If target user doesn't exist
        """
        try:
            # Check if target user exists
            target_user = await self.user_repo.get_by_id(user_id)
            if not target_user:
                raise NotFoundError("User", str(user_id))
            
            # Check permissions
            if not self._can_view_user_properties(target_user, current_user):
                raise InsufficientPermissionsError("view these properties")
            
            # Get properties
            properties, total_count = await self.property_repo.get_properties_by_agent(
                agent_id=user_id,
                skip=skip,
                limit=limit,
                include_inactive=include_inactive
            )
            
            logger.debug(f"Retrieved {len(properties)} properties for user {user_id}")
            return properties, total_count
            
        except NotFoundError:
            raise
        except ForbiddenError:
            raise
        except Exception as e:
            logger.error(f"Failed to get properties for user {user_id}: {e}")
            raise BadRequestError(f"Failed to retrieve user properties: {str(e)}")
    
    async def get_nearby_properties(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        limit: int = 20,
        property_type: Optional[PropertyType] = None,
        current_user: Optional[User] = None
    ) -> List[Property]:
        """
        Get properties near specified coordinates.
        
        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_km: Search radius in kilometers
            limit: Maximum number of properties to return
            property_type: Optional property type filter
            current_user: Optional current user for permission checks
            
        Returns:
            List of nearby properties
            
        Raises:
            ValidationError: If coordinates are invalid
        """
        try:
            # Validate coordinates
            if not (-90 <= latitude <= 90):
                raise ValidationError("Latitude must be between -90 and 90 degrees")
            
            if not (-180 <= longitude <= 180):
                raise ValidationError("Longitude must be between -180 and 180 degrees")
            
            if radius_km <= 0 or radius_km > 100:
                raise ValidationError("Radius must be between 0 and 100 kilometers")
            
            # Get nearby properties
            properties = await self.property_repo.get_nearby_properties(
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km,
                limit=limit,
                property_type=property_type
            )
            
            logger.debug(f"Found {len(properties)} properties within {radius_km}km")
            return properties
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to get nearby properties: {e}")
            raise BadRequestError(f"Failed to get nearby properties: {str(e)}")
    
    async def toggle_property_status(
        self,
        property_id: uuid.UUID,
        current_user: User
    ) -> Property:
        """
        Toggle property active status with permission validation.
        
        Args:
            property_id: UUID of the property
            current_user: User toggling the status
            
        Returns:
            Updated property instance
            
        Raises:
            NotFoundError: If property doesn't exist
            ForbiddenError: If user doesn't have permission
        """
        try:
            # Get existing property
            existing_property = await self.property_repo.get_property_with_details(property_id)
            
            if not existing_property:
                raise NotFoundError("Property", str(property_id))
            
            # Check permissions
            if not self._can_manage_property(existing_property, current_user):
                raise InsufficientPermissionsError("modify this property status")
            
            # Toggle status
            new_status = not existing_property.is_active
            updated_property = await self.property_repo.update_property_status(property_id, new_status)
            
            if not updated_property:
                raise NotFoundError("Property", str(property_id))
            
            status_text = "activated" if new_status else "deactivated"
            logger.info(f"Property {status_text} by user {current_user.email}: {property_id}")
            
            return updated_property
            
        except NotFoundError:
            raise
        except ForbiddenError:
            raise
        except Exception as e:
            logger.error(f"Failed to toggle property status {property_id}: {e}")
            raise BadRequestError(f"Failed to toggle property status: {str(e)}")
    
    async def get_property_statistics(
        self,
        current_user: User,
        agent_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Get property statistics with permission validation.
        
        Args:
            current_user: User requesting statistics
            agent_id: Optional agent ID to filter statistics
            
        Returns:
            Dictionary with property statistics
            
        Raises:
            ForbiddenError: If user doesn't have permission to view statistics
        """
        try:
            # Determine which statistics to show based on permissions
            if agent_id:
                # Check if user can view specific agent's statistics
                if not self._can_view_agent_statistics(agent_id, current_user):
                    raise InsufficientPermissionsError("view these statistics")
                target_agent_id = agent_id
            else:
                # For non-admin users, show only their own statistics
                if current_user.role != UserRole.ADMIN:
                    target_agent_id = current_user.id
                else:
                    target_agent_id = None  # Admin can see all statistics
            
            # Get statistics
            statistics = await self.property_repo.get_property_statistics(target_agent_id)
            
            logger.debug(f"Generated property statistics for agent {target_agent_id}")
            return statistics
            
        except ForbiddenError:
            raise
        except Exception as e:
            logger.error(f"Failed to get property statistics: {e}")
            raise BadRequestError(f"Failed to get property statistics: {str(e)}")
    
    async def get_featured_properties(self, limit: int = 10) -> List[Property]:
        """
        Get featured properties (properties with images).
        
        Args:
            limit: Maximum number of properties to return
            
        Returns:
            List of featured properties
        """
        try:
            if limit <= 0 or limit > 100:
                raise ValidationError("Limit must be between 1 and 100")
            
            properties = await self.property_repo.get_featured_properties(limit)
            
            logger.debug(f"Retrieved {len(properties)} featured properties")
            return properties
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to get featured properties: {e}")
            raise BadRequestError(f"Failed to get featured properties: {str(e)}")
    
    # Private helper methods for business logic validation
    
    def _can_create_property(self, user: User) -> bool:
        """Check if user can create properties."""
        return user.is_active and user.role in [UserRole.AGENT, UserRole.ADMIN]
    
    def _can_view_property(self, property_obj: Property, user: User) -> bool:
        """Check if user can view a specific property."""
        # Admins can view all properties
        if user.role == UserRole.ADMIN:
            return True
        
        # Agents can view their own properties (active or inactive)
        if property_obj.agent_id == user.id:
            return True
        
        # Other users can only view active properties
        return property_obj.is_active
    
    def _can_manage_property(self, property_obj: Property, user: User) -> bool:
        """Check if user can manage (update/delete) a specific property."""
        # Admins can manage all properties
        if user.role == UserRole.ADMIN:
            return True
        
        # Agents can only manage their own properties
        return property_obj.agent_id == user.id
    
    def _can_view_user_properties(self, target_user: User, current_user: User) -> bool:
        """Check if user can view another user's properties."""
        # Admins can view all user properties
        if current_user.role == UserRole.ADMIN:
            return True
        
        # Users can view their own properties
        return target_user.id == current_user.id
    
    def _can_view_agent_statistics(self, agent_id: uuid.UUID, current_user: User) -> bool:
        """Check if user can view agent statistics."""
        # Admins can view all statistics
        if current_user.role == UserRole.ADMIN:
            return True
        
        # Users can view their own statistics
        return agent_id == current_user.id
    
    async def _validate_property_business_rules(self, property_data: Dict[str, Any], user: User) -> None:
        """Validate business rules for property creation."""
        # Add any specific business rules here
        # For example: limit number of properties per agent, validate location, etc.
        
        # Example: Limit properties per agent (if needed)
        if user.role == UserRole.AGENT:
            # Get current property count for agent
            _, total_count = await self.property_repo.get_properties_by_agent(
                agent_id=user.id,
                skip=0,
                limit=1,
                include_inactive=True
            )
            
            # Example limit: 100 properties per agent
            if total_count >= 100:
                raise BadRequestError("Maximum number of properties per agent exceeded (100)")
    
    async def _validate_property_update_rules(
        self,
        existing_property: Property,
        update_data: Dict[str, Any],
        user: User
    ) -> None:
        """Validate business rules for property updates."""
        # Add any specific business rules for updates
        # For example: prevent certain fields from being updated, validate status changes, etc.
        
        # Example: Prevent changing agent_id (if included in update data)
        if "agent_id" in update_data and update_data["agent_id"] != existing_property.agent_id:
            if user.role != UserRole.ADMIN:
                raise ForbiddenError("Only administrators can change property ownership")
    
    async def _validate_property_deletion_rules(self, property_obj: Property, user: User) -> None:
        """Validate business rules for property deletion."""
        # Add any specific business rules for deletion
        # For example: prevent deletion of properties with active bookings, etc.
        pass
    
    def _validate_search_filters(self, filters: PropertySearchSchema, user: Optional[User]) -> None:
        """Validate search filter parameters."""
        # Validate agent_id filter (admin only)
        if filters.agent_id and (not user or user.role != UserRole.ADMIN):
            raise ForbiddenError("Only administrators can filter by agent ID")
        
        # Validate price ranges
        if filters.min_price and filters.max_price and filters.min_price > filters.max_price:
            raise ValidationError("Minimum price cannot be greater than maximum price")
        
        # Validate area ranges
        if filters.min_area and filters.max_area and filters.min_area > filters.max_area:
            raise ValidationError("Minimum area cannot be greater than maximum area")
    
    def _convert_search_filters(
        self,
        schema_filters: PropertySearchSchema,
        user: Optional[User]
    ) -> PropertySearchFilters:
        """Convert schema filters to repository filter format."""
        # Convert agent_id string to UUID if provided
        agent_id = None
        if schema_filters.agent_id:
            try:
                agent_id = uuid.UUID(schema_filters.agent_id)
            except ValueError:
                raise ValidationError("Invalid agent ID format")
        
        return PropertySearchFilters(
            location=schema_filters.location,
            min_price=schema_filters.min_price,
            max_price=schema_filters.max_price,
            bedrooms=schema_filters.bedrooms,
            bathrooms=schema_filters.bathrooms,
            min_area=schema_filters.min_area,
            max_area=schema_filters.max_area,
            property_type=schema_filters.property_type,
            agent_id=agent_id,
            is_active=schema_filters.is_active,
            search_text=schema_filters.query
        )