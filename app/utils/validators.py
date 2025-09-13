"""
Comprehensive validation utilities for the Property Listing API.
Provides custom validators, sanitizers, and validation helpers.
"""

import re
import uuid
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal, InvalidOperation
from datetime import datetime
from email_validator import validate_email, EmailNotValidError
from pydantic import ValidationError as PydanticValidationError

from app.utils.exceptions import ValidationError, BadRequestError


class ValidationUtils:
    """
    Utility class for common validation operations.
    Provides reusable validation methods for various data types.
    """
    
    # Regular expressions for validation
    UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    PHONE_PATTERN = re.compile(r'^\+?[1-9]\d{1,14}$')
    SLUG_PATTERN = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
    
    # Dangerous characters for XSS prevention
    DANGEROUS_CHARS = ['<', '>', '"', "'", '&', 'javascript:', 'data:', 'vbscript:']
    
    @staticmethod
    def validate_uuid(value: Any, field_name: str = "id") -> str:
        """
        Validate UUID format.
        
        Args:
            value: Value to validate
            field_name: Name of the field for error messages
            
        Returns:
            Valid UUID string
            
        Raises:
            ValidationError: If UUID is invalid
        """
        if not value:
            raise ValidationError(f"{field_name} is required")
        
        uuid_str = str(value).strip()
        
        if not ValidationUtils.UUID_PATTERN.match(uuid_str):
            raise ValidationError(f"Invalid UUID format for {field_name}")
        
        try:
            # Validate using uuid module
            uuid.UUID(uuid_str)
            return uuid_str
        except ValueError:
            raise ValidationError(f"Invalid UUID format for {field_name}")
    
    @staticmethod
    def validate_email_address(email: Any, field_name: str = "email") -> str:
        """
        Validate email address format.
        
        Args:
            email: Email to validate
            field_name: Name of the field for error messages
            
        Returns:
            Valid email string
            
        Raises:
            ValidationError: If email is invalid
        """
        if not email:
            raise ValidationError(f"{field_name} is required")
        
        email_str = str(email).strip().lower()
        
        try:
            # Use email-validator library for comprehensive validation
            valid_email = validate_email(email_str)
            return valid_email.email
        except EmailNotValidError as e:
            raise ValidationError(f"Invalid email format for {field_name}: {str(e)}")
    
    @staticmethod
    def validate_string(
        value: Any,
        field_name: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        allow_empty: bool = False,
        pattern: Optional[re.Pattern] = None,
        sanitize: bool = True
    ) -> str:
        """
        Validate string value with comprehensive checks.
        
        Args:
            value: Value to validate
            field_name: Name of the field for error messages
            min_length: Minimum string length
            max_length: Maximum string length
            allow_empty: Whether to allow empty strings
            pattern: Regex pattern to match
            sanitize: Whether to sanitize the string
            
        Returns:
            Valid string
            
        Raises:
            ValidationError: If string is invalid
        """
        if value is None:
            if not allow_empty:
                raise ValidationError(f"{field_name} is required")
            return ""
        
        str_value = str(value).strip()
        
        # Check for empty string
        if not str_value and not allow_empty:
            raise ValidationError(f"{field_name} cannot be empty")
        
        # Check length constraints
        if min_length is not None and len(str_value) < min_length:
            raise ValidationError(f"{field_name} must be at least {min_length} characters long")
        
        if max_length is not None and len(str_value) > max_length:
            raise ValidationError(f"{field_name} cannot exceed {max_length} characters")
        
        # Check for dangerous characters if sanitizing
        if sanitize:
            str_value = ValidationUtils.sanitize_string(str_value, field_name)
        
        # Check pattern if provided
        if pattern and not pattern.match(str_value):
            raise ValidationError(f"{field_name} format is invalid")
        
        return str_value
    
    @staticmethod
    def validate_integer(
        value: Any,
        field_name: str,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None
    ) -> int:
        """
        Validate integer value.
        
        Args:
            value: Value to validate
            field_name: Name of the field for error messages
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Returns:
            Valid integer
            
        Raises:
            ValidationError: If integer is invalid
        """
        if value is None:
            raise ValidationError(f"{field_name} is required")
        
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be a valid integer")
        
        if min_value is not None and int_value < min_value:
            raise ValidationError(f"{field_name} must be at least {min_value}")
        
        if max_value is not None and int_value > max_value:
            raise ValidationError(f"{field_name} cannot exceed {max_value}")
        
        return int_value
    
    @staticmethod
    def validate_decimal(
        value: Any,
        field_name: str,
        min_value: Optional[Decimal] = None,
        max_value: Optional[Decimal] = None,
        max_digits: Optional[int] = None,
        decimal_places: Optional[int] = None
    ) -> Decimal:
        """
        Validate decimal value.
        
        Args:
            value: Value to validate
            field_name: Name of the field for error messages
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            max_digits: Maximum total digits
            decimal_places: Maximum decimal places
            
        Returns:
            Valid Decimal
            
        Raises:
            ValidationError: If decimal is invalid
        """
        if value is None:
            raise ValidationError(f"{field_name} is required")
        
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            raise ValidationError(f"{field_name} must be a valid decimal number")
        
        if min_value is not None and decimal_value < min_value:
            raise ValidationError(f"{field_name} must be at least {min_value}")
        
        if max_value is not None and decimal_value > max_value:
            raise ValidationError(f"{field_name} cannot exceed {max_value}")
        
        # Check digit constraints
        if max_digits is not None or decimal_places is not None:
            sign, digits, exponent = decimal_value.as_tuple()
            
            if max_digits is not None and len(digits) > max_digits:
                raise ValidationError(f"{field_name} cannot have more than {max_digits} total digits")
            
            if decimal_places is not None and exponent < -decimal_places:
                raise ValidationError(f"{field_name} cannot have more than {decimal_places} decimal places")
        
        return decimal_value
    
    @staticmethod
    def validate_coordinates(
        latitude: Any,
        longitude: Any,
        field_prefix: str = "coordinate"
    ) -> tuple[Optional[Decimal], Optional[Decimal]]:
        """
        Validate latitude and longitude coordinates.
        
        Args:
            latitude: Latitude value
            longitude: Longitude value
            field_prefix: Prefix for field names in error messages
            
        Returns:
            Tuple of validated coordinates
            
        Raises:
            ValidationError: If coordinates are invalid
        """
        # Both must be provided or both must be None
        if (latitude is None) != (longitude is None):
            raise ValidationError(f"Both {field_prefix} latitude and longitude must be provided together")
        
        if latitude is None and longitude is None:
            return None, None
        
        # Validate latitude
        lat_decimal = ValidationUtils.validate_decimal(
            latitude,
            f"{field_prefix} latitude",
            min_value=Decimal('-90'),
            max_value=Decimal('90')
        )
        
        # Validate longitude
        lng_decimal = ValidationUtils.validate_decimal(
            longitude,
            f"{field_prefix} longitude",
            min_value=Decimal('-180'),
            max_value=Decimal('180')
        )
        
        return lat_decimal, lng_decimal
    
    @staticmethod
    def validate_phone_number(phone: Any, field_name: str = "phone") -> str:
        """
        Validate phone number format.
        
        Args:
            phone: Phone number to validate
            field_name: Name of the field for error messages
            
        Returns:
            Valid phone number string
            
        Raises:
            ValidationError: If phone number is invalid
        """
        if not phone:
            raise ValidationError(f"{field_name} is required")
        
        phone_str = str(phone).strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        if not ValidationUtils.PHONE_PATTERN.match(phone_str):
            raise ValidationError(f"Invalid phone number format for {field_name}")
        
        return phone_str
    
    @staticmethod
    def sanitize_string(value: str, field_name: str) -> str:
        """
        Sanitize string to prevent XSS and other security issues.
        
        Args:
            value: String to sanitize
            field_name: Name of the field for error messages
            
        Returns:
            Sanitized string
            
        Raises:
            ValidationError: If string contains dangerous content
        """
        if not value:
            return value
        
        # Check for dangerous characters
        lower_value = value.lower()
        for dangerous_char in ValidationUtils.DANGEROUS_CHARS:
            if dangerous_char in lower_value:
                raise ValidationError(f"{field_name} contains potentially dangerous content")
        
        # Basic HTML entity encoding for safety
        sanitized = (value
                    .replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;')
                    .replace("'", '&#x27;'))
        
        return sanitized
    
    @staticmethod
    def validate_pagination(
        page: Any,
        page_size: Any,
        max_page_size: int = 100
    ) -> tuple[int, int]:
        """
        Validate pagination parameters.
        
        Args:
            page: Page number
            page_size: Page size
            max_page_size: Maximum allowed page size
            
        Returns:
            Tuple of validated page and page_size
            
        Raises:
            ValidationError: If pagination parameters are invalid
        """
        validated_page = ValidationUtils.validate_integer(
            page,
            "page",
            min_value=1
        )
        
        validated_page_size = ValidationUtils.validate_integer(
            page_size,
            "page_size",
            min_value=1,
            max_value=max_page_size
        )
        
        return validated_page, validated_page_size
    
    @staticmethod
    def validate_sort_parameters(
        sort_by: Any,
        sort_order: Any,
        allowed_fields: List[str]
    ) -> tuple[str, str]:
        """
        Validate sorting parameters.
        
        Args:
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            allowed_fields: List of allowed sort fields
            
        Returns:
            Tuple of validated sort_by and sort_order
            
        Raises:
            ValidationError: If sort parameters are invalid
        """
        if sort_by and sort_by not in allowed_fields:
            raise ValidationError(f"Invalid sort field. Allowed fields: {', '.join(allowed_fields)}")
        
        validated_sort_by = sort_by or allowed_fields[0]
        
        if sort_order and sort_order.lower() not in ['asc', 'desc']:
            raise ValidationError("Sort order must be 'asc' or 'desc'")
        
        validated_sort_order = sort_order.lower() if sort_order else 'desc'
        
        return validated_sort_by, validated_sort_order


