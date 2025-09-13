"""
Test configuration and fixtures for the property listing API.
Provides database fixtures, test data factories, and common test utilities.
"""

import pytest
import asyncio
import uuid
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from httpx import AsyncClient
import os
from decimal import Decimal

from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.models.property import Property, PropertyType
from app.models.image import PropertyImage
from app.repositories.user import UserRepository
from app.repositories.property import PropertyRepository
from app.repositories.image import ImageRepository
from app.services.auth import AuthService
from app.services.property import PropertyService
from app.services.image import ImageService


# Test database configuration
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5433/property_listings_test"
)

# Create async engine for testing
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False} if "sqlite" in TEST_DATABASE_URL else {}
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Set up test database schema."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest.fixture
def client(db_session: AsyncSession) -> TestClient:
    """Create a test client with database session override."""
    def override_get_db():
        return db_session
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with database session override."""
    def override_get_db():
        return db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


# Repository fixtures
@pytest.fixture
def user_repository(db_session: AsyncSession) -> UserRepository:
    """Create a user repository instance."""
    return UserRepository(db_session)


@pytest.fixture
def property_repository(db_session: AsyncSession) -> PropertyRepository:
    """Create a property repository instance."""
    return PropertyRepository(db_session)


@pytest.fixture
def image_repository(db_session: AsyncSession) -> ImageRepository:
    """Create an image repository instance."""
    return ImageRepository(db_session)


# Service fixtures
@pytest.fixture
def auth_service(db_session: AsyncSession) -> AuthService:
    """Create an auth service instance."""
    return AuthService(db_session)


@pytest.fixture
def property_service(db_session: AsyncSession) -> PropertyService:
    """Create a property service instance."""
    return PropertyService(db_session)


@pytest.fixture
def image_service(db_session: AsyncSession) -> ImageService:
    """Create an image service instance."""
    return ImageService(db_session)


# Test data factories
class UserFactory:
    """Factory for creating test users."""
    
    @staticmethod
    def create_user_data(
        email: str = None,
        password: str = "testpassword123",
        full_name: str = "Test User",
        role: UserRole = UserRole.AGENT,
        is_active: bool = True
    ) -> dict:
        """Create user data dictionary."""
        return {
            "email": email or f"test{uuid.uuid4().hex[:8]}@example.com",
            "password": password,
            "full_name": full_name,
            "role": role,
            "is_active": is_active
        }
    
    @staticmethod
    async def create_user(
        user_repo: UserRepository,
        email: str = None,
        password: str = "testpassword123",
        full_name: str = "Test User",
        role: UserRole = UserRole.AGENT,
        is_active: bool = True
    ) -> User:
        """Create a test user in the database."""
        user_data = UserFactory.create_user_data(
            email=email,
            password=password,
            full_name=full_name,
            role=role,
            is_active=is_active
        )
        return await user_repo.create_user(user_data)


class PropertyFactory:
    """Factory for creating test properties."""
    
    @staticmethod
    def create_property_data(
        title: str = "Test Property",
        description: str = "A beautiful test property",
        property_type: PropertyType = PropertyType.RENTAL,
        price: Decimal = Decimal("1000.00"),
        bedrooms: int = 2,
        bathrooms: int = 1,
        area_sqft: int = 1000,
        location: str = "Test City",
        latitude: Decimal = None,
        longitude: Decimal = None,
        agent_id: uuid.UUID = None,
        is_active: bool = True
    ) -> dict:
        """Create property data dictionary."""
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
            "agent_id": agent_id,
            "is_active": is_active
        }
    
    @staticmethod
    async def create_property(
        property_repo: PropertyRepository,
        agent_id: uuid.UUID,
        title: str = "Test Property",
        description: str = "A beautiful test property",
        property_type: PropertyType = PropertyType.RENTAL,
        price: Decimal = Decimal("1000.00"),
        bedrooms: int = 2,
        bathrooms: int = 1,
        area_sqft: int = 1000,
        location: str = "Test City",
        latitude: Decimal = None,
        longitude: Decimal = None,
        is_active: bool = True
    ) -> Property:
        """Create a test property in the database."""
        property_data = PropertyFactory.create_property_data(
            title=title,
            description=description,
            property_type=property_type,
            price=price,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            area_sqft=area_sqft,
            location=location,
            latitude=latitude,
            longitude=longitude,
            agent_id=agent_id,
            is_active=is_active
        )
        return await property_repo.create_property(property_data)


class ImageFactory:
    """Factory for creating test property images."""
    
    @staticmethod
    def create_image_data(
        property_id: uuid.UUID,
        filename: str = "test_image.jpg",
        file_path: str = "/uploads/test/test_image.jpg",
        file_size: int = 1024000,  # 1MB
        mime_type: str = "image/jpeg",
        width: int = 800,
        height: int = 600,
        is_primary: bool = False,
        display_order: int = 0
    ) -> dict:
        """Create image data dictionary."""
        return {
            "property_id": property_id,
            "filename": filename,
            "file_path": file_path,
            "file_size": file_size,
            "mime_type": mime_type,
            "width": width,
            "height": height,
            "is_primary": is_primary,
            "display_order": display_order
        }
    
    @staticmethod
    async def create_image(
        image_repo: ImageRepository,
        property_id: uuid.UUID,
        filename: str = "test_image.jpg",
        file_path: str = None,
        file_size: int = 1024000,
        mime_type: str = "image/jpeg",
        width: int = 800,
        height: int = 600,
        is_primary: bool = False,
        display_order: int = 0
    ) -> PropertyImage:
        """Create a test property image in the database."""
        if file_path is None:
            file_path = f"/uploads/test/{uuid.uuid4().hex}/{filename}"
        
        image_data = ImageFactory.create_image_data(
            property_id=property_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            width=width,
            height=height,
            is_primary=is_primary,
            display_order=display_order
        )
        return await image_repo.create(image_data)


# Common test fixtures
@pytest.fixture
async def test_agent(user_repository: UserRepository) -> User:
    """Create a test agent user."""
    return await UserFactory.create_user(
        user_repository,
        email="agent@test.com",
        full_name="Test Agent",
        role=UserRole.AGENT
    )


@pytest.fixture
async def test_admin(user_repository: UserRepository) -> User:
    """Create a test admin user."""
    return await UserFactory.create_user(
        user_repository,
        email="admin@test.com",
        full_name="Test Admin",
        role=UserRole.ADMIN
    )


@pytest.fixture
async def test_inactive_user(user_repository: UserRepository) -> User:
    """Create a test inactive user."""
    return await UserFactory.create_user(
        user_repository,
        email="inactive@test.com",
        full_name="Inactive User",
        role=UserRole.AGENT,
        is_active=False
    )


@pytest.fixture
async def test_property(property_repository: PropertyRepository, test_agent: User) -> Property:
    """Create a test property."""
    return await PropertyFactory.create_property(
        property_repository,
        agent_id=test_agent.id,
        title="Test Property",
        price=Decimal("1500.00"),
        bedrooms=3,
        location="Test Location"
    )


@pytest.fixture
async def test_inactive_property(property_repository: PropertyRepository, test_agent: User) -> Property:
    """Create a test inactive property."""
    return await PropertyFactory.create_property(
        property_repository,
        agent_id=test_agent.id,
        title="Inactive Property",
        price=Decimal("2000.00"),
        is_active=False
    )


@pytest.fixture
async def test_property_image(image_repository: ImageRepository, test_property: Property) -> PropertyImage:
    """Create a test property image."""
    return await ImageFactory.create_image(
        image_repository,
        property_id=test_property.id,
        filename="test_property.jpg",
        is_primary=True
    )


# Utility functions for tests
def assert_user_equal(user1: User, user2: User, check_password: bool = False):
    """Assert that two users are equal."""
    assert user1.id == user2.id
    assert user1.email == user2.email
    assert user1.full_name == user2.full_name
    assert user1.role == user2.role
    assert user1.is_active == user2.is_active
    
    if check_password:
        assert user1.hashed_password == user2.hashed_password


def assert_property_equal(prop1: Property, prop2: Property):
    """Assert that two properties are equal."""
    assert prop1.id == prop2.id
    assert prop1.title == prop2.title
    assert prop1.description == prop2.description
    assert prop1.property_type == prop2.property_type
    assert prop1.price == prop2.price
    assert prop1.bedrooms == prop2.bedrooms
    assert prop1.bathrooms == prop2.bathrooms
    assert prop1.area_sqft == prop2.area_sqft
    assert prop1.location == prop2.location
    assert prop1.agent_id == prop2.agent_id
    assert prop1.is_active == prop2.is_active


def assert_image_equal(img1: PropertyImage, img2: PropertyImage):
    """Assert that two property images are equal."""
    assert img1.id == img2.id
    assert img1.property_id == img2.property_id
    assert img1.filename == img2.filename
    assert img1.file_path == img2.file_path
    assert img1.file_size == img2.file_size
    assert img1.mime_type == img2.mime_type
    assert img1.is_primary == img2.is_primary