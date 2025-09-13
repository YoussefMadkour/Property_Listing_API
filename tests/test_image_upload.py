"""
Basic test for image upload functionality.
This is a simple test to verify the image upload system works.
"""

import pytest
import uuid
from pathlib import Path
from PIL import Image
import io
from fastapi.testclient import TestClient

from app.main import app
from app.utils.file_utils import FileValidator, FileStorage

client = TestClient(app)


def create_test_image(width: int = 800, height: int = 600, format: str = "JPEG") -> bytes:
    """Create a test image in memory."""
    img = Image.new('RGB', (width, height), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format=format)
    img_bytes.seek(0)
    return img_bytes.getvalue()


def test_file_validator_valid_image():
    """Test file validator with valid image."""
    validator = FileValidator()
    
    # Test valid extension
    extension = validator.validate_file_extension("test.jpg")
    assert extension == ".jpg"
    
    # Test valid MIME type
    mime_type = validator.validate_mime_type("image/jpeg")
    assert mime_type == "image/jpeg"
    
    # Test valid file size
    file_size = validator.validate_file_size(1024 * 1024)  # 1MB
    assert file_size == 1024 * 1024
    
    # Test valid dimensions
    width, height = validator.validate_image_dimensions(800, 600)
    assert width == 800
    assert height == 600


def test_file_validator_invalid_extension():
    """Test file validator with invalid extension."""
    validator = FileValidator()
    
    with pytest.raises(Exception):  # Should raise ValidationError
        validator.validate_file_extension("test.txt")


def test_file_validator_invalid_mime_type():
    """Test file validator with invalid MIME type."""
    validator = FileValidator()
    
    with pytest.raises(Exception):  # Should raise ValidationError
        validator.validate_mime_type("text/plain")


def test_file_validator_oversized_file():
    """Test file validator with oversized file."""
    validator = FileValidator()
    
    with pytest.raises(Exception):  # Should raise ValidationError
        validator.validate_file_size(20 * 1024 * 1024)  # 20MB


def test_file_storage_path_generation():
    """Test file storage path generation."""
    storage = FileStorage()
    property_id = uuid.uuid4()
    
    # Test unique filename generation
    filename1 = storage.generate_unique_filename("test.jpg")
    filename2 = storage.generate_unique_filename("test.jpg")
    assert filename1 != filename2
    assert filename1.endswith(".jpg")
    assert filename2.endswith(".jpg")
    
    # Test property directory creation
    property_dir = storage.get_property_directory(property_id)
    assert property_dir.exists()
    assert str(property_id) in str(property_dir)
    
    # Test file path generation
    file_path = storage.generate_file_path(property_id, "test.jpg")
    assert file_path.parent == property_dir
    assert file_path.suffix == ".jpg"


def test_image_endpoints_without_auth():
    """Test image endpoints return proper authentication errors."""
    # Test upload without authentication
    response = client.post(
        f"/api/v1/images/property/{uuid.uuid4()}/upload",
        files={"file": ("test.jpg", create_test_image(), "image/jpeg")}
    )
    assert response.status_code == 401  # Unauthorized
    
    # Test get images (should work without auth)
    response = client.get(f"/api/v1/images/property/{uuid.uuid4()}")
    assert response.status_code in [200, 404]  # Either OK or not found


def test_application_starts():
    """Test that the application starts properly."""
    response = client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "status" in data


if __name__ == "__main__":
    pytest.main([__file__])