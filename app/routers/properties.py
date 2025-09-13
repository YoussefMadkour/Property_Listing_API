"""
Property management API endpoints for CRUD operations, search, and filtering.
Provides comprehensive property management with authentication and authorization.
"""

from fastapi import APIRouter, Depends, status, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID
import math

from app.database import get_db
from app.models.user import User
from app.models.property import PropertyType
from app.services.property import PropertyService
from app.schemas.property import (
    PropertyCreate,
    PropertyUpdate,
    PropertyResponse,
    PropertyListResponse,
    PropertySearchFilters,
    PropertySummary
)
from app.utils.dependencies import (
    get_current_active_user,
    get_optional_current_user,
    get_property_service
)
from app.utils.exceptions import (
    NotFoundError,
    ForbiddenError,
    ValidationError,
    BadRequestError,
    InsufficientPermissionsError
)
from app.schemas.error import get_crud_error_responses, get_common_error_responses


router = APIRouter(prefix="/properties", tags=["Properties"])


@router.post(
    "",
    response_model=PropertyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new property",
    description="Create a new property listing. Requires agent or admin role.",
    responses=get_crud_error_responses()
)
async def create_property(
    property_data: PropertyCreate,
    current_user: User = Depends(get_current_active_user),
    property_service: PropertyService = Depends(get_property_service)
) -> PropertyResponse:
    """
    Create a new property listing.
    
    Args:
        property_data: Property creation data
        current_user: Current authenticated user
        property_service: Property service instance
        
    Returns:
        Created property with details
        
    Raises:
        ForbiddenError: If user doesn't have permission to create properties
        ValidationError: If property data is invalid
        BadRequestError: If business rules are violated
    """
    try:
        # Create property
        property_obj = await property_service.create_property(property_data, current_user)
        
        # Convert to response format
        return PropertyResponse.model_validate(property_obj.to_dict())
        
    except (ForbiddenError, ValidationError, BadRequestError, InsufficientPermissionsError):
        raise
    except Exception as e:
        raise BadRequestError(f"Failed to create property: {str(e)}")