class BusinessRuleValidator:
    """
    Validator for business rules and complex validation logic.
    Handles domain-specific validation requirements.
    """
    
    @staticmethod
    def validate_property_ownership(
        property_agent_id: str,
        current_user_id: str,
        current_user_role: str
    ) -> None:
        """
        Validate property ownership for operations.
        
        Args:
            property_agent_id: ID of the property's agent
            current_user_id: ID of the current user
            current_user_role: Role of the current user
            
        Raises:
            ValidationError: If user doesn't have permission
        """
        if current_user_role == "admin":
            return  # Admins can access all properties
        
        if property_agent_id != current_user_id:
            raise ValidationError("You don't have permission to access this property")
    
    @staticmethod
    def validate_property_status_change(
        current_status: bool,
        new_status: bool,
        user_role: str
    ) -> None:
        """
        Validate property status changes.
        
        Args:
            current_status: Current active status
            new_status: New active status
            user_role: User role
            
        Raises:
            ValidationError: If status change is not allowed
        """
        # Only allow deactivation if property is currently active
        if current_status and not new_status:
            return  # Deactivation is always allowed
        
        # Reactivation might have business rules
        if not current_status and new_status:
            # Add any business rules for reactivation
            pass
    
    @staticmethod
    def validate_image_upload_limits(
        current_image_count: int,
        max_images_per_property: int = 20
    ) -> None:
        """
        Validate image upload limits.
        
        Args:
            current_image_count: Current number of images
            max_images_per_property: Maximum allowed images
            
        Raises:
            ValidationError: If limit would be exceeded
        """
        if current_image_count >= max_images_per_property:
            raise ValidationError(f"Maximum {max_images_per_property} images allowed per property")
    
    @staticmethod
    def validate_price_range(
        min_price: Optional[Decimal],
        max_price: Optional[Decimal]
    ) -> None:
        """
        Validate price range parameters.
        
        Args:
            min_price: Minimum price
            max_price: Maximum price
            
        Raises:
            ValidationError: If price range is invalid
        """
        if min_price is not None and max_price is not None:
            if min_price > max_price:
                raise ValidationError("Minimum price cannot be greater than maximum price")
            
            # Check for reasonable price ranges
            if max_price - min_price > Decimal('1000000'):
                raise ValidationError("Price range is too wide (maximum range: 1,000,000)")


def create_validation_error_response(
    errors: List[Dict[str, Any]],
    message: str = "Validation failed"
) -> ValidationError:
    """
    Create a structured validation error response.
    
    Args:
        errors: List of field errors
        message: Main error message
        
    Returns:
        ValidationError instance
    """
    return ValidationError(
        detail=message,
        field_errors=errors
    )


def handle_pydantic_validation_error(exc: PydanticValidationError) -> ValidationError:
    """
    Convert Pydantic validation error to custom ValidationError.
    
    Args:
        exc: Pydantic validation error
        
    Returns:
        Custom ValidationError instance
    """
    field_errors = []
    
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        field_errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })
    
    return ValidationError(
        detail="Request validation failed",
        field_errors=field_errors
    )


# Validation decorators
def validate_request_data(schema_class):
    """
    Decorator to validate request data using Pydantic schema.
    
    Args:
        schema_class: Pydantic schema class for validation
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                # Validate request data
                if 'data' in kwargs:
                    validated_data = schema_class(**kwargs['data'])
                    kwargs['data'] = validated_data
                return func(*args, **kwargs)
            except PydanticValidationError as e:
                raise handle_pydantic_validation_error(e)
        return wrapper
    return decorator