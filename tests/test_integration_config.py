"""
Configuration and utilities for integration tests.
Provides test environment setup, Docker integration, and test data management.
"""

import os
import asyncio
import pytest
from typing import Dict, Any, Optional
from pathlib import Path
import tempfile
import shutil

# Test environment configuration
TEST_CONFIG = {
    "database": {
        "url": "postgresql+asyncpg://postgres:postgres@localhost:5433/property_listings_test",
        "echo": False,
        "pool_size": 5,
        "max_overflow": 10
    },
    "uploads": {
        "directory": "/tmp/test_uploads",
        "max_file_size": 10 * 1024 * 1024,  # 10MB
        "allowed_extensions": [".jpg", ".jpeg", ".png", ".webp"]
    },
    "auth": {
        "secret_key": "test-secret-key-for-integration-tests",
        "algorithm": "HS256",
        "access_token_expire_minutes": 30,
        "refresh_token_expire_days": 7
    },
    "api": {
        "base_url": "http://test",
        "timeout": 30
    }
}


class TestEnvironmentManager:
    """Manages test environment setup and cleanup."""
    
    def __init__(self):
        self.temp_dirs = []
        self.created_files = []
    
    def setup_test_uploads_directory(self) -> Path:
        """Create temporary uploads directory for testing."""
        temp_dir = Path(tempfile.mkdtemp(prefix="test_uploads_"))
        self.temp_dirs.append(temp_dir)
        
        # Create subdirectories
        (temp_dir / "properties").mkdir(exist_ok=True)
        (temp_dir / "temp").mkdir(exist_ok=True)
        
        return temp_dir
    
    def cleanup(self):
        """Clean up temporary files and directories."""
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
        
        for file_path in self.created_files:
            if file_path.exists():
                file_path.unlink(missing_ok=True)
        
        self.temp_dirs.clear()
        self.created_files.clear()


