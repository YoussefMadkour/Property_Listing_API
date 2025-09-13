"""
Comprehensive tests for service classes.
Tests business logic, authentication, authorization, and service interactions.
"""

import pytest
import uuid
from decimal import Decimal
from unittest.mock import Mock, patch

from app.models.user import User, UserRole
from app.models.property import Property, PropertyType
from app.services.auth import AuthService
from app.services.property import PropertyService
from app.schemas.user import UserCreate
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertySearchFilters
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
from tests.conftest import UserFactory, PropertyFactory


class TestAuthService:
    """Test AuthService functionality."""
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_service: AuthService, test_agent: User):
        """Test successful user authentication."""
        # Use known password from test fixture
        password = "testpassword123"
        
        authenticated_user = await auth_service.authenticate_user(test_agent.email, password)
        
        assert authenticated_user is not None
        assert authenticated_user.id == test_agent.id
        assert authenticated_user.email == test_agent.email
    
    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_credentials(self, auth_service: AuthService, test_agent: User):
        """Test authentication with invalid credentials."""
        with pytest.raises(InvalidCredentialsError):
            await auth_service.authenticate_user(test_agent.email, "wrongpassword")
    
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, auth_service: AuthService):
        """Test authentication with non-existent user."""
        with pytest.raises(InvalidCredentialsError):
            await auth_service.authenticate_user("nonexistent@example.com", "password")
    
    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(self, auth_service: AuthService, test_inactive_user: User):
        """Test authentication with inactive user."""
        with pytest.raises(InvalidCredentialsError):
            await auth_service.authenticate_user(test_inactive_user.email, "testpassword123")
    
    @pytest.mark.asyncio
    async def test_authenticate_user_empty_email(self, auth_service: AuthService):
        """Test authentication with empty email."""
        with pytest.raises(ValidationError, match="Email is required"):
            await auth_service.authenticate_user("", "password")
    
    @pytest.mark.asyncio
    async def test_authenticate_user_empty_password(self, auth_service: AuthService):
        """Test authentication with empty password."""
        with pytest.raises(ValidationError, match="Password is required"):
            await auth_service.authenticate_user("test@example.com", "")
    
    @pytest.mark.asyncio
    async def test_create_tokens(self, auth_service: AuthService, test_agent: User):
        """Test token creation."""
        access_token, refresh_token = await auth_service.create_tokens(test_agent)
        
        assert access_token is not None
        assert refresh_token is not None
        assert isinstance(access_token, str)
        assert isinstance(refresh_token, str)
        assert len(access_token) > 50  # JWT tokens are long
        assert len(refresh_token) > 50
    
    @pytest.mark.asyncio
    async def test_login_success(self, auth_service: AuthService, test_agent: User):
        """Test successful login flow."""
        password = "testpassword123"
        
        user, access_token, refresh_token = await auth_service.login(test_agent.email, password)
        
        assert user.id == test_agent.id
        assert access_token is not None
        assert refresh_token is not None
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, auth_service: AuthService, test_agent: User):
        """Test login with invalid credentials."""
        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(test_agent.email, "wrongpassword")
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, auth_service: AuthService, test_agent: User):
        """Test getting user by ID."""
        retrieved_user = await auth_service.get_user_by_id(test_agent.id)
        
        assert retrieved_user.id == test_agent.id
        assert retrieved_user.email == test_agent.email
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, auth_service: AuthService):
        """Test getting non-existent user by ID."""
        non_existent_id = uuid.uuid4()
        
        with pytest.raises(NotFoundError):
            await auth_service.get_user_by_id(non_existent_id)
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_invalid_uuid(self, auth_service: AuthService):
        """Test getting user with invalid UUID."""
        with pytest.raises(ValidationError, match="User ID is required"):
            await auth_service.get_user_by_id(None)
    
    @pytest.mark.asyncio
    async def test_get_user_by_email_success(self, auth_service: AuthService, test_agent: User):
        """Test getting user by email."""
        retrieved_user = await auth_service.get_user_by_email(test_agent.email)
        
        assert retrieved_user is not None
        assert retrieved_user.id == test_agent.id
    
    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, auth_service: AuthService):
        """Test getting non-existent user by email."""
        retrieved_user = await auth_service.get_user_by_email("nonexistent@example.com")
        
        assert retrieved_user is None
    
    @pytest.mark.asyncio
    async def test_get_user_by_email_empty(self, auth_service: AuthService):
        """Test getting user with empty email."""
        with pytest.raises(ValidationError, match="Email is required"):
            await auth_service.get_user_by_email("")
    
    def test_verify_user_permissions_admin(self, test_admin: User):
        """Test admin user permissions."""
        auth_service = AuthService(Mock())
        
        # Admin should have access to everything
        assert auth_service.verify_user_permissions(test_admin, UserRole.AGENT) is True
        assert auth_service.verify_user_permissions(test_admin, UserRole.ADMIN) is True
    
    def test_verify_user_permissions_agent(self, test_agent: User):
        """Test agent user permissions."""
        auth_service = AuthService(Mock())
        
        # Agent should only have agent permissions
        assert auth_service.verify_user_permissions(test_agent, UserRole.AGENT) is True
        assert auth_service.verify_user_permissions(test_agent, UserRole.ADMIN) is False
    
    def test_can_manage_resource_admin(self, test_admin: User):
        """Test admin resource management permissions."""
        auth_service = AuthService(Mock())
        other_user_id = uuid.uuid4()
        
        # Admin can manage all resources
        assert auth_service.can_manage_resource(test_admin, other_user_id) is True
        assert auth_service.can_manage_resource(test_admin, test_admin.id) is True
    
    def test_can_manage_resource_agent(self, test_agent: User):
        """Test agent resource management permissions."""
        auth_service = AuthService(Mock())
        other_user_id = uuid.uuid4()
        
        # Agent can only manage their own resources
        assert auth_service.can_manage_resource(test_agent, test_agent.id) is True
        assert auth_service.can_manage_resource(test_agent, other_user_id) is False
    
    @pytest.mark.asyncio
    async def test_create_user_as_admin(self, auth_service: AuthService, test_admin: User):
        """Test creating user as admin."""
        user_data = UserCreate(
            email="newuser@example.com",
            password="newpassword123",
            full_name="New User",
            role=UserRole.AGENT
        )
        
        created_user = await auth_service.create_user(user_data, test_admin)
        
        assert created_user.email == "newuser@example.com"
        assert created_user.full_name == "New User"
        assert created_user.role == UserRole.AGENT
    
    @pytest.mark.asyncio
    async def test_create_user_as_agent(self, auth_service: AuthService, test_agent: User):
        """Test creating user as agent (should fail)."""
        user_data = UserCreate(
            email="newuser@example.com",
            password="newpassword123",
            full_name="New User",
            role=UserRole.AGENT
        )
        
        with pytest.raises(InsufficientPermissionsError):
            await auth_service.create_user(user_data, test_agent)
    
    @pytest.mark.asyncio
    async def test_create_admin_user_as_agent(self, auth_service: AuthService, test_admin: User):
        """Test creating admin user (only admin can do this)."""
        user_data = UserCreate(
            email="newadmin@example.com",
            password="newpassword123",
            full_name="New Admin",
            role=UserRole.ADMIN
        )
        
        # Should work for admin
        created_user = await auth_service.create_user(user_data, test_admin)
        assert created_user.role == UserRole.ADMIN
    
    @pytest.mark.asyncio
    async def test_update_user_role_as_admin(self, auth_service: AuthService, test_admin: User, test_agent: User):
        """Test updating user role as admin."""
        updated_user = await auth_service.update_user_role(
            test_agent.id, UserRole.ADMIN, test_admin
        )
        
        assert updated_user.role == UserRole.ADMIN
    
    @pytest.mark.asyncio
    async def test_update_user_role_as_agent(self, auth_service: AuthService, test_agent: User):
        """Test updating user role as agent (should fail)."""
        other_agent_id = uuid.uuid4()
        
        with pytest.raises(InsufficientPermissionsError):
            await auth_service.update_user_role(other_agent_id, UserRole.ADMIN, test_agent)
    
    @pytest.mark.asyncio
    async def test_update_own_role(self, auth_service: AuthService, test_admin: User):
        """Test updating own role (should fail)."""
        with pytest.raises(ForbiddenError, match="cannot change their own role"):
            await auth_service.update_user_role(test_admin.id, UserRole.AGENT, test_admin)
    
    @pytest.mark.asyncio
    async def test_update_user_status_as_admin(self, auth_service: AuthService, test_admin: User, test_agent: User):
        """Test updating user status as admin."""
        updated_user = await auth_service.update_user_status(
            test_agent.id, False, test_admin
        )
        
        assert updated_user.is_active is False
    
    @pytest.mark.asyncio
    async def test_deactivate_self(self, auth_service: AuthService, test_admin: User):
        """Test deactivating own account (should fail)."""
        with pytest.raises(ForbiddenError, match="cannot deactivate their own account"):
            await auth_service.update_user_status(test_admin.id, False, test_admin)
    
    @pytest.mark.asyncio
    async def test_change_password_own(self, auth_service: AuthService, test_agent: User):
        """Test changing own password."""
        current_password = "testpassword123"
        new_password = "newpassword123"
        
        updated_user = await auth_service.change_password(
            test_agent.id, current_password, new_password, test_agent
        )
        
        assert updated_user.verify_password(new_password)
        assert not updated_user.verify_password(current_password)
    
    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, auth_service: AuthService, test_agent: User):
        """Test changing password with wrong current password."""
        with pytest.raises(InvalidCredentialsError, match="Current password is incorrect"):
            await auth_service.change_password(
                test_agent.id, "wrongpassword", "newpassword123", test_agent
            )
    
    @pytest.mark.asyncio
    async def test_change_password_as_admin(self, auth_service: AuthService, test_admin: User, test_agent: User):
        """Test admin changing another user's password."""
        new_password = "adminsetpassword123"
        
        updated_user = await auth_service.change_password(
            test_agent.id, "", new_password, test_admin  # Admin doesn't need current password
        )
        
        assert updated_user.verify_password(new_password)
    
    @pytest.mark.asyncio
    async def test_change_password_invalid_new_password(self, auth_service: AuthService, test_agent: User):
        """Test changing to invalid new password."""
        with pytest.raises(ValidationError, match="must be at least 8 characters"):
            await auth_service.change_password(
                test_agent.id, "testpassword123", "short", test_agent
            )


