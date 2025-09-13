"""
Comprehensive tests for repository classes.
Tests CRUD operations, filtering, pagination, and database interactions.
"""

import pytest
import uuid
from decimal import Decimal
from typing import List

from app.models.user import User, UserRole
from app.models.property import Property, PropertyType
from app.models.image import PropertyImage
from app.repositories.user import UserRepository
from app.repositories.property import PropertyRepository, PropertySearchFilters
from app.repositories.image import ImageRepository
from tests.conftest import UserFactory, PropertyFactory, ImageFactory, assert_user_equal, assert_property_equal


class TestBaseRepository:
    """Test base repository functionality through UserRepository."""
    
    @pytest.mark.asyncio
    async def test_create(self, user_repository: UserRepository):
        """Test creating a record."""
        user_data = UserFactory.create_user_data(email="test@example.com")
        user = await user_repository.create_user(user_data)
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.created_at is not None
        assert user.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, user_repository: UserRepository):
        """Test getting a record by ID."""
        # Create user
        user_data = UserFactory.create_user_data()
        created_user = await user_repository.create_user(user_data)
        
        # Get by ID
        retrieved_user = await user_repository.get_by_id(created_user.id)
        
        assert retrieved_user is not None
        assert_user_equal(retrieved_user, created_user)
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, user_repository: UserRepository):
        """Test getting a non-existent record."""
        non_existent_id = uuid.uuid4()
        user = await user_repository.get_by_id(non_existent_id)
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_update(self, user_repository: UserRepository):
        """Test updating a record."""
        # Create user
        user_data = UserFactory.create_user_data()
        created_user = await user_repository.create_user(user_data)
        
        # Update user
        update_data = {"full_name": "Updated Name"}
        updated_user = await user_repository.update(created_user.id, update_data)
        
        assert updated_user is not None
        assert updated_user.full_name == "Updated Name"
        assert updated_user.id == created_user.id
    
    @pytest.mark.asyncio
    async def test_update_not_found(self, user_repository: UserRepository):
        """Test updating a non-existent record."""
        non_existent_id = uuid.uuid4()
        update_data = {"full_name": "Updated Name"}
        
        updated_user = await user_repository.update(non_existent_id, update_data)
        assert updated_user is None
    
    @pytest.mark.asyncio
    async def test_delete(self, user_repository: UserRepository):
        """Test deleting a record."""
        # Create user
        user_data = UserFactory.create_user_data()
        created_user = await user_repository.create_user(user_data)
        
        # Delete user
        deleted = await user_repository.delete(created_user.id)
        assert deleted is True
        
        # Verify deletion
        retrieved_user = await user_repository.get_by_id(created_user.id)
        assert retrieved_user is None
    
    @pytest.mark.asyncio
    async def test_delete_not_found(self, user_repository: UserRepository):
        """Test deleting a non-existent record."""
        non_existent_id = uuid.uuid4()
        deleted = await user_repository.delete(non_existent_id)
        
        assert deleted is False
    
    @pytest.mark.asyncio
    async def test_count(self, user_repository: UserRepository):
        """Test counting records."""
        # Initial count
        initial_count = await user_repository.count()
        
        # Create users
        for i in range(3):
            user_data = UserFactory.create_user_data(email=f"test{i}@example.com")
            await user_repository.create_user(user_data)
        
        # Check count
        final_count = await user_repository.count()
        assert final_count == initial_count + 3
    
    @pytest.mark.asyncio
    async def test_count_with_filters(self, user_repository: UserRepository):
        """Test counting records with filters."""
        # Create users with different roles
        agent_data = UserFactory.create_user_data(email="agent@example.com", role=UserRole.AGENT)
        admin_data = UserFactory.create_user_data(email="admin@example.com", role=UserRole.ADMIN)
        
        await user_repository.create_user(agent_data)
        await user_repository.create_user(admin_data)
        
        # Count agents
        agent_count = await user_repository.count({"role": UserRole.AGENT})
        assert agent_count >= 1
        
        # Count admins
        admin_count = await user_repository.count({"role": UserRole.ADMIN})
        assert admin_count >= 1
    
    @pytest.mark.asyncio
    async def test_exists(self, user_repository: UserRepository):
        """Test checking if record exists."""
        # Create user
        user_data = UserFactory.create_user_data()
        created_user = await user_repository.create_user(user_data)
        
        # Check existence
        exists = await user_repository.exists(created_user.id)
        assert exists is True
        
        # Check non-existent
        non_existent_id = uuid.uuid4()
        exists = await user_repository.exists(non_existent_id)
        assert exists is False
    
    @pytest.mark.asyncio
    async def test_get_multi(self, user_repository: UserRepository):
        """Test getting multiple records."""
        # Create users
        users = []
        for i in range(5):
            user_data = UserFactory.create_user_data(email=f"test{i}@example.com")
            user = await user_repository.create_user(user_data)
            users.append(user)
        
        # Get multiple with pagination
        retrieved_users = await user_repository.get_multi(skip=1, limit=3)
        
        assert len(retrieved_users) <= 3
        assert len(retrieved_users) >= 1  # At least some users should exist
    
    @pytest.mark.asyncio
    async def test_get_by_field(self, user_repository: UserRepository):
        """Test getting record by field."""
        # Create user
        user_data = UserFactory.create_user_data(email="unique@example.com")
        created_user = await user_repository.create_user(user_data)
        
        # Get by email
        retrieved_user = await user_repository.get_by_field("email", "unique@example.com")
        
        assert retrieved_user is not None
        assert_user_equal(retrieved_user, created_user)
    
    @pytest.mark.asyncio
    async def test_bulk_create(self, user_repository: UserRepository):
        """Test bulk creating records."""
        users_data = [
            UserFactory.create_user_data(email=f"bulk{i}@example.com")
            for i in range(3)
        ]
        
        # Remove password field and add hashed_password for bulk create
        for user_data in users_data:
            password = user_data.pop("password")
            user_data["hashed_password"] = User.hash_password(password)
        
        created_users = await user_repository.bulk_create(users_data)
        
        assert len(created_users) == 3
        for user in created_users:
            assert user.id is not None
            assert user.email.startswith("bulk")


