"""
Integration tests for all API endpoints.
Tests complete request/response cycles with Docker test environment.
"""

import pytest
import uuid
import io
import json
from decimal import Decimal
from typing import Dict, Any
from httpx import AsyncClient
from fastapi import status
from PIL import Image as PILImage

from app.models.user import User, UserRole
from app.models.property import Property, PropertyType
from app.models.image import PropertyImage
from tests.conftest import UserFactory, PropertyFactory, ImageFactory


class TestAuthenticationEndpoints:
    """Integration tests for authentication endpoints."""
    
    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient, test_agent: User):
        """Test successful login flow."""
        login_data = {
            "email": test_agent.email,
            "password": "testpassword123"
        }
        
        response = await async_client.post("/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == test_agent.email
        assert data["user"]["role"] == test_agent.role.value
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, async_client: AsyncClient, test_agent: User):
        """Test login with invalid credentials."""
        login_data = {
            "email": test_agent.email,
            "password": "wrongpassword"
        }
        
        response = await async_client.post("/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """Test login with non-existent user."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "password123"
        }
        
        response = await async_client.post("/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_login_inactive_user(self, async_client: AsyncClient, test_inactive_user: User):
        """Test login with inactive user."""
        login_data = {
            "email": test_inactive_user.email,
            "password": "testpassword123"
        }
        
        response = await async_client.post("/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_get_current_user_success(self, async_client: AsyncClient, test_agent: User):
        """Test getting current user info with valid token."""
        # Login first to get token
        login_data = {
            "email": test_agent.email,
            "password": "testpassword123"
        }
        login_response = await async_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Get current user
        headers = {"Authorization": f"Bearer {token}"}
        response = await async_client.get("/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["id"] == str(test_agent.id)
        assert data["email"] == test_agent.email
        assert data["role"] == test_agent.role.value
        assert data["is_active"] == test_agent.is_active
    
    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, async_client: AsyncClient):
        """Test getting current user without token."""
        response = await async_client.get("/auth/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, async_client: AsyncClient):
        """Test getting current user with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = await async_client.get("/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, async_client: AsyncClient, test_agent: User):
        """Test successful token refresh."""
        # Login first to get refresh token
        login_data = {
            "email": test_agent.email,
            "password": "testpassword123"
        }
        login_response = await async_client.post("/auth/login", json=login_data)
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh token
        refresh_data = {"refresh_token": refresh_token}
        response = await async_client.post("/auth/refresh", json=refresh_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, async_client: AsyncClient):
        """Test token refresh with invalid refresh token."""
        refresh_data = {"refresh_token": "invalid_refresh_token"}
        response = await async_client.post("/auth/refresh", json=refresh_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_validate_token_success(self, async_client: AsyncClient, test_agent: User):
        """Test successful token validation."""
        # Login first to get token
        login_data = {
            "email": test_agent.email,
            "password": "testpassword123"
        }
        login_response = await async_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Validate token
        headers = {"Authorization": f"Bearer {token}"}
        response = await async_client.post("/auth/validate", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["valid"] is True
        assert data["user_id"] == str(test_agent.id)
        assert data["email"] == test_agent.email
        assert data["role"] == test_agent.role.value
    
    @pytest.mark.asyncio
    async def test_validate_token_invalid(self, async_client: AsyncClient):
        """Test token validation with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = await async_client.post("/auth/validate", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["valid"] is False
    
    @pytest.mark.asyncio
    async def test_logout_success(self, async_client: AsyncClient, test_agent: User):
        """Test successful logout."""
        # Login first to get token
        login_data = {
            "email": test_agent.email,
            "password": "testpassword123"
        }
        login_response = await async_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Logout
        headers = {"Authorization": f"Bearer {token}"}
        response = await async_client.post("/auth/logout", headers=headers)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestPropertyManagementEndpoints:
    """Integration tests for property management endpoints."""
    
    async def get_auth_headers(self, async_client: AsyncClient, user: User) -> Dict[str, str]:
        """Helper method to get authentication headers."""
        login_data = {
            "email": user.email,
            "password": "testpassword123"
        }
        login_response = await async_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.mark.asyncio
    async def test_create_property_success(self, async_client: AsyncClient, test_agent: User):
        """Test successful property creation."""
        headers = await self.get_auth_headers(async_client, test_agent)
        
        property_data = {
            "title": "Integration Test Property",
            "description": "A property created during integration testing",
            "property_type": "rental",
            "price": 2500.00,
            "bedrooms": 3,
            "bathrooms": 2,
            "area_sqft": 1500,
            "location": "Integration Test City",
            "latitude": 25.2048,
            "longitude": 55.2708
        }
        
        response = await async_client.post("/properties", json=property_data, headers=headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert data["title"] == property_data["title"]
        assert data["description"] == property_data["description"]
        assert data["property_type"] == property_data["property_type"]
        assert float(data["price"]) == property_data["price"]
        assert data["bedrooms"] == property_data["bedrooms"]
        assert data["agent_id"] == str(test_agent.id)
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
    
    @pytest.mark.asyncio
    async def test_create_property_unauthorized(self, async_client: AsyncClient):
        """Test property creation without authentication."""
        property_data = {
            "title": "Unauthorized Property",
            "description": "This should fail",
            "property_type": "rental",
            "price": 1000.00,
            "bedrooms": 2,
            "bathrooms": 1,
            "area_sqft": 800,
            "location": "Test City"
        }
        
        response = await async_client.post("/properties", json=property_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_create_property_invalid_data(self, async_client: AsyncClient, test_agent: User):
        """Test property creation with invalid data."""
        headers = await self.get_auth_headers(async_client, test_agent)
        
        property_data = {
            "title": "",  # Empty title should fail
            "description": "Test description",
            "property_type": "rental",
            "price": -100.00,  # Negative price should fail
            "bedrooms": 0,
            "bathrooms": 0,
            "area_sqft": 0,
            "location": ""
        }
        
        response = await async_client.post("/properties", json=property_data, headers=headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_get_property_success(self, async_client: AsyncClient, test_property: Property):
        """Test getting property details."""
        response = await async_client.get(f"/properties/{test_property.id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["id"] == str(test_property.id)
        assert data["title"] == test_property.title
        assert data["description"] == test_property.description
        assert data["is_active"] == test_property.is_active
    
    @pytest.mark.asyncio
    async def test_get_property_not_found(self, async_client: AsyncClient):
        """Test getting non-existent property."""
        non_existent_id = uuid.uuid4()
        response = await async_client.get(f"/properties/{non_existent_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_get_inactive_property_anonymous(self, async_client: AsyncClient, test_inactive_property: Property):
        """Test getting inactive property without authentication."""
        response = await async_client.get(f"/properties/{test_inactive_property.id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_get_inactive_property_as_owner(self, async_client: AsyncClient, test_inactive_property: Property, test_agent: User):
        """Test getting inactive property as owner."""
        headers = await self.get_auth_headers(async_client, test_agent)
        
        response = await async_client.get(f"/properties/{test_inactive_property.id}", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] is False
    
    @pytest.mark.asyncio
    async def test_update_property_success(self, async_client: AsyncClient, test_property: Property, test_agent: User):
        """Test successful property update."""
        headers = await self.get_auth_headers(async_client, test_agent)
        
        update_data = {
            "title": "Updated Integration Test Property",
            "price": 3000.00,
            "bedrooms": 4
        }
        
        response = await async_client.put(f"/properties/{test_property.id}", json=update_data, headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["title"] == update_data["title"]
        assert float(data["price"]) == update_data["price"]
        assert data["bedrooms"] == update_data["bedrooms"]
        assert data["id"] == str(test_property.id)
    
    @pytest.mark.asyncio
    async def test_update_property_unauthorized(self, async_client: AsyncClient, test_property: Property):
        """Test property update without authentication."""
        update_data = {"title": "Unauthorized Update"}
        
        response = await async_client.put(f"/properties/{test_property.id}", json=update_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_update_property_forbidden(self, async_client: AsyncClient, test_property: Property, user_repository):
        """Test property update by non-owner."""
        # Create another agent
        other_agent = await UserFactory.create_user(
            user_repository,
            email="other_agent@test.com",
            role=UserRole.AGENT
        )
        
        headers = await self.get_auth_headers(async_client, other_agent)
        update_data = {"title": "Forbidden Update"}
        
        response = await async_client.put(f"/properties/{test_property.id}", json=update_data, headers=headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_update_property_as_admin(self, async_client: AsyncClient, test_property: Property, test_admin: User):
        """Test property update by admin."""
        headers = await self.get_auth_headers(async_client, test_admin)
        
        update_data = {"title": "Admin Updated Property"}
        
        response = await async_client.put(f"/properties/{test_property.id}", json=update_data, headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == update_data["title"]
    
    @pytest.mark.asyncio
    async def test_delete_property_success(self, async_client: AsyncClient, test_agent: User, property_repository):
        """Test successful property deletion."""
        # Create a property to delete
        property_to_delete = await PropertyFactory.create_property(
            property_repository,
            agent_id=test_agent.id,
            title="Property to Delete"
        )
        
        headers = await self.get_auth_headers(async_client, test_agent)
        
        response = await async_client.delete(f"/properties/{property_to_delete.id}", headers=headers)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify property is deleted
        get_response = await async_client.get(f"/properties/{property_to_delete.id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_delete_property_unauthorized(self, async_client: AsyncClient, test_property: Property):
        """Test property deletion without authentication."""
        response = await async_client.delete(f"/properties/{test_property.id}")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_delete_property_forbidden(self, async_client: AsyncClient, test_property: Property, user_repository):
        """Test property deletion by non-owner."""
        # Create another agent
        other_agent = await UserFactory.create_user(
            user_repository,
            email="other_agent2@test.com",
            role=UserRole.AGENT
        )
        
        headers = await self.get_auth_headers(async_client, other_agent)
        
        response = await async_client.delete(f"/properties/{test_property.id}", headers=headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_list_properties_basic(self, async_client: AsyncClient, test_property: Property):
        """Test basic property listing."""
        response = await async_client.get("/properties")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "properties" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert "has_next" in data
        assert "has_previous" in data
        
        assert data["total"] >= 1
        assert len(data["properties"]) >= 1
        assert any(prop["id"] == str(test_property.id) for prop in data["properties"])
    
    @pytest.mark.asyncio
    async def test_list_properties_with_pagination(self, async_client: AsyncClient, property_repository, test_agent: User):
        """Test property listing with pagination."""
        # Create multiple properties
        for i in range(5):
            await PropertyFactory.create_property(
                property_repository,
                agent_id=test_agent.id,
                title=f"Pagination Test Property {i}",
                price=Decimal(f"{1000 + i * 100}.00")
            )
        
        # Test first page
        response = await async_client.get("/properties?page=1&page_size=3")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["properties"]) <= 3
        assert data["page"] == 1
        assert data["page_size"] == 3
        assert data["total"] >= 5
        
        # Test second page
        response = await async_client.get("/properties?page=2&page_size=3")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["page"] == 2
        assert data["has_previous"] is True
    
    @pytest.mark.asyncio
    async def test_search_properties_by_location(self, async_client: AsyncClient, property_repository, test_agent: User):
        """Test property search by location."""
        # Create properties with specific locations
        await PropertyFactory.create_property(
            property_repository,
            agent_id=test_agent.id,
            title="Dubai Marina Property",
            location="Dubai Marina"
        )
        await PropertyFactory.create_property(
            property_repository,
            agent_id=test_agent.id,
            title="Abu Dhabi Property",
            location="Abu Dhabi Downtown"
        )
        
        # Search for Dubai properties
        response = await async_client.get("/properties?location=Dubai")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["total"] >= 1
        for prop in data["properties"]:
            assert "Dubai" in prop["location"]
    
    @pytest.mark.asyncio
    async def test_search_properties_by_price_range(self, async_client: AsyncClient, property_repository, test_agent: User):
        """Test property search by price range."""
        # Create properties with different prices
        await PropertyFactory.create_property(
            property_repository,
            agent_id=test_agent.id,
            title="Cheap Property",
            price=Decimal("500.00")
        )
        await PropertyFactory.create_property(
            property_repository,
            agent_id=test_agent.id,
            title="Expensive Property",
            price=Decimal("5000.00")
        )
        
        # Search for properties in mid-range
        response = await async_client.get("/properties?min_price=1000&max_price=3000")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        for prop in data["properties"]:
            price = float(prop["price"])
            assert 1000 <= price <= 3000
    
    @pytest.mark.asyncio
    async def test_search_properties_by_bedrooms(self, async_client: AsyncClient, property_repository, test_agent: User):
        """Test property search by bedrooms."""
        # Create properties with different bedroom counts
        await PropertyFactory.create_property(
            property_repository,
            agent_id=test_agent.id,
            title="Studio Apartment",
            bedrooms=0
        )
        await PropertyFactory.create_property(
            property_repository,
            agent_id=test_agent.id,
            title="Large House",
            bedrooms=5
        )
        
        # Search for properties with 3+ bedrooms
        response = await async_client.get("/properties?bedrooms=3")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        for prop in data["properties"]:
            assert prop["bedrooms"] >= 3
    
    @pytest.mark.asyncio
    async def test_search_properties_by_type(self, async_client: AsyncClient, property_repository, test_agent: User):
        """Test property search by type."""
        # Create properties of different types
        await PropertyFactory.create_property(
            property_repository,
            agent_id=test_agent.id,
            title="Rental Property",
            property_type=PropertyType.RENTAL
        )
        await PropertyFactory.create_property(
            property_repository,
            agent_id=test_agent.id,
            title="Sale Property",
            property_type=PropertyType.SALE
        )
        
        # Search for rental properties
        response = await async_client.get("/properties?property_type=rental")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        for prop in data["properties"]:
            assert prop["property_type"] == "rental"
    
    @pytest.mark.asyncio
    async def test_search_properties_combined_filters(self, async_client: AsyncClient, property_repository, test_agent: User):
        """Test property search with multiple filters."""
        # Create a specific property that matches all filters
        await PropertyFactory.create_property(
            property_repository,
            agent_id=test_agent.id,
            title="Perfect Match Property",
            location="Dubai Marina",
            price=Decimal("2500.00"),
            bedrooms=3,
            property_type=PropertyType.RENTAL
        )
        
        # Search with combined filters
        response = await async_client.get(
            "/properties?location=Dubai&min_price=2000&max_price=3000&bedrooms=3&property_type=rental"
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["total"] >= 1
        for prop in data["properties"]:
            assert "Dubai" in prop["location"]
            assert 2000 <= float(prop["price"]) <= 3000
            assert prop["bedrooms"] >= 3
            assert prop["property_type"] == "rental"
    
    @pytest.mark.asyncio
    async def test_search_properties_invalid_price_range(self, async_client: AsyncClient):
        """Test property search with invalid price range."""
        response = await async_client.get("/properties?min_price=5000&max_price=1000")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_get_nearby_properties(self, async_client: AsyncClient, property_repository, test_agent: User):
        """Test getting nearby properties."""
        # Create properties with coordinates
        await PropertyFactory.create_property(
            property_repository,
            agent_id=test_agent.id,
            title="Nearby Property",
            latitude=Decimal("25.2048"),
            longitude=Decimal("55.2708")
        )
        
        # Search for nearby properties
        response = await async_client.get("/properties/nearby/location?latitude=25.2048&longitude=55.2708&radius_km=10")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_nearby_properties_invalid_coordinates(self, async_client: AsyncClient):
        """Test getting nearby properties with invalid coordinates."""
        response = await async_client.get("/properties/nearby/location?latitude=91&longitude=55.2708")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_get_featured_properties(self, async_client: AsyncClient):
        """Test getting featured properties."""
        response = await async_client.get("/properties/featured/list")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_toggle_property_status(self, async_client: AsyncClient, test_property: Property, test_agent: User):
        """Test toggling property status."""
        headers = await self.get_auth_headers(async_client, test_agent)
        original_status = test_property.is_active
        
        response = await async_client.patch(f"/properties/{test_property.id}/status", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["is_active"] != original_status
    
    @pytest.mark.asyncio
    async def test_get_agent_properties(self, async_client: AsyncClient, test_agent: User, test_property: Property):
        """Test getting agent's properties."""
        headers = await self.get_auth_headers(async_client, test_agent)
        
        response = await async_client.get(f"/properties/agent/{test_agent.id}", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "properties" in data
        assert "total" in data
        assert data["total"] >= 1
        assert any(prop["id"] == str(test_property.id) for prop in data["properties"])
    
    @pytest.mark.asyncio
    async def test_get_property_statistics(self, async_client: AsyncClient, test_agent: User):
        """Test getting property statistics."""
        headers = await self.get_auth_headers(async_client, test_agent)
        
        response = await async_client.get("/properties/statistics/summary", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "total_properties" in data
        assert "active_properties" in data
        assert "properties_by_type" in data
        assert isinstance(data["total_properties"], int)


class TestImageManagementEndpoints:
    """Integration tests for image management endpoints."""
    
    async def get_auth_headers(self, async_client: AsyncClient, user: User) -> Dict[str, str]:
        """Helper method to get authentication headers."""
        login_data = {
            "email": user.email,
            "password": "testpassword123"
        }
        login_response = await async_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def create_test_image_file(self, filename: str = "test_image.jpg", size: tuple = (800, 600)) -> io.BytesIO:
        """Create a test image file in memory."""
        image = PILImage.new('RGB', size, color='red')
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='JPEG')
        image_bytes.seek(0)
        return image_bytes
    
    @pytest.mark.asyncio
    async def test_upload_property_image_success(self, async_client: AsyncClient, test_property: Property, test_agent: User):
        """Test successful property image upload."""
        headers = await self.get_auth_headers(async_client, test_agent)
        
        # Create test image file
        image_file = self.create_test_image_file()
        
        files = {"file": ("test_image.jpg", image_file, "image/jpeg")}
        data = {"is_primary": "true", "display_order": "0"}
        
        response = await async_client.post(
            f"/images/property/{test_property.id}/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        
        assert response_data["success"] is True
        assert "image" in response_data
        assert response_data["image"]["property_id"] == str(test_property.id)
        assert response_data["image"]["is_primary"] is True
    
    @pytest.mark.asyncio
    async def test_upload_property_image_unauthorized(self, async_client: AsyncClient, test_property: Property):
        """Test property image upload without authentication."""
        image_file = self.create_test_image_file()
        
        files = {"file": ("test_image.jpg", image_file, "image/jpeg")}
        data = {"is_primary": "false"}
        
        response = await async_client.post(
            f"/images/property/{test_property.id}/upload",
            files=files,
            data=data
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_upload_property_image_invalid_property(self, async_client: AsyncClient, test_agent: User):
        """Test image upload for non-existent property."""
        headers = await self.get_auth_headers(async_client, test_agent)
        non_existent_id = uuid.uuid4()
        
        image_file = self.create_test_image_file()
        
        files = {"file": ("test_image.jpg", image_file, "image/jpeg")}
        data = {"is_primary": "false"}
        
        response = await async_client.post(
            f"/images/property/{non_existent_id}/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    @pytest.mark.asyncio
    async def test_upload_multiple_property_images(self, async_client: AsyncClient, test_property: Property, test_agent: User):
        """Test uploading multiple property images."""
        headers = await self.get_auth_headers(async_client, test_agent)
        
        # Create multiple test image files
        image_files = [
            ("files", ("test_image1.jpg", self.create_test_image_file(), "image/jpeg")),
            ("files", ("test_image2.jpg", self.create_test_image_file(), "image/jpeg")),
            ("files", ("test_image3.jpg", self.create_test_image_file(), "image/jpeg"))
        ]
        
        response = await async_client.post(
            f"/images/property/{test_property.id}/upload-multiple",
            files=image_files,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        
        assert response_data["success"] is True
        assert response_data["uploaded_count"] == 3
        assert len(response_data["images"]) == 3
    
    @pytest.mark.asyncio
    async def test_get_property_images(self, async_client: AsyncClient, test_property: Property, test_property_image: PropertyImage):
        """Test getting all images for a property."""
        response = await async_client.get(f"/images/property/{test_property.id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "images" in data
        assert "total" in data
        assert data["total"] >= 1
        assert any(img["id"] == str(test_property_image.id) for img in data["images"])
    
    @pytest.mark.asyncio
    async def test_get_property_images_invalid_property(self, async_client: AsyncClient):
        """Test getting images for non-existent property."""
        non_existent_id = uuid.uuid4()
        response = await async_client.get(f"/images/property/{non_existent_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_get_image_details(self, async_client: AsyncClient, test_property_image: PropertyImage):
        """Test getting specific image details."""
        response = await async_client.get(f"/images/{test_property_image.id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["id"] == str(test_property_image.id)
        assert data["property_id"] == str(test_property_image.property_id)
        assert data["filename"] == test_property_image.filename
    
    @pytest.mark.asyncio
    async def test_get_image_details_not_found(self, async_client: AsyncClient):
        """Test getting details for non-existent image."""
        non_existent_id = uuid.uuid4()
        response = await async_client.get(f"/images/{non_existent_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_update_image_metadata(self, async_client: AsyncClient, test_property_image: PropertyImage, test_agent: User):
        """Test updating image metadata."""
        headers = await self.get_auth_headers(async_client, test_agent)
        
        update_data = {
            "is_primary": True,
            "display_order": 1
        }
        
        response = await async_client.put(
            f"/images/{test_property_image.id}",
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["is_primary"] is True
        assert data["display_order"] == 1
    
    @pytest.mark.asyncio
    async def test_set_primary_image(self, async_client: AsyncClient, test_property_image: PropertyImage, test_agent: User):
        """Test setting image as primary."""
        headers = await self.get_auth_headers(async_client, test_agent)
        
        response = await async_client.post(
            f"/images/{test_property_image.id}/set-primary",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["is_primary"] is True
    
    @pytest.mark.asyncio
    async def test_delete_image_success(self, async_client: AsyncClient, test_agent: User, image_repository, test_property: Property):
        """Test successful image deletion."""
        # Create an image to delete
        image_to_delete = await ImageFactory.create_image(
            image_repository,
            property_id=test_property.id,
            filename="delete_me.jpg"
        )
        
        headers = await self.get_auth_headers(async_client, test_agent)
        
        response = await async_client.delete(f"/images/{image_to_delete.id}", headers=headers)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify image is deleted
        get_response = await async_client.get(f"/images/{image_to_delete.id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_delete_image_unauthorized(self, async_client: AsyncClient, test_property_image: PropertyImage):
        """Test image deletion without authentication."""
        response = await async_client.delete(f"/images/{test_property_image.id}")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_delete_image_not_found(self, async_client: AsyncClient, test_agent: User):
        """Test deleting non-existent image."""
        headers = await self.get_auth_headers(async_client, test_agent)
        non_existent_id = uuid.uuid4()
        
        response = await async_client.delete(f"/images/{non_existent_id}", headers=headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestSearchAndFilteringEndpoints:
    """Integration tests for advanced search and filtering functionality."""
    
    @pytest.mark.asyncio
    async def test_advanced_search_endpoint(self, async_client: AsyncClient, property_repository, test_agent: User):
        """Test advanced search endpoint with complex filters."""
        # Create test properties with various attributes
        await PropertyFactory.create_property(
            property_repository,
            agent_id=test_agent.id,
            title="Luxury Dubai Villa",
            location="Dubai Hills",
            price=Decimal("8000.00"),
            bedrooms=5,
            bathrooms=4,
            area_sqft=3000,
            property_type=PropertyType.RENTAL
        )
        
        search_filters = {
            "query": "Luxury",
            "location": "Dubai",
            "min_price": 5000,
            "max_price": 10000,
            "bedrooms": 4,
            "bathrooms": 3,
            "min_area": 2000,
            "property_type": "rental",
            "page": 1,
            "page_size": 10,
            "sort_by": "price",
            "sort_order": "desc"
        }
        
        response = await async_client.post("/properties/search/advanced", json=search_filters)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "properties" in data
        assert "total" in data
        
        # Verify search results match filters
        for prop in data["properties"]:
            if search_filters["query"]:
                assert search_filters["query"].lower() in prop["title"].lower() or search_filters["query"].lower() in prop["description"].lower()
            if search_filters["location"]:
                assert search_filters["location"].lower() in prop["location"].lower()
            assert float(prop["price"]) >= search_filters["min_price"]
            assert float(prop["price"]) <= search_filters["max_price"]
            assert prop["bedrooms"] >= search_filters["bedrooms"]
            assert prop["bathrooms"] >= search_filters["bathrooms"]
            assert prop["area_sqft"] >= search_filters["min_area"]
            assert prop["property_type"] == search_filters["property_type"]
    
    @pytest.mark.asyncio
    async def test_search_with_sorting(self, async_client: AsyncClient, property_repository, test_agent: User):
        """Test search results sorting."""
        # Create properties with different prices
        prices = [1000, 3000, 2000, 4000, 1500]
        for i, price in enumerate(prices):
            await PropertyFactory.create_property(
                property_repository,
                agent_id=test_agent.id,
                title=f"Sort Test Property {i}",
                price=Decimal(f"{price}.00")
            )
        
        # Test ascending sort
        response = await async_client.get("/properties?sort_by=price&sort_order=asc&page_size=10")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        prices_in_response = [float(prop["price"]) for prop in data["properties"]]
        assert prices_in_response == sorted(prices_in_response)
        
        # Test descending sort
        response = await async_client.get("/properties?sort_by=price&sort_order=desc&page_size=10")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        prices_in_response = [float(prop["price"]) for prop in data["properties"]]
        assert prices_in_response == sorted(prices_in_response, reverse=True)
    
    @pytest.mark.asyncio
    async def test_search_with_text_query(self, async_client: AsyncClient, property_repository, test_agent: User):
        """Test text search in title and description."""
        # Create properties with specific keywords
        await PropertyFactory.create_property(
            property_repository,
            agent_id=test_agent.id,
            title="Modern Apartment with Sea View",
            description="Beautiful modern apartment overlooking the sea"
        )
        await PropertyFactory.create_property(
            property_repository,
            agent_id=test_agent.id,
            title="Traditional Villa",
            description="Classic villa with garden and pool"
        )
        
        # Search for "modern"
        response = await async_client.get("/properties?query=modern")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["total"] >= 1
        for prop in data["properties"]:
            assert "modern" in prop["title"].lower() or "modern" in prop["description"].lower()
    
    @pytest.mark.asyncio
    async def test_search_no_results(self, async_client: AsyncClient):
        """Test search with no matching results."""
        response = await async_client.get("/properties?query=nonexistentkeyword12345")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["total"] == 0
        assert len(data["properties"]) == 0
    
    @pytest.mark.asyncio
    async def test_search_with_invalid_sort_field(self, async_client: AsyncClient):
        """Test search with invalid sort field."""
        response = await async_client.get("/properties?sort_by=invalid_field")
        
        # Should either return 422 or default to valid sort field
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    @pytest.mark.asyncio
    async def test_pagination_edge_cases(self, async_client: AsyncClient):
        """Test pagination edge cases."""
        # Test page 0 (should default to 1 or return error)
        response = await async_client.get("/properties?page=0")
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]
        
        # Test negative page
        response = await async_client.get("/properties?page=-1")
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]
        
        # Test very large page size
        response = await async_client.get("/properties?page_size=1000")
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    @pytest.mark.asyncio
    async def test_filter_combinations(self, async_client: AsyncClient, property_repository, test_agent: User):
        """Test various filter combinations."""
        # Create diverse properties
        properties_data = [
            {"title": "Studio Downtown", "bedrooms": 0, "bathrooms": 1, "price": Decimal("800.00"), "location": "Downtown", "property_type": PropertyType.RENTAL},
            {"title": "Family House Suburbs", "bedrooms": 4, "bathrooms": 3, "price": Decimal("2500.00"), "location": "Suburbs", "property_type": PropertyType.RENTAL},
            {"title": "Luxury Penthouse", "bedrooms": 3, "bathrooms": 2, "price": Decimal("500000.00"), "location": "Marina", "property_type": PropertyType.SALE},
            {"title": "Office Space", "bedrooms": 0, "bathrooms": 2, "price": Decimal("3000.00"), "location": "Business District", "property_type": PropertyType.RENTAL}
        ]
        
        for prop_data in properties_data:
            await PropertyFactory.create_property(
                property_repository,
                agent_id=test_agent.id,
                **prop_data
            )
        
        # Test filter: rental properties with 2+ bedrooms under 3000
        response = await async_client.get("/properties?property_type=rental&bedrooms=2&max_price=3000")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        for prop in data["properties"]:
            assert prop["property_type"] == "rental"
            assert prop["bedrooms"] >= 2
            assert float(prop["price"]) <= 3000
        
        # Test filter: properties in Marina or Downtown
        response = await async_client.get("/properties?location=Marina")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        for prop in data["properties"]:
            assert "Marina" in prop["location"]


class TestDatabaseCleanupAndIsolation:
    """Tests for database cleanup and isolation in Docker environment."""
    
    @pytest.mark.asyncio
    async def test_test_isolation(self, async_client: AsyncClient, test_agent: User, property_repository):
        """Test that tests are properly isolated."""
        # Create a property in this test
        test_property = await PropertyFactory.create_property(
            property_repository,
            agent_id=test_agent.id,
            title="Isolation Test Property"
        )
        
        # Verify it exists
        response = await async_client.get(f"/properties/{test_property.id}")
        assert response.status_code == status.HTTP_200_OK
        
        # This property should not interfere with other tests
        # due to database session isolation
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, async_client: AsyncClient, test_agent: User):
        """Test concurrent API operations."""
        headers = {
            "Authorization": f"Bearer {await self.get_token(async_client, test_agent)}"
        }
        
        # Create multiple properties concurrently
        import asyncio
        
        async def create_property(index: int):
            property_data = {
                "title": f"Concurrent Property {index}",
                "description": f"Property created concurrently {index}",
                "property_type": "rental",
                "price": 1000.00 + index * 100,
                "bedrooms": 2,
                "bathrooms": 1,
                "area_sqft": 1000,
                "location": f"Test Location {index}"
            }
            return await async_client.post("/properties", json=property_data, headers=headers)
        
        # Create 5 properties concurrently
        tasks = [create_property(i) for i in range(5)]
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for response in responses:
            assert response.status_code == status.HTTP_201_CREATED
    
    async def get_token(self, async_client: AsyncClient, user: User) -> str:
        """Helper to get authentication token."""
        login_data = {
            "email": user.email,
            "password": "testpassword123"
        }
        login_response = await async_client.post("/auth/login", json=login_data)
        return login_response.json()["access_token"]
    
    @pytest.mark.asyncio
    async def test_database_transaction_rollback(self, async_client: AsyncClient, test_agent: User):
        """Test that database transactions are properly rolled back on errors."""
        headers = {
            "Authorization": f"Bearer {await self.get_token(async_client, test_agent)}"
        }
        
        # Try to create a property with invalid data that should cause rollback
        invalid_property_data = {
            "title": "Test Property",
            "description": "Test description",
            "property_type": "invalid_type",  # This should cause validation error
            "price": 1000.00,
            "bedrooms": 2,
            "bathrooms": 1,
            "area_sqft": 1000,
            "location": "Test Location"
        }
        
        response = await async_client.post("/properties", json=invalid_property_data, headers=headers)
        
        # Should fail with validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Database should be in consistent state - verify by creating valid property
        valid_property_data = {
            "title": "Valid Property",
            "description": "Valid description",
            "property_type": "rental",
            "price": 1000.00,
            "bedrooms": 2,
            "bathrooms": 1,
            "area_sqft": 1000,
            "location": "Test Location"
        }
        
        response = await async_client.post("/properties", json=valid_property_data, headers=headers)
        assert response.status_code == status.HTTP_201_CREATED


class TestDockerVolumeIntegration:
    """Tests for Docker volume integration with image uploads."""
    
    async def get_auth_headers(self, async_client: AsyncClient, user: User) -> Dict[str, str]:
        """Helper method to get authentication headers."""
        login_data = {
            "email": user.email,
            "password": "testpassword123"
        }
        login_response = await async_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def create_test_image_file(self, filename: str = "test_image.jpg", size: tuple = (800, 600)) -> io.BytesIO:
        """Create a test image file in memory."""
        image = PILImage.new('RGB', size, color='blue')
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='JPEG')
        image_bytes.seek(0)
        return image_bytes
    
    @pytest.mark.asyncio
    async def test_image_upload_with_docker_volume(self, async_client: AsyncClient, test_property: Property, test_agent: User):
        """Test image upload and storage in Docker volume."""
        headers = await self.get_auth_headers(async_client, test_agent)
        
        # Upload image
        image_file = self.create_test_image_file("docker_test.jpg")
        files = {"file": ("docker_test.jpg", image_file, "image/jpeg")}
        data = {"is_primary": "true"}
        
        upload_response = await async_client.post(
            f"/images/property/{test_property.id}/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        assert upload_response.status_code == status.HTTP_201_CREATED
        upload_data = upload_response.json()
        image_id = upload_data["image"]["id"]
        
        # Verify image can be retrieved
        get_response = await async_client.get(f"/images/{image_id}")
        assert get_response.status_code == status.HTTP_200_OK
        
        # Verify image file can be downloaded
        download_response = await async_client.get(f"/images/{image_id}/file")
        assert download_response.status_code == status.HTTP_200_OK
        assert download_response.headers["content-type"] == "image/jpeg"
    
    @pytest.mark.asyncio
    async def test_image_persistence_across_requests(self, async_client: AsyncClient, test_property: Property, test_agent: User):
        """Test that uploaded images persist across multiple requests."""
        headers = await self.get_auth_headers(async_client, test_agent)
        
        # Upload multiple images
        image_ids = []
        for i in range(3):
            image_file = self.create_test_image_file(f"persist_test_{i}.jpg")
            files = {"file": (f"persist_test_{i}.jpg", image_file, "image/jpeg")}
            data = {"is_primary": "false", "display_order": str(i)}
            
            upload_response = await async_client.post(
                f"/images/property/{test_property.id}/upload",
                files=files,
                data=data,
                headers=headers
            )
            
            assert upload_response.status_code == status.HTTP_201_CREATED
            image_ids.append(upload_response.json()["image"]["id"])
        
        # Verify all images can be retrieved
        for image_id in image_ids:
            get_response = await async_client.get(f"/images/{image_id}")
            assert get_response.status_code == status.HTTP_200_OK
        
        # Verify property has all images
        property_images_response = await async_client.get(f"/images/property/{test_property.id}")
        assert property_images_response.status_code == status.HTTP_200_OK
        
        property_images_data = property_images_response.json()
        assert property_images_data["total"] >= 3
    
    @pytest.mark.asyncio
    async def test_image_cleanup_on_property_deletion(self, async_client: AsyncClient, test_agent: User, property_repository):
        """Test that images are cleaned up when property is deleted."""
        headers = await self.get_auth_headers(async_client, test_agent)
        
        # Create a property to delete
        property_to_delete = await PropertyFactory.create_property(
            property_repository,
            agent_id=test_agent.id,
            title="Property for Deletion Test"
        )
        
        # Upload image to the property
        image_file = self.create_test_image_file("cleanup_test.jpg")
        files = {"file": ("cleanup_test.jpg", image_file, "image/jpeg")}
        data = {"is_primary": "true"}
        
        upload_response = await async_client.post(
            f"/images/property/{property_to_delete.id}/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        assert upload_response.status_code == status.HTTP_201_CREATED
        image_id = upload_response.json()["image"]["id"]
        
        # Verify image exists
        get_response = await async_client.get(f"/images/{image_id}")
        assert get_response.status_code == status.HTTP_200_OK
        
        # Delete the property
        delete_response = await async_client.delete(f"/properties/{property_to_delete.id}", headers=headers)
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify image is also deleted (or at least inaccessible)
        get_response = await async_client.get(f"/images/{image_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND