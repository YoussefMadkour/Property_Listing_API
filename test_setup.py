#!/usr/bin/env python3
"""
Simple test setup verification script.
Runs a basic test to ensure the test environment is working.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

async def test_basic_imports():
    """Test that we can import all necessary modules."""
    try:
        print("Testing basic imports...")
        
        # Test model imports
        from app.models.user import User, UserRole
        from app.models.property import Property, PropertyType
        from app.models.image import PropertyImage
        print("✅ Model imports successful")
        
        # Test repository imports
        from app.repositories.user import UserRepository
        from app.repositories.property import PropertyRepository
        from app.repositories.image import ImageRepository
        print("✅ Repository imports successful")
        
        # Test service imports
        from app.services.auth import AuthService
        from app.services.property import PropertyService
        print("✅ Service imports successful")
        
        # Test database imports
        from app.database import Base, get_db
        print("✅ Database imports successful")
        
        print("\n🎉 All imports successful! Test environment is ready.")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


async def test_model_creation():
    """Test basic model creation without database."""
    try:
        print("\nTesting model creation...")
        
        # Test User model
        from app.models.user import User, UserRole
        user = User(
            email="test@example.com",
            hashed_password="hashed_password",
            full_name="Test User",
            role=UserRole.AGENT
        )
        assert user.email == "test@example.com"
        assert user.role == UserRole.AGENT
        print("✅ User model creation successful")
        
        # Test Property model
        from app.models.property import Property, PropertyType
        from decimal import Decimal
        import uuid
        
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
        assert property_obj.title == "Test Property"
        assert property_obj.price == Decimal("1500.00")
        print("✅ Property model creation successful")
        
        # Test PropertyImage model
        from app.models.image import PropertyImage
        
        image = PropertyImage(
            property_id=uuid.uuid4(),
            filename="test.jpg",
            file_path="/test/test.jpg",
            file_size=1024000,
            mime_type="image/jpeg"
        )
        assert image.filename == "test.jpg"
        assert image.file_size == 1024000
        print("✅ PropertyImage model creation successful")
        
        print("\n🎉 All model creation tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Model creation error: {e}")
        return False


async def test_validation():
    """Test model validation methods."""
    try:
        print("\nTesting model validation...")
        
        # Test User validation
        from app.models.user import User
        
        # Test email validation
        valid_email = User.validate_email_format("test@gmail.com")
        assert valid_email == "test@gmail.com"
        print("✅ User email validation successful")
        
        # Test password hashing
        password = "testpassword123"
        hashed = User.hash_password(password)
        assert hashed != password
        assert len(hashed) > 50
        print("✅ User password hashing successful")
        
        # Test Property validation
        from app.models.property import Property, PropertyType
        from decimal import Decimal
        import uuid
        
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
        
        # Should not raise exception
        property_obj.validate_all()
        print("✅ Property validation successful")
        
        # Test PropertyImage validation
        from app.models.image import PropertyImage
        
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
        image.validate_all()
        print("✅ PropertyImage validation successful")
        
        print("\n🎉 All validation tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False


async def main():
    """Run all setup tests."""
    print("🚀 Starting test setup verification...\n")
    
    tests = [
        test_basic_imports,
        test_model_creation,
        test_validation
    ]
    
    all_passed = True
    
    for test in tests:
        try:
            result = await test()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("🎉 All setup tests passed! The test environment is ready.")
        print("\nYou can now run the full test suite with:")
        print("  python run_tests.py")
        print("\nOr run specific tests with:")
        print("  python -m pytest tests/test_models.py -v")
        print("  python -m pytest tests/test_repositories.py -v")
        print("  python -m pytest tests/test_services.py -v")
        return 0
    else:
        print("❌ Some setup tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))