class TestUserRepository:
    """Test UserRepository specific functionality."""
    
    @pytest.mark.asyncio
    async def test_create_user(self, user_repository: UserRepository):
        """Test creating a user with validation."""
        user_data = UserFactory.create_user_data(
            email="test@example.com",
            password="testpassword123",
            full_name="Test User",
            role=UserRole.AGENT
        )
        
        user = await user_repository.create_user(user_data)
        
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.role == UserRole.AGENT
        assert user.verify_password("testpassword123")
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, user_repository: UserRepository):
        """Test creating user with duplicate email."""
        email = "duplicate@example.com"
        
        # Create first user
        user_data1 = UserFactory.create_user_data(email=email)
        await user_repository.create_user(user_data1)
        
        # Try to create second user with same email
        user_data2 = UserFactory.create_user_data(email=email)
        
        with pytest.raises(ValueError, match="already exists"):
            await user_repository.create_user(user_data2)
    
    @pytest.mark.asyncio
    async def test_get_by_email(self, user_repository: UserRepository):
        """Test getting user by email."""
        email = "test@example.com"
        user_data = UserFactory.create_user_data(email=email)
        created_user = await user_repository.create_user(user_data)
        
        # Get by email
        retrieved_user = await user_repository.get_by_email(email)
        
        assert retrieved_user is not None
        assert_user_equal(retrieved_user, created_user)
    
    @pytest.mark.asyncio
    async def test_get_by_email_case_insensitive(self, user_repository: UserRepository):
        """Test getting user by email is case insensitive."""
        email = "Test@Example.Com"
        user_data = UserFactory.create_user_data(email=email)
        created_user = await user_repository.create_user(user_data)
        
        # Get by different case
        retrieved_user = await user_repository.get_by_email("test@example.com")
        
        assert retrieved_user is not None
        assert_user_equal(retrieved_user, created_user)
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, user_repository: UserRepository):
        """Test successful user authentication."""
        email = "auth@example.com"
        password = "testpassword123"
        
        user_data = UserFactory.create_user_data(email=email, password=password)
        await user_repository.create_user(user_data)
        
        # Authenticate
        authenticated_user = await user_repository.authenticate_user(email, password)
        
        assert authenticated_user is not None
        assert authenticated_user.email == email
    
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, user_repository: UserRepository):
        """Test authentication with wrong password."""
        email = "auth@example.com"
        password = "testpassword123"
        
        user_data = UserFactory.create_user_data(email=email, password=password)
        await user_repository.create_user(user_data)
        
        # Try wrong password
        authenticated_user = await user_repository.authenticate_user(email, "wrongpassword")
        
        assert authenticated_user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, user_repository: UserRepository):
        """Test authentication with non-existent user."""
        authenticated_user = await user_repository.authenticate_user(
            "nonexistent@example.com", "password"
        )
        
        assert authenticated_user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_inactive_user(self, user_repository: UserRepository):
        """Test authentication with inactive user."""
        email = "inactive@example.com"
        password = "testpassword123"
        
        user_data = UserFactory.create_user_data(
            email=email, password=password, is_active=False
        )
        await user_repository.create_user(user_data)
        
        # Try to authenticate inactive user
        authenticated_user = await user_repository.authenticate_user(email, password)
        
        assert authenticated_user is None
    
    @pytest.mark.asyncio
    async def test_update_password(self, user_repository: UserRepository):
        """Test updating user password."""
        user_data = UserFactory.create_user_data(password="oldpassword123")
        created_user = await user_repository.create_user(user_data)
        
        # Update password
        new_password = "newpassword123"
        updated_user = await user_repository.update_password(created_user.id, new_password)
        
        assert updated_user is not None
        assert updated_user.verify_password(new_password)
        assert not updated_user.verify_password("oldpassword123")
    
    @pytest.mark.asyncio
    async def test_update_user_status(self, user_repository: UserRepository):
        """Test updating user status."""
        user_data = UserFactory.create_user_data(is_active=True)
        created_user = await user_repository.create_user(user_data)
        
        # Deactivate user
        updated_user = await user_repository.update_user_status(created_user.id, False)
        
        assert updated_user is not None
        assert updated_user.is_active is False
    
    @pytest.mark.asyncio
    async def test_update_user_role(self, user_repository: UserRepository):
        """Test updating user role."""
        user_data = UserFactory.create_user_data(role=UserRole.AGENT)
        created_user = await user_repository.create_user(user_data)
        
        # Update to admin
        updated_user = await user_repository.update_user_role(created_user.id, UserRole.ADMIN)
        
        assert updated_user is not None
        assert updated_user.role == UserRole.ADMIN
    
    @pytest.mark.asyncio
    async def test_get_users_by_role(self, user_repository: UserRepository):
        """Test getting users by role."""
        # Create users with different roles
        agent_data = UserFactory.create_user_data(email="agent@example.com", role=UserRole.AGENT)
        admin_data = UserFactory.create_user_data(email="admin@example.com", role=UserRole.ADMIN)
        
        await user_repository.create_user(agent_data)
        await user_repository.create_user(admin_data)
        
        # Get agents
        agents, agent_count = await user_repository.get_users_by_role(UserRole.AGENT)
        
        assert len(agents) >= 1
        assert agent_count >= 1
        for user in agents:
            assert user.role == UserRole.AGENT
    
    @pytest.mark.asyncio
    async def test_get_active_agents(self, user_repository: UserRepository):
        """Test getting active agents."""
        # Create active and inactive agents
        active_agent_data = UserFactory.create_user_data(
            email="active@example.com", role=UserRole.AGENT, is_active=True
        )
        inactive_agent_data = UserFactory.create_user_data(
            email="inactive@example.com", role=UserRole.AGENT, is_active=False
        )
        
        await user_repository.create_user(active_agent_data)
        await user_repository.create_user(inactive_agent_data)
        
        # Get active agents
        active_agents = await user_repository.get_active_agents()
        
        assert len(active_agents) >= 1
        for agent in active_agents:
            assert agent.role == UserRole.AGENT
            assert agent.is_active is True
    
    @pytest.mark.asyncio
    async def test_check_email_availability(self, user_repository: UserRepository):
        """Test checking email availability."""
        email = "taken@example.com"
        
        # Email should be available initially
        is_available = await user_repository.check_email_availability(email)
        assert is_available is True
        
        # Create user with email
        user_data = UserFactory.create_user_data(email=email)
        created_user = await user_repository.create_user(user_data)
        
        # Email should not be available now
        is_available = await user_repository.check_email_availability(email)
        assert is_available is False
        
        # But should be available when excluding the user
        is_available = await user_repository.check_email_availability(
            email, exclude_user_id=created_user.id
        )
        assert is_available is True


