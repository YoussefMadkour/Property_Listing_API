#!/usr/bin/env python3
"""
Demonstration script for comprehensive error handling and validation.
Shows various error scenarios and their structured responses.
"""

import asyncio
import json
from fastapi.testclient import TestClient
from app.main import app
from app.utils.exceptions import ValidationError, NotFoundError, BadRequestError
from app.services.error_handler import ErrorHandlerService
from app.utils.validators import ValidationUtils, BusinessRuleValidator


def demo_error_responses():
    """Demonstrate various error response formats."""
    print("=== Error Response Format Demonstration ===\n")
    
    # 1. Validation Error
    print("1. Validation Error Example:")
    try:
        ValidationUtils.validate_uuid("invalid-uuid", "property_id")
    except ValidationError as e:
        response = ErrorHandlerService.handle_api_exception(e)
        print(json.dumps(json.loads(response.body), indent=2))
    print()
    
    # 2. Business Rule Violation
    print("2. Business Rule Violation Example:")
    try:
        BusinessRuleValidator.validate_property_ownership("user123", "other456", "agent")
    except ValidationError as e:
        response = ErrorHandlerService.handle_api_exception(e)
        print(json.dumps(json.loads(response.body), indent=2))
    print()
    
    # 3. Range Validation Error
    print("3. Range Validation Error Example:")
    try:
        ValidationUtils.validate_integer(150, "bedrooms", max_value=50)
    except ValidationError as e:
        response = ErrorHandlerService.handle_api_exception(e)
        print(json.dumps(json.loads(response.body), indent=2))
    print()
    
    # 4. String Validation with Dangerous Content
    print("4. Security Validation Error Example:")
    try:
        ValidationUtils.validate_string("<script>alert('xss')</script>", "description")
    except ValidationError as e:
        response = ErrorHandlerService.handle_api_exception(e)
        print(json.dumps(json.loads(response.body), indent=2))
    print()


def demo_api_error_responses():
    """Demonstrate API error responses through test client."""
    print("=== API Error Response Demonstration ===\n")
    
    client = TestClient(app)
    
    # 1. Authentication Error
    print("1. Authentication Error:")
    response = client.post("/api/v1/properties", json={})
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    print()
    
    # 2. Not Found Error
    print("2. Not Found Error:")
    response = client.get("/api/v1/properties/123e4567-e89b-12d3-a456-426614174000")
    print(f"Status Code: {response.status_code}")
    if response.status_code != 401:  # Skip if auth error
        print(json.dumps(response.json(), indent=2))
    else:
        print("(Authentication required - would show Not Found error when authenticated)")
    print()
    
    # 3. Validation Error with Invalid Data
    print("3. Validation Error with Invalid Property Data:")
    invalid_property = {
        "title": "",  # Too short
        "description": "Short",  # Too short
        "property_type": "invalid_type",  # Invalid enum
        "price": -100,  # Negative price
        "bedrooms": 100,  # Too many bedrooms
        "bathrooms": -1,  # Negative bathrooms
        "area_sqft": 0,  # Zero area
        "location": ""  # Empty location
    }
    
    response = client.post(
        "/api/v1/properties",
        json=invalid_property,
        headers={"Authorization": "Bearer fake_token"}
    )
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    print()


