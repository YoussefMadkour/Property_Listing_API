"""
Property repository for managing property listings with advanced search and filtering.
Provides optimized database operations for property management and search functionality.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text, desc, asc
from sqlalchemy.orm import selectinload, joinedload
from app.repositories.base import BaseRepository
from app.models.property import Property, PropertyType
from app.models.user import User
from app.models.image import PropertyImage
from app.utils.query_optimizer import query_optimizer
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
import uuid
import logging

logger = logging.getLogger(__name__)


class PropertySearchFilters:
    """Data class for property search filters."""
    
    def __init__(
        self,
        location: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        bedrooms: Optional[int] = None,
        min_bedrooms: Optional[int] = None,
        max_bedrooms: Optional[int] = None,
        bathrooms: Optional[int] = None,
        min_bathrooms: Optional[int] = None,
        max_bathrooms: Optional[int] = None,
        property_type: Optional[PropertyType] = None,
        min_area: Optional[int] = None,
        max_area: Optional[int] = None,
        agent_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = True,
        search_text: Optional[str] = None,
        latitude: Optional[Decimal] = None,
        longitude: Optional[Decimal] = None,
        radius_km: Optional[float] = None
    ):
        self.location = location
        self.min_price = min_price
        self.max_price = max_price
        self.bedrooms = bedrooms
        self.min_bedrooms = min_bedrooms
        self.max_bedrooms = max_bedrooms
        self.bathrooms = bathrooms
        self.min_bathrooms = min_bathrooms
        self.max_bathrooms = max_bathrooms
        self.property_type = property_type
        self.min_area = min_area
        self.max_area = max_area
        self.agent_id = agent_id
        self.is_active = is_active
        self.search_text = search_text
        self.latitude = latitude
        self.longitude = longitude
        self.radius_km = radius_km


class PropertyRepository(BaseRepository[Property]):
    """
    Repository for property management with advanced search and filtering capabilities.
    Optimized for performance with proper indexing and query optimization.
    """
    
    def __init__(self, db: AsyncSession):
        super().__init__(Property, db)
    
    async def create_property(self, property_data: Dict[str, Any]) -> Property:
        """
        Create a new property with validation.
        
        Args:
            property_data: Dictionary containing property information
            
        Returns:
            Created property instance
            
        Raises:
            ValueError: If validation fails
            Exception: If database operation fails
        """
        try:
            # Create property instance for validation
            property_obj = Property(**property_data)
            property_obj.validate_all()
            
            # Create in database
            created_property = await self.create(property_data)
            logger.info(f"Created property: {created_property.title} (ID: {created_property.id})")
            return created_property
        except ValueError as e:
            logger.error(f"Property validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create property: {e}")
            raise
    
    async def get_property_with_details(self, property_id: uuid.UUID) -> Optional[Property]:
        """
        Get property with all related data (agent and images).
        
        Args:
            property_id: UUID of the property
            
        Returns:
            Property with loaded relationships or None if not found
        """
        try:
            query = (
                select(Property)
                .options(
                    selectinload(Property.agent),
                    selectinload(Property.images)
                )
                .where(Property.id == property_id)
            )
            
            result = await self.db.execute(query)
            property_obj = result.scalar_one_or_none()
            
            if property_obj:
                logger.debug(f"Retrieved property with details: {property_id}")
            
            return property_obj
        except Exception as e:
            logger.error(f"Failed to get property with details {property_id}: {e}")
            raise
    
    async def search_properties(
        self,
        filters: PropertySearchFilters,
        skip: int = 0,
        limit: int = 20,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> Tuple[List[Property], int]:
        """
        Search properties with advanced filtering and pagination.
        
        Args:
            filters: PropertySearchFilters instance with search criteria
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            order_by: Field to order by
            order_direction: 'asc' or 'desc'
            
        Returns:
            Tuple of (properties list, total count)
        """
        try:
            # Build base query with relationships
            query = (
                select(Property)
                .options(
                    selectinload(Property.agent),
                    selectinload(Property.images)
                )
            )
            
            # Build count query for total results
            count_query = select(func.count(Property.id))
            
            # Apply filters to both queries
            conditions = self._build_filter_conditions(filters)
            if conditions:
                query = query.where(and_(*conditions))
                count_query = count_query.where(and_(*conditions))
            
            # Monitor count query performance
            count_query_str = str(count_query.compile(compile_kwargs={"literal_binds": True}))
            await query_optimizer.analyze_query_performance(
                self.db, count_query_str, endpoint="/api/v1/properties/search"
            )
            
            # Get total count
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()
            
            # Apply ordering
            if hasattr(Property, order_by):
                order_field = getattr(Property, order_by)
                if order_direction.lower() == "desc":
                    query = query.order_by(desc(order_field))
                else:
                    query = query.order_by(asc(order_field))
            else:
                # Default ordering
                query = query.order_by(desc(Property.created_at))
            
            # Apply pagination
            query = query.offset(skip).limit(limit)
            
            # Monitor main query performance
            main_query_str = str(query.compile(compile_kwargs={"literal_binds": True}))
            await query_optimizer.analyze_query_performance(
                self.db, main_query_str, endpoint="/api/v1/properties/search"
            )
            
            # Execute query
            result = await self.db.execute(query)
            properties = result.scalars().all()
            
            logger.debug(f"Property search returned {len(properties)} of {total_count} total results")
            return list(properties), total_count
        except Exception as e:
            logger.error(f"Failed to search properties: {e}")
            raise
    
    def _build_filter_conditions(self, filters: PropertySearchFilters) -> List:
        """
        Build SQLAlchemy filter conditions from search filters.
        
        Args:
            filters: PropertySearchFilters instance
            
        Returns:
            List of SQLAlchemy conditions
        """
        conditions = []
        
        # Active status filter
        if filters.is_active is not None:
            conditions.append(Property.is_active == filters.is_active)
        
        # Location filter (case-insensitive partial match)
        if filters.location:
            conditions.append(Property.location.ilike(f"%{filters.location}%"))
        
        # Price range filters
        if filters.min_price is not None:
            conditions.append(Property.price >= filters.min_price)
        if filters.max_price is not None:
            conditions.append(Property.price <= filters.max_price)
        
        # Bedroom filters
        if filters.bedrooms is not None:
            conditions.append(Property.bedrooms == filters.bedrooms)
        if filters.min_bedrooms is not None:
            conditions.append(Property.bedrooms >= filters.min_bedrooms)
        if filters.max_bedrooms is not None:
            conditions.append(Property.bedrooms <= filters.max_bedrooms)
        
        # Bathroom filters
        if filters.bathrooms is not None:
            conditions.append(Property.bathrooms == filters.bathrooms)
        if filters.min_bathrooms is not None:
            conditions.append(Property.bathrooms >= filters.min_bathrooms)
        if filters.max_bathrooms is not None:
            conditions.append(Property.bathrooms <= filters.max_bathrooms)
        
        # Property type filter
        if filters.property_type:
            conditions.append(Property.property_type == filters.property_type)
        
        # Area filters
        if filters.min_area is not None:
            conditions.append(Property.area_sqft >= filters.min_area)
        if filters.max_area is not None:
            conditions.append(Property.area_sqft <= filters.max_area)
        
        # Agent filter
        if filters.agent_id:
            conditions.append(Property.agent_id == filters.agent_id)
        
        # Text search in title and description
        if filters.search_text:
            search_term = f"%{filters.search_text}%"
            conditions.append(
                or_(
                    Property.title.ilike(search_term),
                    Property.description.ilike(search_term)
                )
            )
        
        return conditions
    
    async def get_properties_by_agent(
        self,
        agent_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
        include_inactive: bool = False
    ) -> Tuple[List[Property], int]:
        """
        Get properties owned by a specific agent.
        
        Args:
            agent_id: UUID of the agent
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_inactive: Whether to include inactive properties
            
        Returns:
            Tuple of (properties list, total count)
        """
        try:
            query = (
                select(Property)
                .options(selectinload(Property.images))
                .where(Property.agent_id == agent_id)
            )
            
            count_query = select(func.count(Property.id)).where(Property.agent_id == agent_id)
            
            if not include_inactive:
                query = query.where(Property.is_active == True)
                count_query = count_query.where(Property.is_active == True)
            
            # Get total count
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()
            
            # Apply pagination and ordering
            query = query.order_by(desc(Property.updated_at)).offset(skip).limit(limit)
            
            result = await self.db.execute(query)
            properties = result.scalars().all()
            
            logger.debug(f"Retrieved {len(properties)} properties for agent {agent_id}")
            return list(properties), total_count
        except Exception as e:
            logger.error(f"Failed to get properties by agent {agent_id}: {e}")
            raise
    
    async def get_nearby_properties(
        self,
        latitude: Decimal,
        longitude: Decimal,
        radius_km: float = 5.0,
        limit: int = 20,
        property_type: Optional[PropertyType] = None
    ) -> List[Property]:
        """
        Get properties within a specified radius of coordinates.
        Uses Haversine formula for distance calculation.
        
        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_km: Search radius in kilometers
            limit: Maximum number of properties to return
            property_type: Optional property type filter
            
        Returns:
            List of nearby properties ordered by distance
        """
        try:
            # Haversine formula for distance calculation
            distance_formula = func.acos(
                func.sin(func.radians(latitude)) * func.sin(func.radians(Property.latitude)) +
                func.cos(func.radians(latitude)) * func.cos(func.radians(Property.latitude)) *
                func.cos(func.radians(Property.longitude) - func.radians(longitude))
            ) * 6371  # Earth's radius in km
            
            query = (
                select(Property, distance_formula.label('distance'))
                .options(
                    selectinload(Property.agent),
                    selectinload(Property.images)
                )
                .where(
                    and_(
                        Property.latitude.isnot(None),
                        Property.longitude.isnot(None),
                        Property.is_active == True,
                        distance_formula <= radius_km
                    )
                )
            )
            
            if property_type:
                query = query.where(Property.property_type == property_type)
            
            query = query.order_by('distance').limit(limit)
            
            result = await self.db.execute(query)
            properties_with_distance = result.all()
            
            # Extract just the properties (without distance)
            properties = [row[0] for row in properties_with_distance]
            
            logger.debug(f"Found {len(properties)} properties within {radius_km}km")
            return properties
        except Exception as e:
            logger.error(f"Failed to get nearby properties: {e}")
            raise
    
    async def get_property_statistics(self, agent_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """
        Get property statistics for dashboard/reporting.
        
        Args:
            agent_id: Optional agent ID to filter statistics
            
        Returns:
            Dictionary with various property statistics
        """
        try:
            base_query = select(Property)
            if agent_id:
                base_query = base_query.where(Property.agent_id == agent_id)
            
            # Total properties
            total_query = select(func.count(Property.id))
            if agent_id:
                total_query = total_query.where(Property.agent_id == agent_id)
            
            total_result = await self.db.execute(total_query)
            total_properties = total_result.scalar()
            
            # Active properties
            active_query = select(func.count(Property.id)).where(Property.is_active == True)
            if agent_id:
                active_query = active_query.where(Property.agent_id == agent_id)
            
            active_result = await self.db.execute(active_query)
            active_properties = active_result.scalar()
            
            # Properties by type
            type_query = (
                select(Property.property_type, func.count(Property.id))
                .where(Property.is_active == True)
                .group_by(Property.property_type)
            )
            if agent_id:
                type_query = type_query.where(Property.agent_id == agent_id)
            
            type_result = await self.db.execute(type_query)
            properties_by_type = {row[0].value: row[1] for row in type_result.all()}
            
            # Average price by type
            avg_price_query = (
                select(Property.property_type, func.avg(Property.price))
                .where(Property.is_active == True)
                .group_by(Property.property_type)
            )
            if agent_id:
                avg_price_query = avg_price_query.where(Property.agent_id == agent_id)
            
            avg_price_result = await self.db.execute(avg_price_query)
            avg_prices = {row[0].value: float(row[1]) for row in avg_price_result.all()}
            
            # Price range statistics
            price_stats_query = (
                select(
                    func.min(Property.price),
                    func.max(Property.price),
                    func.avg(Property.price)
                )
                .where(Property.is_active == True)
            )
            if agent_id:
                price_stats_query = price_stats_query.where(Property.agent_id == agent_id)
            
            price_stats_result = await self.db.execute(price_stats_query)
            min_price, max_price, avg_price = price_stats_result.first()
            
            statistics = {
                "total_properties": total_properties,
                "active_properties": active_properties,
                "inactive_properties": total_properties - active_properties,
                "properties_by_type": properties_by_type,
                "average_prices_by_type": avg_prices,
                "price_statistics": {
                    "min_price": float(min_price) if min_price else 0,
                    "max_price": float(max_price) if max_price else 0,
                    "avg_price": float(avg_price) if avg_price else 0
                }
            }
            
            logger.debug(f"Generated property statistics for agent {agent_id}")
            return statistics
        except Exception as e:
            logger.error(f"Failed to get property statistics: {e}")
            raise
    
    async def update_property_status(self, property_id: uuid.UUID, is_active: bool) -> Optional[Property]:
        """
        Update property active status.
        
        Args:
            property_id: UUID of the property
            is_active: New active status
            
        Returns:
            Updated property or None if not found
        """
        try:
            updated_property = await self.update(property_id, {"is_active": is_active})
            if updated_property:
                status = "activated" if is_active else "deactivated"
                logger.info(f"Property {property_id} {status}")
            return updated_property
        except Exception as e:
            logger.error(f"Failed to update property status {property_id}: {e}")
            raise
    
    async def delete_property_with_images(self, property_id: uuid.UUID) -> bool:
        """
        Delete property and all associated images.
        Uses CASCADE delete configured in the model.
        
        Args:
            property_id: UUID of the property to delete
            
        Returns:
            True if property was deleted, False if not found
        """
        try:
            # The CASCADE delete in the model will handle image deletion
            deleted = await self.delete(property_id)
            if deleted:
                logger.info(f"Deleted property {property_id} with all associated images")
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete property with images {property_id}: {e}")
            raise
    
    async def get_featured_properties(self, limit: int = 10) -> List[Property]:
        """
        Get featured properties (properties with images, ordered by recent updates).
        
        Args:
            limit: Maximum number of properties to return
            
        Returns:
            List of featured properties
        """
        try:
            # Subquery to get properties that have images
            properties_with_images = (
                select(Property.id)
                .join(PropertyImage)
                .where(Property.is_active == True)
                .distinct()
            )
            
            query = (
                select(Property)
                .options(
                    selectinload(Property.agent),
                    selectinload(Property.images)
                )
                .where(Property.id.in_(properties_with_images))
                .order_by(desc(Property.updated_at))
                .limit(limit)
            )
            
            result = await self.db.execute(query)
            properties = result.scalars().all()
            
            logger.debug(f"Retrieved {len(properties)} featured properties")
            return list(properties)
        except Exception as e:
            logger.error(f"Failed to get featured properties: {e}")
            raise