class TestPropertyRepository:
    """Test PropertyRepository specific functionality."""
    
    @pytest.mark.asyncio
    async def test_create_property(self, property_repository: PropertyRepository, test_agent: User):
        """Test creating a property with validation."""
        property_data = PropertyFactory.create_property_data(
            title="Test Property",
            price=Decimal("1500.00"),
            bedrooms=3,
            agent_id=test_agent.id
        )
        
        property_obj = await property_repository.create_property(property_data)
        
        assert property_obj.title == "Test Property"
        assert property_obj.price == Decimal("1500.00")
        assert property_obj.bedrooms == 3
        assert property_obj.agent_id == test_agent.id
    
    @pytest.mark.asyncio
    async def test_create_property_invalid_data(self, property_repository: PropertyRepository, test_agent: User):
        """Test creating property with invalid data."""
        property_data = PropertyFactory.create_property_data(
            title="Test Property",
            price=Decimal("-100.00"),  # Invalid negative price
            agent_id=test_agent.id
        )
        
        with pytest.raises(ValueError):
            await property_repository.create_property(property_data)
    
    @pytest.mark.asyncio
    async def test_get_property_with_details(self, property_repository: PropertyRepository, test_property: Property):
        """Test getting property with related data."""
        property_obj = await property_repository.get_property_with_details(test_property.id)
        
        assert property_obj is not None
        assert property_obj.id == test_property.id
        assert property_obj.agent is not None  # Should load agent relationship
    
    @pytest.mark.asyncio
    async def test_search_properties_basic(self, property_repository: PropertyRepository, test_property: Property):
        """Test basic property search."""
        filters = PropertySearchFilters(is_active=True)
        
        properties, total_count = await property_repository.search_properties(
            filters=filters,
            skip=0,
            limit=10
        )
        
        assert len(properties) >= 1
        assert total_count >= 1
        assert all(prop.is_active for prop in properties)
    
    @pytest.mark.asyncio
    async def test_search_properties_by_location(self, property_repository: PropertyRepository, test_agent: User):
        """Test searching properties by location."""
        # Create properties in different locations
        prop1_data = PropertyFactory.create_property_data(
            title="Property in Dubai",
            location="Dubai Marina",
            agent_id=test_agent.id
        )
        prop2_data = PropertyFactory.create_property_data(
            title="Property in Abu Dhabi",
            location="Abu Dhabi Downtown",
            agent_id=test_agent.id
        )
        
        await property_repository.create_property(prop1_data)
        await property_repository.create_property(prop2_data)
        
        # Search by location
        filters = PropertySearchFilters(location="Dubai")
        properties, total_count = await property_repository.search_properties(
            filters=filters,
            skip=0,
            limit=10
        )
        
        assert len(properties) >= 1
        assert all("Dubai" in prop.location for prop in properties)
    
    @pytest.mark.asyncio
    async def test_search_properties_by_price_range(self, property_repository: PropertyRepository, test_agent: User):
        """Test searching properties by price range."""
        # Create properties with different prices
        prop1_data = PropertyFactory.create_property_data(
            title="Cheap Property",
            price=Decimal("500.00"),
            agent_id=test_agent.id
        )
        prop2_data = PropertyFactory.create_property_data(
            title="Expensive Property",
            price=Decimal("5000.00"),
            agent_id=test_agent.id
        )
        
        await property_repository.create_property(prop1_data)
        await property_repository.create_property(prop2_data)
        
        # Search by price range
        filters = PropertySearchFilters(
            min_price=Decimal("1000.00"),
            max_price=Decimal("6000.00")
        )
        properties, total_count = await property_repository.search_properties(
            filters=filters,
            skip=0,
            limit=10
        )
        
        assert len(properties) >= 1
        for prop in properties:
            assert Decimal("1000.00") <= prop.price <= Decimal("6000.00")
    
    @pytest.mark.asyncio
    async def test_search_properties_by_bedrooms(self, property_repository: PropertyRepository, test_agent: User):
        """Test searching properties by bedrooms."""
        # Create properties with different bedroom counts
        prop1_data = PropertyFactory.create_property_data(
            title="Studio",
            bedrooms=0,
            agent_id=test_agent.id
        )
        prop2_data = PropertyFactory.create_property_data(
            title="3BR Apartment",
            bedrooms=3,
            agent_id=test_agent.id
        )
        
        await property_repository.create_property(prop1_data)
        await property_repository.create_property(prop2_data)
        
        # Search by bedrooms
        filters = PropertySearchFilters(bedrooms=3)
        properties, total_count = await property_repository.search_properties(
            filters=filters,
            skip=0,
            limit=10
        )
        
        assert len(properties) >= 1
        assert all(prop.bedrooms == 3 for prop in properties)
    
    @pytest.mark.asyncio
    async def test_search_properties_by_agent(self, property_repository: PropertyRepository, test_agent: User, test_admin: User):
        """Test searching properties by agent."""
        # Create properties for different agents
        prop1_data = PropertyFactory.create_property_data(
            title="Agent Property",
            agent_id=test_agent.id
        )
        prop2_data = PropertyFactory.create_property_data(
            title="Admin Property",
            agent_id=test_admin.id
        )
        
        await property_repository.create_property(prop1_data)
        await property_repository.create_property(prop2_data)
        
        # Search by agent
        filters = PropertySearchFilters(agent_id=test_agent.id)
        properties, total_count = await property_repository.search_properties(
            filters=filters,
            skip=0,
            limit=10
        )
        
        assert len(properties) >= 1
        assert all(prop.agent_id == test_agent.id for prop in properties)
    
    @pytest.mark.asyncio
    async def test_get_properties_by_agent(self, property_repository: PropertyRepository, test_agent: User):
        """Test getting properties by agent."""
        # Create properties for agent
        for i in range(3):
            prop_data = PropertyFactory.create_property_data(
                title=f"Agent Property {i}",
                agent_id=test_agent.id
            )
            await property_repository.create_property(prop_data)
        
        # Get agent's properties
        properties, total_count = await property_repository.get_properties_by_agent(
            agent_id=test_agent.id,
            skip=0,
            limit=10
        )
        
        assert len(properties) >= 3
        assert total_count >= 3
        assert all(prop.agent_id == test_agent.id for prop in properties)
    
    @pytest.mark.asyncio
    async def test_get_nearby_properties(self, property_repository: PropertyRepository, test_agent: User):
        """Test getting nearby properties."""
        # Create properties with coordinates
        prop1_data = PropertyFactory.create_property_data(
            title="Nearby Property 1",
            latitude=Decimal("25.2048"),
            longitude=Decimal("55.2708"),
            agent_id=test_agent.id
        )
        prop2_data = PropertyFactory.create_property_data(
            title="Nearby Property 2",
            latitude=Decimal("25.2050"),  # Very close
            longitude=Decimal("55.2710"),
            agent_id=test_agent.id
        )
        prop3_data = PropertyFactory.create_property_data(
            title="Far Property",
            latitude=Decimal("26.0000"),  # Far away
            longitude=Decimal("56.0000"),
            agent_id=test_agent.id
        )
        
        await property_repository.create_property(prop1_data)
        await property_repository.create_property(prop2_data)
        await property_repository.create_property(prop3_data)
        
        # Search nearby
        nearby_properties = await property_repository.get_nearby_properties(
            latitude=Decimal("25.2048"),
            longitude=Decimal("55.2708"),
            radius_km=1.0,  # 1km radius
            limit=10
        )
        
        # Should find the nearby properties but not the far one
        assert len(nearby_properties) >= 2
        nearby_titles = [prop.title for prop in nearby_properties]
        assert "Nearby Property 1" in nearby_titles
        assert "Nearby Property 2" in nearby_titles
        assert "Far Property" not in nearby_titles
    
    @pytest.mark.asyncio
    async def test_update_property_status(self, property_repository: PropertyRepository, test_property: Property):
        """Test updating property status."""
        # Deactivate property
        updated_property = await property_repository.update_property_status(
            test_property.id, False
        )
        
        assert updated_property is not None
        assert updated_property.is_active is False
        
        # Reactivate property
        updated_property = await property_repository.update_property_status(
            test_property.id, True
        )
        
        assert updated_property is not None
        assert updated_property.is_active is True
    
    @pytest.mark.asyncio
    async def test_get_property_statistics(self, property_repository: PropertyRepository, test_agent: User):
        """Test getting property statistics."""
        # Create properties with different types and prices
        rental_data = PropertyFactory.create_property_data(
            title="Rental Property",
            property_type=PropertyType.RENTAL,
            price=Decimal("2000.00"),
            agent_id=test_agent.id
        )
        sale_data = PropertyFactory.create_property_data(
            title="Sale Property",
            property_type=PropertyType.SALE,
            price=Decimal("500000.00"),
            agent_id=test_agent.id
        )
        
        await property_repository.create_property(rental_data)
        await property_repository.create_property(sale_data)
        
        # Get statistics for agent
        stats = await property_repository.get_property_statistics(agent_id=test_agent.id)
        
        assert "total_properties" in stats
        assert "active_properties" in stats
        assert "properties_by_type" in stats
        assert "average_prices_by_type" in stats
        assert "price_statistics" in stats
        
        assert stats["total_properties"] >= 2
        assert stats["active_properties"] >= 2