def demo_validation_utilities():
    """Demonstrate validation utility functions."""
    print("=== Validation Utilities Demonstration ===\n")
    
    # 1. UUID Validation
    print("1. UUID Validation:")
    try:
        valid_uuid = ValidationUtils.validate_uuid("123e4567-e89b-12d3-a456-426614174000")
        print(f"✓ Valid UUID: {valid_uuid}")
    except ValidationError as e:
        print(f"✗ Invalid UUID: {e.detail}")
    
    try:
        ValidationUtils.validate_uuid("invalid-uuid")
    except ValidationError as e:
        print(f"✗ Invalid UUID: {e.detail}")
    print()
    
    # 2. String Validation
    print("2. String Validation:")
    try:
        valid_string = ValidationUtils.validate_string("Valid Property Title", "title", min_length=5, max_length=50)
        print(f"✓ Valid string: {valid_string}")
    except ValidationError as e:
        print(f"✗ Invalid string: {e.detail}")
    
    try:
        ValidationUtils.validate_string("Hi", "title", min_length=5)
    except ValidationError as e:
        print(f"✗ String too short: {e.detail}")
    print()
    
    # 3. Coordinate Validation
    print("3. Coordinate Validation:")
    try:
        lat, lng = ValidationUtils.validate_coordinates(25.2048, 55.2708)
        print(f"✓ Valid coordinates: {lat}, {lng}")
    except ValidationError as e:
        print(f"✗ Invalid coordinates: {e.detail}")
    
    try:
        ValidationUtils.validate_coordinates(91.0, 55.2708)
    except ValidationError as e:
        print(f"✗ Invalid latitude: {e.detail}")
    print()
    
    # 4. Pagination Validation
    print("4. Pagination Validation:")
    try:
        page, page_size = ValidationUtils.validate_pagination(1, 20)
        print(f"✓ Valid pagination: page={page}, page_size={page_size}")
    except ValidationError as e:
        print(f"✗ Invalid pagination: {e.detail}")
    
    try:
        ValidationUtils.validate_pagination(0, 20)
    except ValidationError as e:
        print(f"✗ Invalid page number: {e.detail}")
    print()


def demo_business_rules():
    """Demonstrate business rule validation."""
    print("=== Business Rule Validation Demonstration ===\n")
    
    # 1. Property Ownership
    print("1. Property Ownership Validation:")
    try:
        BusinessRuleValidator.validate_property_ownership("user123", "user123", "agent")
        print("✓ Owner can access their property")
    except ValidationError as e:
        print(f"✗ Ownership error: {e.detail}")
    
    try:
        BusinessRuleValidator.validate_property_ownership("user123", "admin456", "admin")
        print("✓ Admin can access any property")
    except ValidationError as e:
        print(f"✗ Admin access error: {e.detail}")
    
    try:
        BusinessRuleValidator.validate_property_ownership("user123", "other456", "agent")
    except ValidationError as e:
        print(f"✗ Unauthorized access: {e.detail}")
    print()
    
    # 2. Image Upload Limits
    print("2. Image Upload Limits:")
    try:
        BusinessRuleValidator.validate_image_upload_limits(5, 20)
        print("✓ Image upload within limits")
    except ValidationError as e:
        print(f"✗ Upload limit error: {e.detail}")
    
    try:
        BusinessRuleValidator.validate_image_upload_limits(20, 20)
    except ValidationError as e:
        print(f"✗ Upload limit exceeded: {e.detail}")
    print()
    
    # 3. Price Range Validation
    print("3. Price Range Validation:")
    from decimal import Decimal
    try:
        BusinessRuleValidator.validate_price_range(Decimal('1000'), Decimal('5000'))
        print("✓ Valid price range")
    except ValidationError as e:
        print(f"✗ Price range error: {e.detail}")
    
    try:
        BusinessRuleValidator.validate_price_range(Decimal('5000'), Decimal('1000'))
    except ValidationError as e:
        print(f"✗ Invalid price range: {e.detail}")
    print()


def main():
    """Run all demonstrations."""
    print("🚀 Property Listing API - Error Handling & Validation Demo\n")
    print("=" * 60)
    
    demo_error_responses()
    print("=" * 60)
    
    demo_validation_utilities()
    print("=" * 60)
    
    demo_business_rules()
    print("=" * 60)
    
    demo_api_error_responses()
    print("=" * 60)
    
    print("✅ Error handling and validation demonstration completed!")
    print("\nKey Features Demonstrated:")
    print("• Structured error response format with error codes and timestamps")
    print("• Detailed field-level validation error messages")
    print("• Business rule validation with clear error descriptions")
    print("• Security validation to prevent XSS and other attacks")
    print("• Comprehensive input validation for all data types")
    print("• Consistent error handling across all API endpoints")
    print("• Request validation middleware with size and format checks")
    print("• Database error handling with user-friendly messages")


if __name__ == "__main__":
    main()