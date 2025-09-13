"""
Tests for comprehensive error handling and validation.
Tests custom exceptions, validation middleware, and error response formatting.
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError
from unittest.mock import Mock, patch
import json

from app.main import app
from app.services.error_handler import ErrorHandlerService
from app.utils.exceptions import (
    APIException,
    ValidationError,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    BadRequestError,
    ConflictError
)
from app.middleware.validation import ValidationMiddleware, RequestValidationMiddleware
from app.utils.validators import ValidationUtils, BusinessRuleValidator


class TestErrorHandlerService:
    """Test error handler service functionality."""
    
    def test_format_error_response(self):
        """Test error response formatting."""
        response = ErrorHandlerService.format_error_response(
            error_code="TEST_ERROR",
            message="Test error message",
            details=[{"field": "test", "message": "Test field error"}],
            request_id="test123"
        )
        
        assert response["error"]["code"] == "TEST_ERROR"
        assert response["error"]["message"] == "Test error message"
        assert response["error"]["request_id"] == "test123"
        assert len(response["error"]["details"]) == 1
        assert response["error"]["details"][0]["field"] == "test"
        assert "timestamp" in response["error"]
    
    def test_handle_api_exception(self):
        """Test API exception handling."""
        exception = ValidationError("Test validation error")
        response = ErrorHandlerService.handle_api_exception(exception)
        
        assert response.status_code == 422
        response_data = json.loads(response.body)
        assert response_data["error"]["code"] == "VALIDATION_ERROR"
        assert response_data["error"]["message"] == "Test validation error"
    
    def test_handle_validation_error(self):
        """Test Pydantic validation error handling."""
        # Create a mock validation error
        mock_error = Mock()
        mock_error.errors.return_value = [
            {
                "loc": ("field1",),
                "msg": "Field is required",
                "type": "missing",
                "input": None
            },
            {
                "loc": ("field2", "nested"),
                "msg": "Invalid value",
                "type": "value_error",
                "input": "invalid"
            }
        ]
        
        response = ErrorHandlerService.handle_validation_error(mock_error)
        
        assert response.status_code == 422
        response_data = json.loads(response.body)
        assert response_data["error"]["code"] == "VALIDATION_ERROR"
        assert len(response_data["error"]["details"]) == 2
        assert response_data["error"]["details"][0]["field"] == "field1"
        assert response_data["error"]["details"][1]["field"] == "field2 -> nested"
    
    def test_handle_database_error(self):
        """Test database error handling."""
        # Test integrity error
        integrity_error = IntegrityError("statement", "params", "orig")
        response = ErrorHandlerService.handle_database_error(integrity_error)
        
        assert response.status_code == 409
        response_data = json.loads(response.body)
        assert response_data["error"]["code"] == "INTEGRITY_ERROR"
    
    def test_handle_unexpected_error(self):
        """Test unexpected error handling."""
        exception = Exception("Unexpected error")
        response = ErrorHandlerService.handle_unexpected_error(exception)
        
        assert response.status_code == 500
        response_data = json.loads(response.body)
        assert response_data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert "unexpected error occurred" in response_data["error"]["message"].lower()


class TestValidationUtils:
    """Test validation utilities."""
    
    def test_validate_uuid_valid(self):
        """Test valid UUID validation."""
        valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
        result = ValidationUtils.validate_uuid(valid_uuid)
        assert result == valid_uuid
    
    def test_validate_uuid_invalid(self):
        """Test invalid UUID validation."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationUtils.validate_uuid("invalid-uuid")
        assert "Invalid UUID format" in str(exc_info.value.detail)
    
    def test_validate_string_valid(self):
        """Test valid string validation."""
        result = ValidationUtils.validate_string(
            "Test String",
            "test_field",
            min_length=5,
            max_length=20
        )
        assert result == "Test String"
    
    def test_validate_string_too_short(self):
        """Test string too short validation."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationUtils.validate_string(
                "Hi",
                "test_field",
                min_length=5
            )
        assert "must be at least 5 characters" in str(exc_info.value.detail)
    
    def test_validate_string_too_long(self):
        """Test string too long validation."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationUtils.validate_string(
                "This is a very long string",
                "test_field",
                max_length=10
            )
        assert "cannot exceed 10 characters" in str(exc_info.value.detail)
    
    def test_validate_string_dangerous_content(self):
        """Test string with dangerous content."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationUtils.validate_string(
                "<script>alert('xss')</script>",
                "test_field"
            )
        assert "dangerous content" in str(exc_info.value.detail)
    
    def test_validate_integer_valid(self):
        """Test valid integer validation."""
        result = ValidationUtils.validate_integer(42, "test_field")
        assert result == 42
    
    def test_validate_integer_invalid(self):
        """Test invalid integer validation."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationUtils.validate_integer("not_a_number", "test_field")
        assert "must be a valid integer" in str(exc_info.value.detail)
    
    def test_validate_integer_out_of_range(self):
        """Test integer out of range validation."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationUtils.validate_integer(150, "test_field", max_value=100)
        assert "cannot exceed 100" in str(exc_info.value.detail)
    
    def test_validate_coordinates_valid(self):
        """Test valid coordinates validation."""
        lat, lng = ValidationUtils.validate_coordinates(25.2048, 55.2708)
        assert float(lat) == 25.2048
        assert float(lng) == 55.2708
    
    def test_validate_coordinates_invalid_range(self):
        """Test coordinates with invalid range."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationUtils.validate_coordinates(91.0, 55.2708)
        assert "latitude" in str(exc_info.value.detail)
    
    def test_validate_coordinates_partial(self):
        """Test coordinates with only one value provided."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationUtils.validate_coordinates(25.2048, None)
        assert "both" in str(exc_info.value.detail).lower()
    
    def test_validate_pagination_valid(self):
        """Test valid pagination validation."""
        page, page_size = ValidationUtils.validate_pagination(1, 20)
        assert page == 1
        assert page_size == 20
    
    def test_validate_pagination_invalid_page(self):
        """Test invalid page number."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationUtils.validate_pagination(0, 20)
        assert "must be at least 1" in str(exc_info.value.detail)
    
    def test_validate_pagination_invalid_page_size(self):
        """Test invalid page size."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationUtils.validate_pagination(1, 150)
        assert "cannot exceed 100" in str(exc_info.value.detail)


class TestBusinessRuleValidator:
    """Test business rule validation."""
    
    def test_validate_property_ownership_owner(self):
        """Test property ownership validation for owner."""
        # Should not raise exception for owner
        BusinessRuleValidator.validate_property_ownership(
            "user123", "user123", "agent"
        )
    
    def test_validate_property_ownership_admin(self):
        """Test property ownership validation for admin."""
        # Should not raise exception for admin
        BusinessRuleValidator.validate_property_ownership(
            "user123", "admin456", "admin"
        )
    
    def test_validate_property_ownership_unauthorized(self):
        """Test property ownership validation for unauthorized user."""
        with pytest.raises(ValidationError) as exc_info:
            BusinessRuleValidator.validate_property_ownership(
                "user123", "other456", "agent"
            )
        assert "permission" in str(exc_info.value.detail)
    
    def test_validate_image_upload_limits_valid(self):
        """Test valid image upload limits."""
        # Should not raise exception
        BusinessRuleValidator.validate_image_upload_limits(5, 20)
    
    def test_validate_image_upload_limits_exceeded(self):
        """Test image upload limits exceeded."""
        with pytest.raises(ValidationError) as exc_info:
            BusinessRuleValidator.validate_image_upload_limits(20, 20)
        assert "Maximum" in str(exc_info.value.detail)
    
    def test_validate_price_range_valid(self):
        """Test valid price range."""
        from decimal import Decimal
        # Should not raise exception
        BusinessRuleValidator.validate_price_range(
            Decimal('1000'), Decimal('5000')
        )
    
    def test_validate_price_range_invalid(self):
        """Test invalid price range."""
        from decimal import Decimal
        with pytest.raises(ValidationError) as exc_info:
            BusinessRuleValidator.validate_price_range(
                Decimal('5000'), Decimal('1000')
            )
        assert "cannot be greater than" in str(exc_info.value.detail)


class TestValidationMiddleware:
    """Test validation middleware functionality."""
    
    @pytest.fixture
    def test_app(self):
        """Create test FastAPI app with middleware."""
        test_app = FastAPI()
        test_app.add_middleware(ValidationMiddleware, enable_request_logging=False)
        test_app.add_middleware(RequestValidationMiddleware)
        
        @test_app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        @test_app.post("/test")
        async def test_post_endpoint(data: dict):
            return {"message": "success", "data": data}
        
        return test_app
    
    def test_request_size_validation(self, test_app):
        """Test request size validation."""
        client = TestClient(test_app)
        
        # Test with large content-length header
        response = client.post(
            "/test",
            json={"test": "data"},
            headers={"content-length": str(20 * 1024 * 1024)}  # 20MB
        )
        
        assert response.status_code == 400
        assert "exceeds maximum allowed size" in response.json()["error"]["message"]
    
    def test_query_parameter_validation(self, test_app):
        """Test query parameter validation."""
        client = TestClient(test_app)
        
        # Test with invalid page parameter
        response = client.get("/test?page=invalid")
        assert response.status_code == 400
        assert "must be a valid integer" in response.json()["error"]["message"]
    
    def test_uuid_path_parameter_validation(self, test_app):
        """Test UUID path parameter validation."""
        @test_app.get("/test/{item_id}")
        async def test_uuid_endpoint(item_id: str):
            return {"item_id": item_id}
        
        client = TestClient(test_app)
        
        # Test with invalid UUID
        response = client.get("/test/invalid-uuid")
        assert response.status_code == 400
        assert "Invalid UUID format" in response.json()["error"]["message"]


class TestAPIErrorResponses:
    """Test API error responses through actual endpoints."""
    
    def test_validation_error_response_format(self):
        """Test validation error response format."""
        client = TestClient(app)
        
        # Test with invalid property data
        response = client.post(
            "/api/v1/properties",
            json={
                "title": "",  # Too short
                "price": -100,  # Negative price
                "bedrooms": 100  # Too many bedrooms
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        # Should get validation error
        assert response.status_code in [401, 422]  # Either auth error or validation error
        
        response_data = response.json()
        assert "error" in response_data
        assert "code" in response_data["error"]
        assert "message" in response_data["error"]
        assert "timestamp" in response_data["error"]
    
    def test_authentication_error_response_format(self):
        """Test authentication error response format."""
        client = TestClient(app)
        
        # Test without authentication
        response = client.post("/api/v1/properties", json={})
        
        assert response.status_code == 401
        response_data = response.json()
        assert response_data["error"]["code"] == "UNAUTHORIZED"
        assert "authentication" in response_data["error"]["message"].lower()
    
    def test_not_found_error_response_format(self):
        """Test not found error response format."""
        client = TestClient(app)
        
        # Test with non-existent property
        response = client.get("/api/v1/properties/123e4567-e89b-12d3-a456-426614174000")
        
        # Should get not found error (or auth error if not authenticated)
        assert response.status_code in [401, 404]
        
        if response.status_code == 404:
            response_data = response.json()
            assert response_data["error"]["code"] == "NOT_FOUND"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])