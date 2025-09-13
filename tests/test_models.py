"""
Comprehensive tests for database models.
Tests model validation, relationships, and business logic methods.
"""

import pytest
import uuid
from decimal import Decimal
from datetime import datetime

from app.models.user import User, UserRole
from app.models.property import Property, PropertyType
from app.models.image import PropertyImage
from tests.conftest import UserFactory, PropertyFactory, ImageFactory


class TestUserModel:
    """Test User model validation and methods."""
    
    def test_user_creation(self):
        """Test basic user creation."""
        user_data = UserFactory.create_user_data(
            email="test@example.com",
            full_name="Test User",
            role=UserRole.AGENT
        )
        
        user = User(
            email=user_data["email"],
            hashed_password=User.hash_password(user_data["password"]),
            full_name=user_data["full_name"],
            role=user_data["role"],
            is_active=user_data["is_active"]
        )
        
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.role == UserRole.AGENT
        assert user.is_active is True
        assert user.hashed_password is not None
    
    def test_email_validation_valid(self):
        """Test valid email validation."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "123@numbers.com"
        ]
        
        for email in valid_emails:
            normalized = User.validate_email_format(email)
            assert normalized == email.lower()
    
    def test_email_validation_invalid(self):
        """Test invalid email validation."""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test..test@example.com",
            "",
            None
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValueError, match="Invalid email format"):
                User.validate_email_format(email)
    
    def test_password_hashing(self):
        """Test password hashing functionality."""
        password = "testpassword123"
        hashed = User.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
        assert hashed.startswith("$2b$")  # bcrypt prefix
    
    def test_password_hashing_invalid(self):
        """Test password hashing with invalid passwords."""
        invalid_passwords = [
            "",
            "short",
            "1234567",  # 7 chars, minimum is 8
            None
        ]
        
        for password in invalid_passwords:
            with pytest.raises(ValueError, match="Password must be at least 8 characters"):
                User.hash_password(password)
    
    def test_password_verification(self):
        """Test password verification."""
        password = "testpassword123"
        user = User(
            email="test@example.com",
            hashed_password=User.hash_password(password),
            full_name="Test User",
            role=UserRole.AGENT
        )
        
        assert user.verify_password(password) is True
        assert user.verify_password("wrongpassword") is False
        assert user.verify_password("") is False
    
    def test_set_password(self):
        """Test set_password method."""
        user = User(
            email="test@example.com",
            hashed_password="old_hash",
            full_name="Test User",
            role=UserRole.AGENT
        )
        
        new_password = "newpassword123"
        user.set_password(new_password)
        
        assert user.hashed_password != "old_hash"
        assert user.verify_password(new_password) is True
    
    def test_role_properties(self):
        """Test role property methods."""
        agent = User(
            email="agent@example.com",
            hashed_password="hash",
            full_name="Agent User",
            role=UserRole.AGENT
        )
        
        admin = User(
            email="admin@example.com",
            hashed_password="hash",
            full_name="Admin User",
            role=UserRole.ADMIN
        )
        
        assert agent.is_agent is True
        assert agent.is_admin is False
        assert admin.is_agent is False
        assert admin.is_admin is True
    
    def test_can_manage_property(self):
        """Test property management permissions."""
        agent_id = uuid.uuid4()
        other_agent_id = uuid.uuid4()
        
        agent = User(
            id=agent_id,
            email="agent@example.com",
            hashed_password="hash",
            full_name="Agent User",
            role=UserRole.AGENT
        )
        
        admin = User(
            id=uuid.uuid4(),
            email="admin@example.com",
            hashed_password="hash",
            full_name="Admin User",
            role=UserRole.ADMIN
        )
        
        # Agent can manage their own properties
        assert agent.can_manage_property(agent_id) is True
        # Agent cannot manage other's properties
        assert agent.can_manage_property(other_agent_id) is False
        # Admin can manage all properties
        assert admin.can_manage_property(agent_id) is True
        assert admin.can_manage_property(other_agent_id) is True
    
    def test_to_dict(self):
        """Test user dictionary conversion."""
        user = User(
            email="test@example.com",
            hashed_password="hash",
            full_name="Test User",
            role=UserRole.AGENT,
            is_active=True
        )
        
        user_dict = user.to_dict()
        
        assert "id" in user_dict
        assert user_dict["email"] == "test@example.com"
        assert user_dict["full_name"] == "Test User"
        assert user_dict["role"] == "agent"
        assert user_dict["is_active"] is True
        assert "hashed_password" not in user_dict  # Should not include sensitive data
        assert "created_at" in user_dict
        assert "updated_at" in user_dict
    
    def test_user_repr(self):
        """Test user string representation."""
        user = User(
            email="test@example.com",
            hashed_password="hash",
            full_name="Test User",
            role=UserRole.AGENT
        )
        
        repr_str = repr(user)
        assert "User" in repr_str
        assert "test@example.com" in repr_str
        assert "agent" in repr_str


class TestPropertyModel:
    """Test Property model validation and methods."""
    
    def test_property_creation(self):
        """Test basic property creation."""
        agent_id = uuid.uuid4()
        property_data = PropertyFactory.create_property_data(
            title="Test Property",
            price=Decimal("1500.00"),
            bedrooms=3,
            agent_id=agent_id
        )
        
        property_obj = Property(**property_data)
        
        assert property_obj.title == "Test Property"
        assert property_obj.price == Decimal("1500.00")
        assert property_obj.bedrooms == 3
        assert property_obj.agent_id == agent_id
        assert property_obj.is_active is True
    
    def test_price_validation_valid(self):
        """Test valid price validation."""
        property_obj = Property(
            title="Test",
            description="Test",
            property_type=PropertyType.RENTAL,
            price=Decimal("1000.00"),
            bedrooms=2,
            bathrooms=1,
            area_sqft=1000,
            location="Test",
            agent_id=uuid.uuid4()
        )
        
        # Should not raise exception
        property_obj.validate_price()
    
    def test_price_validation_invalid(self):
        """Test invalid price validation."""
        # Test negative price
        property_obj = Property(
            title="Test",
            description="Test",
            property_type=PropertyType.RENTAL,
            price=Decimal("-100.00"),
            bedrooms=2,
            bathrooms=1,
            area_sqft=1000,
            location="Test",
            agent_id=uuid.uuid4()
        )
        
        with pytest.raises(ValueError, match="Property price must be greater than 0"):
            property_obj.validate_price()
        
        # Test zero price
        property_obj.price = Decimal("0.00")
        with pytest.raises(ValueError, match="Property price must be greater than 0"):
            property_obj.validate_price()
        
        # Test excessive price
        property_obj.price = Decimal("1000000000.00")
        with pytest.raises(ValueError, match="Property price exceeds maximum"):
            property_obj.validate_price()
    
    def test_bedrooms_validation_valid(self):
        """Test valid bedrooms validation."""
        property_obj = Property(
            title="Test",
            description="Test",
            property_type=PropertyType.RENTAL,
            price=Decimal("1000.00"),
            bedrooms=3,
            bathrooms=1,
            area_sqft=1000,
            location="Test",
            agent_id=uuid.uuid4()
        )
        
        # Should not raise exception
        property_obj.validate_bedrooms()
    
    def test_bedrooms_validation_invalid(self):
        """Test invalid bedrooms validation."""
        property_obj = Property(
            title="Test",
            description="Test",
            property_type=PropertyType.RENTAL,
            price=Decimal("1000.00"),
            bedrooms=-1,
            bathrooms=1,
            area_sqft=1000,
            location="Test",
            agent_id=uuid.uuid4()
        )
        
        with pytest.raises(ValueError, match="Number of bedrooms cannot be negative"):
            property_obj.validate_bedrooms()
        
        property_obj.bedrooms = 100
        with pytest.raises(ValueError, match="Number of bedrooms exceeds reasonable limit"):
            property_obj.validate_bedrooms()
    
    def test_bathrooms_validation_valid(self):
        """Test valid bathrooms validation."""
        property_obj = Property(
            title="Test",
            description="Test",
            property_type=PropertyType.RENTAL,
            price=Decimal("1000.00"),
            bedrooms=2,
            bathrooms=2,
            area_sqft=1000,
            location="Test",
            agent_id=uuid.uuid4()
        )
        
        # Should not raise exception
        property_obj.validate_bathrooms()
    
    def test_bathrooms_validation_invalid(self):
        """Test invalid bathrooms validation."""
        property_obj = Property(
            title="Test",
            description="Test",
            property_type=PropertyType.RENTAL,
            price=Decimal("1000.00"),
            bedrooms=2,
            bathrooms=-1,
            area_sqft=1000,
            location="Test",
            agent_id=uuid.uuid4()
        )
        
        with pytest.raises(ValueError, match="Number of bathrooms cannot be negative"):
            property_obj.validate_bathrooms()
        
        property_obj.bathrooms = 100
        with pytest.raises(ValueError, match="Number of bathrooms exceeds reasonable limit"):
            property_obj.validate_bathrooms()
    
    def test_area_validation_valid(self):
        """Test valid area validation."""
        property_obj = Property(
            title="Test",
            description="Test",
            property_type=PropertyType.RENTAL,
            price=Decimal("1000.00"),
            bedrooms=2,
            bathrooms=1,
            area_sqft=1500,
            location="Test",
            agent_id=uuid.uuid4()
        )
        
        # Should not raise exception
        property_obj.validate_area()
    
    def test_area_validation_invalid(self):
        """Test invalid area validation."""
        property_obj = Property(
            title="Test",
            description="Test",
            property_type=PropertyType.RENTAL,
            price=Decimal("1000.00"),
            bedrooms=2,
            bathrooms=1,
            area_sqft=0,
            location="Test",
            agent_id=uuid.uuid4()
        )
        
        with pytest.raises(ValueError, match="Property area must be greater than 0"):
            property_obj.validate_area()
        
        property_obj.area_sqft = 2000000
        with pytest.raises(ValueError, match="Property area exceeds reasonable limit"):
            property_obj.validate_area()
    
    def test_coordinates_validation_valid(self):
        """Test valid coordinates validation."""
        property_obj = Property(
            title="Test",
            description="Test",
            property_type=PropertyType.RENTAL,
            price=Decimal("1000.00"),
            bedrooms=2,
            bathrooms=1,
            area_sqft=1000,
            location="Test",
            latitude=Decimal("25.2048"),
            longitude=Decimal("55.2708"),
            agent_id=uuid.uuid4()
        )
        
        # Should not raise exception
        property_obj.validate_coordinates()
    
    def test_coordinates_validation_invalid(self):
        """Test invalid coordinates validation."""
        property_obj = Property(
            title="Test",
            description="Test",
            property_type=PropertyType.RENTAL,
            price=Decimal("1000.00"),
            bedrooms=2,
            bathrooms=1,
            area_sqft=1000,
            location="Test",
            latitude=Decimal("91.0"),  # Invalid latitude
            longitude=Decimal("55.2708"),
            agent_id=uuid.uuid4()
        )
        
        with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
            property_obj.validate_coordinates()
        
        property_obj.latitude = Decimal("25.2048")
        property_obj.longitude = Decimal("181.0")  # Invalid longitude
        with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
            property_obj.validate_coordinates()
    
    def test_validate_all(self):
        """Test comprehensive validation."""
        # Valid property
        property_obj = Property(
            title="Test Property",
            description="A test property",
            property_type=PropertyType.RENTAL,
            price=Decimal("1500.00"),
            bedrooms=3,
            bathrooms=2,
            area_sqft=1200,
            location="Test City",
            latitude=Decimal("25.2048"),
            longitude=Decimal("55.2708"),
            agent_id=uuid.uuid4()
        )
        
        # Should not raise exception
        property_obj.validate_all()
        
        # Invalid property
        property_obj.price = Decimal("-100.00")
        with pytest.raises(ValueError):
            property_obj.validate_all()
    
    def test_to_dict_basic(self):
        """Test basic property dictionary conversion."""
        agent_id = uuid.uuid4()
        property_obj = Property(
            title="Test Property",
            description="A test property",
            property_type=PropertyType.RENTAL,
            price=Decimal("1500.00"),
            bedrooms=3,
            bathrooms=2,
            area_sqft=1200,
            location="Test City",
            agent_id=agent_id
        )
        
        property_dict = property_obj.to_dict()
        
        assert "id" in property_dict
        assert property_dict["title"] == "Test Property"
        assert property_dict["property_type"] == "rental"
        assert property_dict["price"] == 1500.00
        assert property_dict["bedrooms"] == 3
        assert property_dict["agent_id"] == str(agent_id)
        assert "agent" not in property_dict  # Not included by default
        assert "images" not in property_dict  # Not included by default
    
    def test_property_repr(self):
        """Test property string representation."""
        property_obj = Property(
            title="Test Property",
            description="A test property",
            property_type=PropertyType.RENTAL,
            price=Decimal("1500.00"),
            bedrooms=3,
            bathrooms=2,
            area_sqft=1200,
            location="Test City",
            agent_id=uuid.uuid4()
        )
        
        repr_str = repr(property_obj)
        assert "Property" in repr_str
        assert "Test Property" in repr_str
        assert "1500" in repr_str


class TestPropertyImageModel:
    """Test PropertyImage model validation and methods."""
    
    def test_image_creation(self):
        """Test basic image creation."""
        property_id = uuid.uuid4()
        image_data = ImageFactory.create_image_data(
            property_id=property_id,
            filename="test.jpg",
            file_size=1024000
        )
        
        image = PropertyImage(**image_data)
        
        assert image.property_id == property_id
        assert image.filename == "test.jpg"
        assert image.file_size == 1024000
        assert image.mime_type == "image/jpeg"
        assert image.is_primary is False
    
    def test_file_size_mb_property(self):
        """Test file size in MB calculation."""
        image = PropertyImage(
            property_id=uuid.uuid4(),
            filename="test.jpg",
            file_path="/test/test.jpg",
            file_size=2048000,  # 2MB
            mime_type="image/jpeg"
        )
        
        assert image.file_size_mb == 1.95  # Should be rounded to 2 decimal places
    
    def test_file_extension_property(self):
        """Test file extension extraction."""
        image = PropertyImage(
            property_id=uuid.uuid4(),
            filename="test_image.jpeg",
            file_path="/test/test_image.jpeg",
            file_size=1024000,
            mime_type="image/jpeg"
        )
        
        assert image.file_extension == "jpeg"
        
        # Test file without extension
        image.filename = "noextension"
        assert image.file_extension == ""
    
    def test_aspect_ratio_property(self):
        """Test aspect ratio calculation."""
        image = PropertyImage(
            property_id=uuid.uuid4(),
            filename="test.jpg",
            file_path="/test/test.jpg",
            file_size=1024000,
            mime_type="image/jpeg",
            width=1920,
            height=1080
        )
        
        assert image.aspect_ratio == 1.78  # 16:9 ratio
        
        # Test without dimensions
        image.width = None
        image.height = None
        assert image.aspect_ratio is None
    
    def test_file_size_validation_valid(self):
        """Test valid file size validation."""
        image = PropertyImage(
            property_id=uuid.uuid4(),
            filename="test.jpg",
            file_path="/test/test.jpg",
            file_size=5 * 1024 * 1024,  # 5MB
            mime_type="image/jpeg"
        )
        
        # Should not raise exception
        image.validate_file_size(max_size_mb=10)
    
    def test_file_size_validation_invalid(self):
        """Test invalid file size validation."""
        image = PropertyImage(
            property_id=uuid.uuid4(),
            filename="test.jpg",
            file_path="/test/test.jpg",
            file_size=15 * 1024 * 1024,  # 15MB
            mime_type="image/jpeg"
        )
        
        with pytest.raises(ValueError, match="File size.*exceeds maximum"):
            image.validate_file_size(max_size_mb=10)
    
    def test_mime_type_validation_valid(self):
        """Test valid MIME type validation."""
        valid_types = ["image/jpeg", "image/png", "image/webp"]
        
        for mime_type in valid_types:
            image = PropertyImage(
                property_id=uuid.uuid4(),
                filename="test.jpg",
                file_path="/test/test.jpg",
                file_size=1024000,
                mime_type=mime_type
            )
            
            # Should not raise exception
            image.validate_mime_type()
    
    def test_mime_type_validation_invalid(self):
        """Test invalid MIME type validation."""
        image = PropertyImage(
            property_id=uuid.uuid4(),
            filename="test.txt",
            file_path="/test/test.txt",
            file_size=1024,
            mime_type="text/plain"
        )
        
        with pytest.raises(ValueError, match="MIME type.*is not allowed"):
            image.validate_mime_type()
    
    def test_dimensions_validation_valid(self):
        """Test valid dimensions validation."""
        image = PropertyImage(
            property_id=uuid.uuid4(),
            filename="test.jpg",
            file_path="/test/test.jpg",
            file_size=1024000,
            mime_type="image/jpeg",
            width=800,
            height=600
        )
        
        # Should not raise exception
        image.validate_dimensions()
    
    def test_dimensions_validation_invalid(self):
        """Test invalid dimensions validation."""
        # Test width too small
        image = PropertyImage(
            property_id=uuid.uuid4(),
            filename="test.jpg",
            file_path="/test/test.jpg",
            file_size=1024000,
            mime_type="image/jpeg",
            width=50,  # Too small
            height=600
        )
        
        with pytest.raises(ValueError, match="Image width.*is below minimum"):
            image.validate_dimensions()
        
        # Test height too large
        image.width = 800
        image.height = 15000  # Too large
        with pytest.raises(ValueError, match="Image height.*exceeds maximum"):
            image.validate_dimensions()
    
    def test_validate_all(self):
        """Test comprehensive image validation."""
        # Valid image
        image = PropertyImage(
            property_id=uuid.uuid4(),
            filename="test.jpg",
            file_path="/test/test.jpg",
            file_size=2 * 1024 * 1024,  # 2MB
            mime_type="image/jpeg",
            width=1200,
            height=800
        )
        
        # Should not raise exception
        image.validate_all()
        
        # Invalid image
        image.mime_type = "text/plain"
        with pytest.raises(ValueError):
            image.validate_all()
    
    def test_to_dict_basic(self):
        """Test basic image dictionary conversion."""
        property_id = uuid.uuid4()
        image = PropertyImage(
            property_id=property_id,
            filename="test.jpg",
            file_path="/test/test.jpg",
            file_size=1024000,
            mime_type="image/jpeg",
            width=800,
            height=600,
            is_primary=True
        )
        
        image_dict = image.to_dict()
        
        assert "id" in image_dict
        assert image_dict["property_id"] == str(property_id)
        assert image_dict["filename"] == "test.jpg"
        assert image_dict["file_size"] == 1024000
        assert image_dict["file_size_mb"] == 0.98
        assert image_dict["mime_type"] == "image/jpeg"
        assert image_dict["width"] == 800
        assert image_dict["height"] == 600
        assert image_dict["aspect_ratio"] == 1.33
        assert image_dict["is_primary"] is True
        assert image_dict["file_extension"] == "jpg"
        assert "property" not in image_dict  # Not included by default
    
    def test_image_repr(self):
        """Test image string representation."""
        property_id = uuid.uuid4()
        image = PropertyImage(
            property_id=property_id,
            filename="test.jpg",
            file_path="/test/test.jpg",
            file_size=1024000,
            mime_type="image/jpeg"
        )
        
        repr_str = repr(image)
        assert "PropertyImage" in repr_str
        assert str(property_id) in repr_str
        assert "test.jpg" in repr_str