class TestImageRepository:
    """Test ImageRepository specific functionality."""
    
    @pytest.mark.asyncio
    async def test_create_image(self, image_repository: ImageRepository, test_property: Property):
        """Test creating a property image."""
        image_data = ImageFactory.create_image_data(
            property_id=test_property.id,
            filename="test.jpg",
            file_size=1024000
        )
        
        image = await image_repository.create(image_data)
        
        assert image.property_id == test_property.id
        assert image.filename == "test.jpg"
        assert image.file_size == 1024000
    
    @pytest.mark.asyncio
    async def test_get_images_by_property(self, image_repository: ImageRepository, test_property: Property):
        """Test getting images by property."""
        # Create multiple images for property
        for i in range(3):
            image_data = ImageFactory.create_image_data(
                property_id=test_property.id,
                filename=f"test{i}.jpg",
                display_order=i
            )
            await image_repository.create(image_data)
        
        # Get images by property
        images = await image_repository.get_multi(
            filters={"property_id": test_property.id}
        )
        
        assert len(images) >= 3
        assert all(img.property_id == test_property.id for img in images)
    
    @pytest.mark.asyncio
    async def test_set_primary_image(self, image_repository: ImageRepository, test_property: Property):
        """Test setting primary image."""
        # Create multiple images
        images = []
        for i in range(3):
            image_data = ImageFactory.create_image_data(
                property_id=test_property.id,
                filename=f"test{i}.jpg",
                is_primary=(i == 0)  # First image is primary
            )
            image = await image_repository.create(image_data)
            images.append(image)
        
        # Change primary image
        await image_repository.update(images[1].id, {"is_primary": True})
        await image_repository.update(images[0].id, {"is_primary": False})
        
        # Verify primary image changed
        updated_image = await image_repository.get_by_id(images[1].id)
        assert updated_image.is_primary is True
        
        old_primary = await image_repository.get_by_id(images[0].id)
        assert old_primary.is_primary is False