class TestDataBuilder:
    """Builder for creating test data with various configurations."""
    
    @staticmethod
    def user_data(
        email: str = None,
        password: str = "testpassword123",
        full_name: str = "Test User",
        role: str = "agent",
        is_active: bool = True
    ) -> Dict[str, Any]:
        """Build user test data."""
        import uuid
        return {
            "email": email or f"test_{uuid.uuid4().hex[:8]}@example.com",
            "password": password,
            "full_name": full_name,
            "role": role,
            "is_active": is_active
        }
    
    @staticmethod
    def property_data(
        title: str = "Test Property",
        description: str = "A beautiful test property",
        property_type: str = "rental",
        price: float = 1500.00,
        bedrooms: int = 2,
        bathrooms: int = 1,
        area_sqft: int = 1000,
        location: str = "Test City",
        latitude: float = None,
        longitude: float = None,
        is_active: bool = True
    ) -> Dict[str, Any]:
        """Build property test data."""
        return {
            "title": title,
            "description": description,
            "property_type": property_type,
            "price": price,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "area_sqft": area_sqft,
            "location": location,
            "latitude": latitude,
            "longitude": longitude,
            "is_active": is_active
        }
    
    @staticmethod
    def search_filters(
        query: str = None,
        location: str = None,
        min_price: float = None,
        max_price: float = None,
        bedrooms: int = None,
        bathrooms: int = None,
        property_type: str = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """Build search filter test data."""
        filters = {
            "page": page,
            "page_size": page_size,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
        
        # Add optional filters
        if query:
            filters["query"] = query
        if location:
            filters["location"] = location
        if min_price is not None:
            filters["min_price"] = min_price
        if max_price is not None:
            filters["max_price"] = max_price
        if bedrooms is not None:
            filters["bedrooms"] = bedrooms
        if bathrooms is not None:
            filters["bathrooms"] = bathrooms
        if property_type:
            filters["property_type"] = property_type
        
        return filters


class APITestHelper:
    """Helper class for API testing operations."""
    
    def __init__(self, async_client):
        self.client = async_client
        self._auth_tokens = {}
    
    async def login_user(self, email: str, password: str = "testpassword123") -> Dict[str, str]:
        """Login user and return authentication headers."""
        if email in self._auth_tokens:
            return self._auth_tokens[email]
        
        login_data = {"email": email, "password": password}
        response = await self.client.post("/auth/login", json=login_data)
        
        if response.status_code != 200:
            raise Exception(f"Login failed for {email}: {response.text}")
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        self._auth_tokens[email] = headers
        
        return headers
    
    async def create_property(self, property_data: Dict[str, Any], user_email: str) -> Dict[str, Any]:
        """Create a property via API."""
        headers = await self.login_user(user_email)
        response = await self.client.post("/properties", json=property_data, headers=headers)
        
        if response.status_code != 201:
            raise Exception(f"Property creation failed: {response.text}")
        
        return response.json()
    
    async def upload_image(self, property_id: str, user_email: str, filename: str = "test.jpg") -> Dict[str, Any]:
        """Upload an image to a property via API."""
        from PIL import Image as PILImage
        import io
        
        headers = await self.login_user(user_email)
        
        # Create test image
        image = PILImage.new('RGB', (800, 600), color='red')
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='JPEG')
        image_bytes.seek(0)
        
        files = {"file": (filename, image_bytes, "image/jpeg")}
        data = {"is_primary": "true"}
        
        response = await self.client.post(
            f"/images/property/{property_id}/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        if response.status_code != 201:
            raise Exception(f"Image upload failed: {response.text}")
        
        return response.json()
    
    async def search_properties(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Search properties via API."""
        # Convert filters to query parameters
        params = []
        for key, value in filters.items():
            if value is not None:
                params.append(f"{key}={value}")
        
        query_string = "&".join(params)
        response = await self.client.get(f"/properties?{query_string}")
        
        if response.status_code != 200:
            raise Exception(f"Property search failed: {response.text}")
        
        return response.json()
    
    def clear_auth_cache(self):
        """Clear cached authentication tokens."""
        self._auth_tokens.clear()


class TestScenarioRunner:
    """Runs complex test scenarios combining multiple API operations."""
    
    def __init__(self, api_helper: APITestHelper):
        self.api = api_helper
    
    async def create_complete_property_listing(
        self,
        user_email: str,
        property_data: Dict[str, Any],
        image_count: int = 3
    ) -> Dict[str, Any]:
        """Create a complete property listing with images."""
        # Create property
        property_response = await self.api.create_property(property_data, user_email)
        property_id = property_response["id"]
        
        # Upload images
        images = []
        for i in range(image_count):
            image_response = await self.api.upload_image(
                property_id, 
                user_email, 
                f"property_image_{i}.jpg"
            )
            images.append(image_response["image"])
        
        return {
            "property": property_response,
            "images": images
        }
    
    async def simulate_property_search_journey(
        self,
        search_filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulate a complete property search journey."""
        results = {}
        
        # Initial search
        results["initial_search"] = await self.api.search_properties(search_filters)
        
        # Refine search with price filter
        refined_filters = search_filters.copy()
        if "min_price" not in refined_filters:
            refined_filters["min_price"] = 1000
        if "max_price" not in refined_filters:
            refined_filters["max_price"] = 3000
        
        results["refined_search"] = await self.api.search_properties(refined_filters)
        
        # Search with different sorting
        sorted_filters = refined_filters.copy()
        sorted_filters["sort_by"] = "price"
        sorted_filters["sort_order"] = "asc"
        
        results["sorted_search"] = await self.api.search_properties(sorted_filters)
        
        return results
    
    async def test_property_lifecycle(
        self,
        user_email: str,
        property_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Test complete property lifecycle: create, update, deactivate, delete."""
        results = {}
        
        # Create property
        property_response = await self.api.create_property(property_data, user_email)
        property_id = property_response["id"]
        results["created"] = property_response
        
        # Update property
        headers = await self.api.login_user(user_email)
        update_data = {"title": f"Updated {property_data['title']}", "price": property_data["price"] + 500}
        
        update_response = await self.api.client.put(
            f"/properties/{property_id}",
            json=update_data,
            headers=headers
        )
        results["updated"] = update_response.json()
        
        # Toggle status (deactivate)
        status_response = await self.api.client.patch(
            f"/properties/{property_id}/status",
            headers=headers
        )
        results["status_toggled"] = status_response.json()
        
        # Delete property
        delete_response = await self.api.client.delete(
            f"/properties/{property_id}",
            headers=headers
        )
        results["deleted"] = delete_response.status_code == 204
        
        return results


# Pytest fixtures for integration testing
@pytest.fixture(scope="session")
def test_env_manager():
    """Test environment manager fixture."""
    manager = TestEnvironmentManager()
    yield manager
    manager.cleanup()


@pytest.fixture
def test_data_builder():
    """Test data builder fixture."""
    return TestDataBuilder()


@pytest.fixture
async def api_helper(async_client):
    """API test helper fixture."""
    helper = APITestHelper(async_client)
    yield helper
    helper.clear_auth_cache()


@pytest.fixture
async def scenario_runner(api_helper):
    """Test scenario runner fixture."""
    return TestScenarioRunner(api_helper)


# Test markers for different test categories
pytest_markers = {
    "integration": "Integration tests that test complete API workflows",
    "auth": "Authentication and authorization tests",
    "crud": "CRUD operation tests",
    "search": "Search and filtering tests",
    "upload": "File upload and image management tests",
    "performance": "Performance and load tests",
    "docker": "Docker environment specific tests"
}


def pytest_configure(config):
    """Configure pytest with custom markers."""
    for marker, description in pytest_markers.items():
        config.addinivalue_line("markers", f"{marker}: {description}")


# Environment validation
def validate_test_environment():
    """Validate that test environment is properly configured."""
    required_env_vars = [
        "TEST_DATABASE_URL",
        "TESTING"
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
    
    # Validate database connection
    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url.startswith("postgresql"):
        raise EnvironmentError("TEST_DATABASE_URL must be a PostgreSQL connection string")
    
    return True