@router.get(
    "",
    response_model=PropertyListResponse,
    status_code=status.HTTP_200_OK,
    summary="List properties with search and filtering",
    description="Get paginated list of properties with optional search filters"
)
async def list_properties(
    # Search parameters
    query: Optional[str] = Query(None, description="Search query for title and description"),
    location: Optional[str] = Query(None, description="Location filter"),
    
    # Price filters
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    
    # Property specification filters
    bedrooms: Optional[int] = Query(None, ge=0, le=50, description="Minimum number of bedrooms"),
    bathrooms: Optional[int] = Query(None, ge=0, le=50, description="Minimum number of bathrooms"),
    min_area: Optional[int] = Query(None, gt=0, description="Minimum area in square feet"),
    max_area: Optional[int] = Query(None, gt=0, description="Maximum area in square feet"),
    
    # Property type filter
    property_type: Optional[str] = Query(None, description="Property type (rental/sale)"),
    
    # Status filter
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    
    # Agent filter (admin only)
    agent_id: Optional[str] = Query(None, description="Filter by agent ID (admin only)"),
    
    # Pagination
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Number of properties per page"),
    
    # Sorting
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    
    # Dependencies
    current_user: Optional[User] = Depends(get_optional_current_user),
    property_service: PropertyService = Depends(get_property_service)
) -> PropertyListResponse:
    """
    Get paginated list of properties with search and filtering capabilities.
    
    Args:
        Various query parameters for filtering and pagination
        current_user: Optional current authenticated user
        property_service: Property service instance
        
    Returns:
        Paginated list of properties with metadata
    """
    try:
        # Convert property_type string to enum if provided
        property_type_enum = None
        if property_type:
            try:
                property_type_enum = PropertyType(property_type.lower())
            except ValueError:
                raise ValidationError(f"Invalid property type: {property_type}. Must be 'rental' or 'sale'")
        
        # Create search filters
        search_filters = PropertySearchFilters(
            query=query,
            location=location,
            min_price=min_price,
            max_price=max_price,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            min_area=min_area,
            max_area=max_area,
            property_type=property_type_enum,
            is_active=is_active,
            agent_id=agent_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Search properties
        properties, total_count = await property_service.search_properties(
            search_filters, current_user
        )
        
        # Convert to response format
        property_responses = [
            PropertyResponse.model_validate(prop.to_dict()) 
            for prop in properties
        ]
        
        # Calculate pagination metadata
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        has_next = page < total_pages
        has_previous = page > 1
        
        return PropertyListResponse(
            properties=property_responses,
            total=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous
        )
        
    except (ValidationError, ForbiddenError):
        raise
    except Exception as e:
        raise BadRequestError(f"Failed to search properties: {str(e)}")


@router.get(
    "/{property_id}",
    response_model=PropertyResponse,
    status_code=status.HTTP_200_OK,
    summary="Get property details",
    description="Get detailed information about a specific property"
)
async def get_property(
    property_id: UUID = Path(..., description="Property ID"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    property_service: PropertyService = Depends(get_property_service)
) -> PropertyResponse:
    """
    Get detailed information about a specific property.
    
    Args:
        property_id: UUID of the property
        current_user: Optional current authenticated user
        property_service: Property service instance
        
    Returns:
        Property details with related information
        
    Raises:
        NotFoundError: If property doesn't exist
        ForbiddenError: If user doesn't have permission to view property
    """
    try:
        # Get property
        property_obj = await property_service.get_property(property_id, current_user)
        
        # Convert to response format
        return PropertyResponse.model_validate(property_obj.to_dict())
        
    except (NotFoundError, ForbiddenError):
        raise
    except Exception as e:
        raise BadRequestError(f"Failed to retrieve property: {str(e)}")


@router.put(
    "/{property_id}",
    response_model=PropertyResponse,
    status_code=status.HTTP_200_OK,
    summary="Update property",
    description="Update property details. Only property owner or admin can update."
)
async def update_property(
    property_id: UUID = Path(..., description="Property ID"),
    property_data: PropertyUpdate = ...,
    current_user: User = Depends(get_current_active_user),
    property_service: PropertyService = Depends(get_property_service)
) -> PropertyResponse:
    """
    Update property details.
    
    Args:
        property_id: UUID of the property to update
        property_data: Property update data
        current_user: Current authenticated user
        property_service: Property service instance
        
    Returns:
        Updated property details
        
    Raises:
        NotFoundError: If property doesn't exist
        ForbiddenError: If user doesn't have permission to update property
        ValidationError: If update data is invalid
    """
    try:
        # Update property
        updated_property = await property_service.update_property(
            property_id, property_data, current_user
        )
        
        # Convert to response format
        return PropertyResponse.model_validate(updated_property.to_dict())
        
    except (NotFoundError, ForbiddenError, ValidationError, InsufficientPermissionsError):
        raise
    except Exception as e:
        raise BadRequestError(f"Failed to update property: {str(e)}")


@router.delete(
    "/{property_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete property",
    description="Delete property listing. Only property owner or admin can delete."
)
async def delete_property(
    property_id: UUID = Path(..., description="Property ID"),
    current_user: User = Depends(get_current_active_user),
    property_service: PropertyService = Depends(get_property_service)
) -> None:
    """
    Delete property listing.
    
    Args:
        property_id: UUID of the property to delete
        current_user: Current authenticated user
        property_service: Property service instance
        
    Raises:
        NotFoundError: If property doesn't exist
        ForbiddenError: If user doesn't have permission to delete property
    """
    try:
        # Delete property
        deleted = await property_service.delete_property(property_id, current_user)
        
        if not deleted:
            raise NotFoundError("Property", str(property_id))
            
    except (NotFoundError, ForbiddenError, InsufficientPermissionsError):
        raise
    except Exception as e:
        raise BadRequestError(f"Failed to delete property: {str(e)}")


@router.get(
    "/search/advanced",
    response_model=PropertyListResponse,
    status_code=status.HTTP_200_OK,
    summary="Advanced property search",
    description="Advanced search with complex filtering options"
)
async def advanced_search(
    search_filters: PropertySearchFilters,
    current_user: Optional[User] = Depends(get_optional_current_user),
    property_service: PropertyService = Depends(get_property_service)
) -> PropertyListResponse:
    """
    Advanced property search with complex filtering.
    
    Args:
        search_filters: Advanced search filters
        current_user: Optional current authenticated user
        property_service: Property service instance
        
    Returns:
        Paginated search results with metadata
    """
    try:
        # Search properties
        properties, total_count = await property_service.search_properties(
            search_filters, current_user
        )
        
        # Convert to response format
        property_responses = [
            PropertyResponse.model_validate(prop.to_dict()) 
            for prop in properties
        ]
        
        # Calculate pagination metadata
        total_pages = math.ceil(total_count / search_filters.page_size) if total_count > 0 else 1
        has_next = search_filters.page < total_pages
        has_previous = search_filters.page > 1
        
        return PropertyListResponse(
            properties=property_responses,
            total=total_count,
            page=search_filters.page,
            page_size=search_filters.page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous
        )
        
    except (ValidationError, ForbiddenError):
        raise
    except Exception as e:
        raise BadRequestError(f"Failed to perform advanced search: {str(e)}")


@router.get(
    "/nearby/location",
    response_model=List[PropertyResponse],
    status_code=status.HTTP_200_OK,
    summary="Find nearby properties",
    description="Find properties near specified coordinates"
)
async def get_nearby_properties(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude coordinate"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude coordinate"),
    radius_km: float = Query(5.0, gt=0, le=100, description="Search radius in kilometers"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of properties"),
    property_type: Optional[str] = Query(None, description="Property type filter"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    property_service: PropertyService = Depends(get_property_service)
) -> List[PropertyResponse]:
    """
    Find properties near specified coordinates.
    
    Args:
        latitude: Center latitude
        longitude: Center longitude
        radius_km: Search radius in kilometers
        limit: Maximum number of properties
        property_type: Optional property type filter
        current_user: Optional current authenticated user
        property_service: Property service instance
        
    Returns:
        List of nearby properties
    """
    try:
        # Convert property_type string to enum if provided
        property_type_enum = None
        if property_type:
            try:
                property_type_enum = PropertyType(property_type.lower())
            except ValueError:
                raise ValidationError(f"Invalid property type: {property_type}. Must be 'rental' or 'sale'")
        
        # Get nearby properties
        properties = await property_service.get_nearby_properties(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            limit=limit,
            property_type=property_type_enum,
            current_user=current_user
        )
        
        # Convert to response format
        return [
            PropertyResponse.model_validate(prop.to_dict()) 
            for prop in properties
        ]
        
    except ValidationError:
        raise
    except Exception as e:
        raise BadRequestError(f"Failed to find nearby properties: {str(e)}")


@router.get(
    "/featured/list",
    response_model=List[PropertyResponse],
    status_code=status.HTTP_200_OK,
    summary="Get featured properties",
    description="Get featured properties (properties with images)"
)
async def get_featured_properties(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of properties"),
    property_service: PropertyService = Depends(get_property_service)
) -> List[PropertyResponse]:
    """
    Get featured properties (properties with images).
    
    Args:
        limit: Maximum number of properties
        property_service: Property service instance
        
    Returns:
        List of featured properties
    """
    try:
        # Get featured properties
        properties = await property_service.get_featured_properties(limit)
        
        # Convert to response format
        return [
            PropertyResponse.model_validate(prop.to_dict()) 
            for prop in properties
        ]
        
    except ValidationError:
        raise
    except Exception as e:
        raise BadRequestError(f"Failed to get featured properties: {str(e)}")


@router.patch(
    "/{property_id}/status",
    response_model=PropertyResponse,
    status_code=status.HTTP_200_OK,
    summary="Toggle property status",
    description="Toggle property active/inactive status"
)
async def toggle_property_status(
    property_id: UUID = Path(..., description="Property ID"),
    current_user: User = Depends(get_current_active_user),
    property_service: PropertyService = Depends(get_property_service)
) -> PropertyResponse:
    """
    Toggle property active/inactive status.
    
    Args:
        property_id: UUID of the property
        current_user: Current authenticated user
        property_service: Property service instance
        
    Returns:
        Updated property with new status
    """
    try:
        # Toggle status
        updated_property = await property_service.toggle_property_status(
            property_id, current_user
        )
        
        # Convert to response format
        return PropertyResponse.model_validate(updated_property.to_dict())
        
    except (NotFoundError, ForbiddenError, InsufficientPermissionsError):
        raise
    except Exception as e:
        raise BadRequestError(f"Failed to toggle property status: {str(e)}")


@router.get(
    "/agent/{agent_id}",
    response_model=PropertyListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get agent's properties",
    description="Get properties owned by a specific agent"
)
async def get_agent_properties(
    agent_id: UUID = Path(..., description="Agent ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Properties per page"),
    include_inactive: bool = Query(False, description="Include inactive properties"),
    current_user: User = Depends(get_current_active_user),
    property_service: PropertyService = Depends(get_property_service)
) -> PropertyListResponse:
    """
    Get properties owned by a specific agent.
    
    Args:
        agent_id: UUID of the agent
        page: Page number
        page_size: Properties per page
        include_inactive: Include inactive properties
        current_user: Current authenticated user
        property_service: Property service instance
        
    Returns:
        Paginated list of agent's properties
    """
    try:
        # Calculate skip
        skip = (page - 1) * page_size
        
        # Get agent properties
        properties, total_count = await property_service.get_user_properties(
            user_id=agent_id,
            current_user=current_user,
            skip=skip,
            limit=page_size,
            include_inactive=include_inactive
        )
        
        # Convert to response format
        property_responses = [
            PropertyResponse.model_validate(prop.to_dict()) 
            for prop in properties
        ]
        
        # Calculate pagination metadata
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        has_next = page < total_pages
        has_previous = page > 1
        
        return PropertyListResponse(
            properties=property_responses,
            total=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous
        )
        
    except (NotFoundError, ForbiddenError, InsufficientPermissionsError):
        raise
    except Exception as e:
        raise BadRequestError(f"Failed to get agent properties: {str(e)}")


@router.get(
    "/statistics/summary",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get property statistics",
    description="Get property statistics for current user or specified agent"
)
async def get_property_statistics(
    agent_id: Optional[UUID] = Query(None, description="Agent ID (admin only)"),
    current_user: User = Depends(get_current_active_user),
    property_service: PropertyService = Depends(get_property_service)
) -> dict:
    """
    Get property statistics.
    
    Args:
        agent_id: Optional agent ID (admin only)
        current_user: Current authenticated user
        property_service: Property service instance
        
    Returns:
        Property statistics dictionary
    """
    try:
        # Get statistics
        statistics = await property_service.get_property_statistics(
            current_user=current_user,
            agent_id=agent_id
        )
        
        return statistics
        
    except (ForbiddenError, InsufficientPermissionsError):
        raise
    except Exception as e:
        raise BadRequestError(f"Failed to get property statistics: {str(e)}")