class TestPropertyService:
    """Test PropertyService functionality."""
    
    @pytest.mark.asyncio
    async def test_create_property_success(self, property_service: PropertyService, test_agent: User):
        """Test successful property creation."""
        property_data = PropertyCreate(
            title="Test Property",
            description="A beautiful test property",
            property_type=PropertyType.RENTAL,
            price=Decimal("1500.00"),
            bedrooms=3,
            bathrooms=2,
            area_sqft=1200,
            location="Test City"
        )
        
        created_property = await property_service.create_property(property_data, test_agent)
        
        assert created_property.title == "Test Property"
        assert created_property.price == Decimal("1500.00")
        assert created_property.agent_id == test_agent.id
        assert created_property.is_active is True
    
    @pytest.mark.asyncio
    async def test_create_property_as_admin(self, property_service: PropertyService, test_admin: User):
        """Test property creation as admin."""
        property_data = PropertyCreate(
            title="Admin Property",
            description="Property created by admin",
            property_type=PropertyType.SALE,
            price=Decimal("500000.00"),
            bedrooms=4,
            bathrooms=3,
            area_sqft=2000,
            location="Admin City"
        )
        
        created_property = await property_service.create_property(property_data, test_admin)
        
        assert created_property.title == "Admin Property"
        assert created_property.agent_id == test_admin.id
    
    @pytest.mark.asyncio
    async def test_create_property_inactive_user(self, property_service: PropertyService, test_inactive_user: User):
        """Test property creation with inactive user."""
        property_data = PropertyCreate(
            title="Test Property",
            description="A test property",
            property_type=PropertyType.RENTAL,
            price=Decimal("1500.00"),
            bedrooms=3,
            bathrooms=2,
            area_sqft=1200,
            location="Test City"
        )
        
        with pytest.raises(ForbiddenError, match="Inactive users cannot create properties"):
            await property_service.create_property(property_data, test_inactive_user)
    
    @pytest.mark.asyncio
    async def test_create_property_invalid_data(self, property_service: PropertyService, test_agent: User):
        """Test property creation with invalid data."""
        property_data = PropertyCreate(
            title="Test Property",
            description="A test property",
            property_type=PropertyType.RENTAL,
            price=Decimal("-100.00"),  # Invalid negative price
            bedrooms=3,
            bathrooms=2,
            area_sqft=1200,
            location="Test City"
        )
        
        with pytest.raises(ValidationError):
            await property_service.create_property(property_data, test_agent)
    
    @pytest.mark.asyncio
    async def test_get_property_success(self, property_service: PropertyService, test_property: Property, test_agent: User):
        """Test getting property successfully."""
        retrieved_property = await property_service.get_property(test_property.id, test_agent)
        
        assert retrieved_property.id == test_property.id
        assert retrieved_property.title == test_property.title
    
    @pytest.mark.asyncio
    async def test_get_property_not_found(self, property_service: PropertyService, test_agent: User):
        """Test getting non-existent property."""
        non_existent_id = uuid.uuid4()
        
        with pytest.raises(NotFoundError):
            await property_service.get_property(non_existent_id, test_agent)
    
    @pytest.mark.asyncio
    async def test_get_inactive_property_as_owner(self, property_service: PropertyService, test_inactive_property: Property, test_agent: User):
        """Test getting inactive property as owner."""
        # Owner should be able to see their inactive properties
        retrieved_property = await property_service.get_property(test_inactive_property.id, test_agent)
        
        assert retrieved_property.id == test_inactive_property.id
        assert retrieved_property.is_active is False
    
    @pytest.mark.asyncio
    async def test_get_inactive_property_anonymous(self, property_service: PropertyService, test_inactive_property: Property):
        """Test getting inactive property without authentication."""
        # Anonymous users should not see inactive properties
        with pytest.raises(NotFoundError):
            await property_service.get_property(test_inactive_property.id, None)
    
    @pytest.mark.asyncio
    async def test_update_property_success(self, property_service: PropertyService, test_property: Property, test_agent: User):
        """Test successful property update."""
        update_data = PropertyUpdate(
            title="Updated Property Title",
            price=Decimal("2000.00")
        )
        
        updated_property = await property_service.update_property(
            test_property.id, update_data, test_agent
        )
        
        assert updated_property.title == "Updated Property Title"
        assert updated_property.price == Decimal("2000.00")
        assert updated_property.id == test_property.id
    
    @pytest.mark.asyncio
    async def test_update_property_not_owner(self, property_service: PropertyService, test_property: Property, test_admin: User):
        """Test updating property as admin (should work)."""
        update_data = PropertyUpdate(title="Admin Updated Title")
        
        updated_property = await property_service.update_property(
            test_property.id, update_data, test_admin
        )
        
        assert updated_property.title == "Admin Updated Title"
    
    @pytest.mark.asyncio
    async def test_update_property_unauthorized(self, property_service: PropertyService, test_property: Property, user_repository):
        """Test updating property without permission."""
        # Create another agent
        other_agent = await UserFactory.create_user(
            user_repository,
            email="other@example.com",
            role=UserRole.AGENT
        )
        
        update_data = PropertyUpdate(title="Unauthorized Update")
        
        with pytest.raises(InsufficientPermissionsError):
            await property_service.update_property(test_property.id, update_data, other_agent)
    
    @pytest.mark.asyncio
    async def test_update_property_empty_data(self, property_service: PropertyService, test_property: Property, test_agent: User):
        """Test updating property with empty data."""
        update_data = PropertyUpdate()  # All fields are None
        
        with pytest.raises(ValidationError, match="No valid fields provided"):
            await property_service.update_property(test_property.id, update_data, test_agent)
    
    @pytest.mark.asyncio
    async def test_delete_property_success(self, property_service: PropertyService, test_property: Property, test_agent: User):
        """Test successful property deletion."""
        deleted = await property_service.delete_property(test_property.id, test_agent)
        
        assert deleted is True
        
        # Verify property is deleted
        with pytest.raises(NotFoundError):
            await property_service.get_property(test_property.id, test_agent)
    
    @pytest.mark.asyncio
    async def test_delete_property_as_admin(self, property_service: PropertyService, test_property: Property, test_admin: User):
        """Test deleting property as admin."""
        deleted = await property_service.delete_property(test_property.id, test_admin)
        
        assert deleted is True
    
    @pytest.mark.asyncio
    async def test_delete_property_unauthorized(self, property_service: PropertyService, test_property: Property, user_repository):
        """Test deleting property without permission."""
        # Create another agent
        other_agent = await UserFactory.create_user(
            user_repository,
            email="other@example.com",
            role=UserRole.AGENT
        )
        
        with pytest.raises(InsufficientPermissionsError):
            await property_service.delete_property(test_property.id, other_agent)
    
    @pytest.mark.asyncio
    async def test_search_properties_basic(self, property_service: PropertyService, test_property: Property):
        """Test basic property search."""
        search_filters = PropertySearchFilters(
            page=1,
            page_size=10,
            sort_by="created_at",
            sort_order="desc"
        )
        
        properties, total_count = await property_service.search_properties(search_filters)
        
        assert len(properties) >= 1
        assert total_count >= 1
        assert any(prop.id == test_property.id for prop in properties)
    
    @pytest.mark.asyncio
    async def test_search_properties_by_location(self, property_service: PropertyService, property_repository, test_agent: User):
        """Test searching properties by location."""
        # Create property with specific location
        prop_data = PropertyFactory.create_property_data(
            title="Dubai Property",
            location="Dubai Marina",
            agent_id=test_agent.id
        )
        await property_repository.create_property(prop_data)
        
        search_filters = PropertySearchFilters(
            location="Dubai",
            page=1,
            page_size=10
        )
        
        properties, total_count = await property_service.search_properties(search_filters)
        
        assert len(properties) >= 1
        assert all("Dubai" in prop.location for prop in properties)
    
    @pytest.mark.asyncio
    async def test_search_properties_price_range_invalid(self, property_service: PropertyService):
        """Test searching with invalid price range."""
        search_filters = PropertySearchFilters(
            min_price=Decimal("5000.00"),
            max_price=Decimal("1000.00"),  # Max less than min
            page=1,
            page_size=10
        )
        
        with pytest.raises(ValidationError, match="Minimum price cannot be greater than maximum"):
            await property_service.search_properties(search_filters)
    
    @pytest.mark.asyncio
    async def test_search_properties_agent_filter_unauthorized(self, property_service: PropertyService, test_agent: User):
        """Test searching with agent filter as non-admin."""
        search_filters = PropertySearchFilters(
            agent_id=str(test_agent.id),  # Non-admin trying to filter by agent
            page=1,
            page_size=10
        )
        
        with pytest.raises(ForbiddenError, match="Only administrators can filter by agent"):
            await property_service.search_properties(search_filters, test_agent)
    
    @pytest.mark.asyncio
    async def test_get_user_properties_own(self, property_service: PropertyService, test_agent: User, test_property: Property):
        """Test getting own properties."""
        properties, total_count = await property_service.get_user_properties(
            test_agent.id, test_agent
        )
        
        assert len(properties) >= 1
        assert total_count >= 1
        assert all(prop.agent_id == test_agent.id for prop in properties)
    
    @pytest.mark.asyncio
    async def test_get_user_properties_as_admin(self, property_service: PropertyService, test_admin: User, test_agent: User):
        """Test admin getting another user's properties."""
        properties, total_count = await property_service.get_user_properties(
            test_agent.id, test_admin
        )
        
        assert isinstance(properties, list)
        assert isinstance(total_count, int)
    
    @pytest.mark.asyncio
    async def test_get_user_properties_unauthorized(self, property_service: PropertyService, test_agent: User, user_repository):
        """Test getting another user's properties without permission."""
        # Create another agent
        other_agent = await UserFactory.create_user(
            user_repository,
            email="other@example.com",
            role=UserRole.AGENT
        )
        
        with pytest.raises(InsufficientPermissionsError):
            await property_service.get_user_properties(test_agent.id, other_agent)
    
    @pytest.mark.asyncio
    async def test_get_nearby_properties_valid(self, property_service: PropertyService):
        """Test getting nearby properties with valid coordinates."""
        properties = await property_service.get_nearby_properties(
            latitude=25.2048,
            longitude=55.2708,
            radius_km=10.0
        )
        
        assert isinstance(properties, list)
    
    @pytest.mark.asyncio
    async def test_get_nearby_properties_invalid_coordinates(self, property_service: PropertyService):
        """Test getting nearby properties with invalid coordinates."""
        with pytest.raises(ValidationError, match="Latitude must be between"):
            await property_service.get_nearby_properties(
                latitude=91.0,  # Invalid latitude
                longitude=55.2708
            )
        
        with pytest.raises(ValidationError, match="Longitude must be between"):
            await property_service.get_nearby_properties(
                latitude=25.2048,
                longitude=181.0  # Invalid longitude
            )
    
    @pytest.mark.asyncio
    async def test_get_nearby_properties_invalid_radius(self, property_service: PropertyService):
        """Test getting nearby properties with invalid radius."""
        with pytest.raises(ValidationError, match="Radius must be between"):
            await property_service.get_nearby_properties(
                latitude=25.2048,
                longitude=55.2708,
                radius_km=150.0  # Too large
            )
    
    @pytest.mark.asyncio
    async def test_toggle_property_status(self, property_service: PropertyService, test_property: Property, test_agent: User):
        """Test toggling property status."""
        original_status = test_property.is_active
        
        updated_property = await property_service.toggle_property_status(
            test_property.id, test_agent
        )
        
        assert updated_property.is_active != original_status
    
    @pytest.mark.asyncio
    async def test_toggle_property_status_unauthorized(self, property_service: PropertyService, test_property: Property, user_repository):
        """Test toggling property status without permission."""
        # Create another agent
        other_agent = await UserFactory.create_user(
            user_repository,
            email="other@example.com",
            role=UserRole.AGENT
        )
        
        with pytest.raises(InsufficientPermissionsError):
            await property_service.toggle_property_status(test_property.id, other_agent)
    
    @pytest.mark.asyncio
    async def test_get_property_statistics_own(self, property_service: PropertyService, test_agent: User):
        """Test getting own property statistics."""
        stats = await property_service.get_property_statistics(test_agent)
        
        assert "total_properties" in stats
        assert "active_properties" in stats
        assert "properties_by_type" in stats
        assert isinstance(stats["total_properties"], int)
    
    @pytest.mark.asyncio
    async def test_get_property_statistics_as_admin(self, property_service: PropertyService, test_admin: User, test_agent: User):
        """Test admin getting specific agent's statistics."""
        stats = await property_service.get_property_statistics(
            test_admin, agent_id=test_agent.id
        )
        
        assert "total_properties" in stats
        assert isinstance(stats["total_properties"], int)
    
    @pytest.mark.asyncio
    async def test_get_property_statistics_unauthorized(self, property_service: PropertyService, test_agent: User, user_repository):
        """Test getting another agent's statistics without permission."""
        # Create another agent
        other_agent = await UserFactory.create_user(
            user_repository,
            email="other@example.com",
            role=UserRole.AGENT
        )
        
        with pytest.raises(InsufficientPermissionsError):
            await property_service.get_property_statistics(
                test_agent, agent_id=other_agent.id
            )
    
    @pytest.mark.asyncio
    async def test_get_featured_properties(self, property_service: PropertyService):
        """Test getting featured properties."""
        properties = await property_service.get_featured_properties(limit=5)
        
        assert isinstance(properties, list)
        assert len(properties) <= 5
    
    @pytest.mark.asyncio
    async def test_get_featured_properties_invalid_limit(self, property_service: PropertyService):
        """Test getting featured properties with invalid limit."""
        with pytest.raises(ValidationError, match="Limit must be between 1 and 100"):
            await property_service.get_featured_properties(limit=0)
        
        with pytest.raises(ValidationError, match="Limit must be between 1 and 100"):
            await property_service.get_featured_properties(limit=150)