"""
Custom exception classes for the Property Listing API.
Provides structured error handling with appropriate HTTP status codes.
"""

from typing import Any, Dict, Optional, List
from fastapi import HTTPException, status


class APIException(HTTPException):
    """Base API exception class."""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code


class ValidationError(APIException):
    """Validation error exception."""
    
    def __init__(
        self,
        detail: str,
        field_errors: Optional[List[Dict[str, str]]] = None
    ):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="VALIDATION_ERROR"
        )
        self.field_errors = field_errors or []


class NotFoundError(APIException):
    """Resource not found exception."""
    
    def __init__(self, resource: str, resource_id: Optional[str] = None):
        detail = f"{resource} not found"
        if resource_id:
            detail += f" with ID: {resource_id}"
        
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code="NOT_FOUND"
        )


class UnauthorizedError(APIException):
    """Authentication required exception."""
    
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="UNAUTHORIZED",
            headers={"WWW-Authenticate": "Bearer"}
        )


class ForbiddenError(APIException):
    """Access forbidden exception."""
    
    def __init__(self, detail: str = "Access forbidden"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="FORBIDDEN"
        )


class ConflictError(APIException):
    """Resource conflict exception."""
    
    def __init__(self, detail: str, resource: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="CONFLICT"
        )


class BadRequestError(APIException):
    """Bad request exception."""
    
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="BAD_REQUEST"
        )


class InternalServerError(APIException):
    """Internal server error exception."""
    
    def __init__(self, detail: str = "Internal server error"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="INTERNAL_SERVER_ERROR"
        )


# Authentication specific exceptions
class InvalidCredentialsError(UnauthorizedError):
    """Invalid login credentials exception."""
    
    def __init__(self, detail: str = "Invalid email or password"):
        super().__init__(detail)


class TokenExpiredError(UnauthorizedError):
    """JWT token expired exception."""
    
    def __init__(self, detail: str = "Token has expired"):
        super().__init__(detail)


class InvalidTokenError(UnauthorizedError):
    """Invalid JWT token exception."""
    
    def __init__(self, detail: str = "Invalid token"):
        super().__init__(detail)


class InactiveUserError(ForbiddenError):
    """Inactive user account exception."""
    
    def __init__(self, detail: str = "User account is inactive"):
        super().__init__(detail)


class InsufficientPermissionsError(ForbiddenError):
    """Insufficient permissions exception."""
    
    def __init__(self, action: str):
        super().__init__(f"Insufficient permissions to {action}")


# Property specific exceptions
class PropertyNotFoundError(NotFoundError):
    """Property not found exception."""
    
    def __init__(self, property_id: str):
        super().__init__("Property", property_id)


class PropertyOwnershipError(ForbiddenError):
    """Property ownership violation exception."""
    
    def __init__(self, detail: str = "You don't own this property"):
        super().__init__(detail)


class PropertyStatusError(BadRequestError):
    """Property status error exception."""
    
    def __init__(self, detail: str):
        super().__init__(detail)


# Business rule exceptions
class BusinessRuleViolationError(BadRequestError):
    """Business rule violation exception."""
    
    def __init__(self, rule: str, detail: Optional[str] = None):
        message = f"Business rule violation: {rule}"
        if detail:
            message += f" - {detail}"
        super().__init__(message)


class ResourceLimitExceededError(BadRequestError):
    """Resource limit exceeded exception."""
    
    def __init__(self, resource: str, limit: int):
        super().__init__(f"{resource} limit exceeded (maximum: {limit})")


class DuplicateResourceError(ConflictError):
    """Duplicate resource exception."""
    
    def __init__(self, resource: str, identifier: str):
        super().__init__(f"{resource} with identifier '{identifier}' already exists")


# File upload exceptions
class FileUploadError(BadRequestError):
    """File upload error exception."""
    
    def __init__(self, detail: str):
        super().__init__(f"File upload error: {detail}")


class UnsupportedFileTypeError(BadRequestError):
    """Unsupported file type exception."""
    
    def __init__(self, file_type: str, supported_types: List[str]):
        supported = ", ".join(supported_types)
        super().__init__(f"Unsupported file type '{file_type}'. Supported types: {supported}")


class FileSizeExceededError(BadRequestError):
    """File size exceeded exception."""
    
    def __init__(self, size: int, max_size: int):
        super().__init__(f"File size {size} bytes exceeds maximum allowed size {max_size} bytes")


# Rate limiting exceptions
class RateLimitExceededError(APIException):
    """Rate limit exceeded exception."""
    
    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            error_code="RATE_LIMIT_EXCEEDED",
            headers={"Retry-After": str(retry_after)}
        )


# Service unavailable exceptions
class ServiceUnavailableError(APIException):
    """Service unavailable exception."""
    
    def __init__(self, detail: str = "Service temporarily unavailable"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code="SERVICE_UNAVAILABLE"
        )