"""
Error response schemas for API documentation and consistent error formatting.
Provides standardized error response models for OpenAPI documentation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime


class ErrorDetail(BaseModel):
    """Schema for individual error detail."""
    
    field: Optional[str] = Field(
        None,
        description="Field name that caused the error",
        example="email"
    )
    
    message: str = Field(
        ...,
        description="Human-readable error message",
        example="Invalid email format"
    )
    
    type: Optional[str] = Field(
        None,
        description="Error type identifier",
        example="value_error.email"
    )
    
    input: Optional[Any] = Field(
        None,
        description="Input value that caused the error",
        example="invalid-email"
    )
    
    rule: Optional[str] = Field(
        None,
        description="Business rule that was violated",
        example="unique_email"
    )


class ErrorResponse(BaseModel):
    """Schema for standardized error responses."""
    
    code: str = Field(
        ...,
        description="Error code identifier",
        example="VALIDATION_ERROR"
    )
    
    message: str = Field(
        ...,
        description="Human-readable error message",
        example="Request validation failed"
    )
    
    timestamp: str = Field(
        ...,
        description="Error timestamp in ISO format",
        example="2023-01-01T00:00:00Z"
    )
    
    request_id: Optional[str] = Field(
        None,
        description="Unique request identifier for tracking",
        example="abc12345"
    )
    
    details: Optional[List[ErrorDetail]] = Field(
        None,
        description="Detailed error information for validation errors"
    )


class APIErrorResponse(BaseModel):
    """Schema for API error response wrapper."""
    
    error: ErrorResponse = Field(
        ...,
        description="Error information"
    )


# Common error response examples for documentation
COMMON_ERROR_RESPONSES = {
    400: {
        "description": "Bad Request - Invalid request parameters",
        "model": APIErrorResponse,
        "content": {
            "application/json": {
                "examples": {
                    "bad_request": {
                        "summary": "Bad Request Example",
                        "value": {
                            "error": {
                                "code": "BAD_REQUEST",
                                "message": "Invalid request parameters",
                                "timestamp": "2023-01-01T00:00:00Z",
                                "request_id": "abc12345"
                            }
                        }
                    },
                    "business_rule_violation": {
                        "summary": "Business Rule Violation",
                        "value": {
                            "error": {
                                "code": "BUSINESS_RULE_VIOLATION",
                                "message": "Business rule violation: unique_email",
                                "timestamp": "2023-01-01T00:00:00Z",
                                "request_id": "abc12345",
                                "details": [
                                    {
                                        "field": "email",
                                        "message": "Email address already exists",
                                        "rule": "unique_email"
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }
    },
    401: {
        "description": "Unauthorized - Authentication required",
        "model": APIErrorResponse,
        "content": {
            "application/json": {
                "examples": {
                    "unauthorized": {
                        "summary": "Authentication Required",
                        "value": {
                            "error": {
                                "code": "UNAUTHORIZED",
                                "message": "Authentication required",
                                "timestamp": "2023-01-01T00:00:00Z",
                                "request_id": "abc12345"
                            }
                        }
                    },
                    "invalid_token": {
                        "summary": "Invalid Token",
                        "value": {
                            "error": {
                                "code": "UNAUTHORIZED",
                                "message": "Invalid token",
                                "timestamp": "2023-01-01T00:00:00Z",
                                "request_id": "abc12345"
                            }
                        }
                    },
                    "token_expired": {
                        "summary": "Token Expired",
                        "value": {
                            "error": {
                                "code": "UNAUTHORIZED",
                                "message": "Token has expired",
                                "timestamp": "2023-01-01T00:00:00Z",
                                "request_id": "abc12345"
                            }
                        }
                    }
                }
            }
        }
    },
    403: {
        "description": "Forbidden - Access denied",
        "model": APIErrorResponse,
        "content": {
            "application/json": {
                "examples": {
                    "forbidden": {
                        "summary": "Access Forbidden",
                        "value": {
                            "error": {
                                "code": "FORBIDDEN",
                                "message": "Access forbidden",
                                "timestamp": "2023-01-01T00:00:00Z",
                                "request_id": "abc12345"
                            }
                        }
                    },
                    "insufficient_permissions": {
                        "summary": "Insufficient Permissions",
                        "value": {
                            "error": {
                                "code": "FORBIDDEN",
                                "message": "Insufficient permissions to delete property",
                                "timestamp": "2023-01-01T00:00:00Z",
                                "request_id": "abc12345"
                            }
                        }
                    },
                    "property_ownership": {
                        "summary": "Property Ownership Error",
                        "value": {
                            "error": {
                                "code": "FORBIDDEN",
                                "message": "You don't own this property",
                                "timestamp": "2023-01-01T00:00:00Z",
                                "request_id": "abc12345"
                            }
                        }
                    }
                }
            }
        }
    },
    404: {
        "description": "Not Found - Resource not found",
        "model": APIErrorResponse,
        "content": {
            "application/json": {
                "examples": {
                    "not_found": {
                        "summary": "Resource Not Found",
                        "value": {
                            "error": {
                                "code": "NOT_FOUND",
                                "message": "Property not found with ID: 123e4567-e89b-12d3-a456-426614174000",
                                "timestamp": "2023-01-01T00:00:00Z",
                                "request_id": "abc12345"
                            }
                        }
                    },
                    "user_not_found": {
                        "summary": "User Not Found",
                        "value": {
                            "error": {
                                "code": "NOT_FOUND",
                                "message": "User not found",
                                "timestamp": "2023-01-01T00:00:00Z",
                                "request_id": "abc12345"
                            }
                        }
                    }
                }
            }
        }
    },
    409: {
        "description": "Conflict - Resource conflict",
        "model": APIErrorResponse,
        "content": {
            "application/json": {
                "examples": {
                    "conflict": {
                        "summary": "Resource Conflict",
                        "value": {
                            "error": {
                                "code": "CONFLICT",
                                "message": "User with email 'user@example.com' already exists",
                                "timestamp": "2023-01-01T00:00:00Z",
                                "request_id": "abc12345"
                            }
                        }
                    },
                    "integrity_error": {
                        "summary": "Database Integrity Error",
                        "value": {
                            "error": {
                                "code": "INTEGRITY_ERROR",
                                "message": "Constraint violation: Duplicate value for unique field",
                                "timestamp": "2023-01-01T00:00:00Z",
                                "request_id": "abc12345"
                            }
                        }
                    }
                }
            }
        }
    },
    422: {
        "description": "Unprocessable Entity - Validation error",
        "model": APIErrorResponse,
        "content": {
            "application/json": {
                "examples": {
                    "validation_error": {
                        "summary": "Validation Error",
                        "value": {
                            "error": {
                                "code": "VALIDATION_ERROR",
                                "message": "Request validation failed",
                                "timestamp": "2023-01-01T00:00:00Z",
                                "request_id": "abc12345",
                                "details": [
                                    {
                                        "field": "email",
                                        "message": "Invalid email format",
                                        "type": "value_error.email",
                                        "input": "invalid-email"
                                    },
                                    {
                                        "field": "price",
                                        "message": "Price must be greater than 0",
                                        "type": "value_error.number.not_gt",
                                        "input": -100
                                    }
                                ]
                            }
                        }
                    },
                    "field_required": {
                        "summary": "Required Field Missing",
                        "value": {
                            "error": {
                                "code": "VALIDATION_ERROR",
                                "message": "Request validation failed",
                                "timestamp": "2023-01-01T00:00:00Z",
                                "request_id": "abc12345",
                                "details": [
                                    {
                                        "field": "title",
                                        "message": "Field required",
                                        "type": "missing"
                                    }
                                ]
                            }
                        }
                    },
                    "range_validation": {
                        "summary": "Range Validation Error",
                        "value": {
                            "error": {
                                "code": "VALIDATION_ERROR",
                                "message": "Request validation failed",
                                "timestamp": "2023-01-01T00:00:00Z",
                                "request_id": "abc12345",
                                "details": [
                                    {
                                        "field": "bedrooms",
                                        "message": "Input should be less than or equal to 50",
                                        "type": "less_than_equal",
                                        "input": 100
                                    },
                                    {
                                        "field": "min_price -> max_price",
                                        "message": "Minimum price cannot be greater than maximum price",
                                        "type": "value_error"
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }
    },
    429: {
        "description": "Too Many Requests - Rate limit exceeded",
        "model": APIErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Rate limit exceeded",
                        "timestamp": "2023-01-01T00:00:00Z",
                        "request_id": "abc12345"
                    }
                }
            }
        }
    },
    500: {
        "description": "Internal Server Error - Unexpected error",
        "model": APIErrorResponse,
        "content": {
            "application/json": {
                "examples": {
                    "internal_error": {
                        "summary": "Internal Server Error",
                        "value": {
                            "error": {
                                "code": "INTERNAL_SERVER_ERROR",
                                "message": "An unexpected error occurred. Please try again later.",
                                "timestamp": "2023-01-01T00:00:00Z",
                                "request_id": "abc12345"
                            }
                        }
                    },
                    "database_error": {
                        "summary": "Database Error",
                        "value": {
                            "error": {
                                "code": "DATABASE_ERROR",
                                "message": "Database operation failed",
                                "timestamp": "2023-01-01T00:00:00Z",
                                "request_id": "abc12345"
                            }
                        }
                    }
                }
            }
        }
    },
    503: {
        "description": "Service Unavailable - Service temporarily unavailable",
        "model": APIErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "SERVICE_UNAVAILABLE",
                        "message": "Service temporarily unavailable",
                        "timestamp": "2023-01-01T00:00:00Z",
                        "request_id": "abc12345"
                    }
                }
            }
        }
    }
}


def get_error_responses(*status_codes: int) -> Dict[int, Dict[str, Any]]:
    """
    Get error response schemas for specific status codes.
    
    Args:
        status_codes: HTTP status codes to include
        
    Returns:
        Dictionary of error response schemas
    """
    return {
        code: COMMON_ERROR_RESPONSES[code]
        for code in status_codes
        if code in COMMON_ERROR_RESPONSES
    }


def get_validation_error_response() -> Dict[int, Dict[str, Any]]:
    """Get validation error response schema."""
    return get_error_responses(422)


def get_auth_error_responses() -> Dict[int, Dict[str, Any]]:
    """Get authentication and authorization error response schemas."""
    return get_error_responses(401, 403)


def get_common_error_responses() -> Dict[int, Dict[str, Any]]:
    """Get common error response schemas for most endpoints."""
    return get_error_responses(400, 401, 403, 404, 422, 500)


def get_crud_error_responses() -> Dict[int, Dict[str, Any]]:
    """Get error response schemas for CRUD operations."""
    return get_error_responses(400, 401, 403, 404, 409, 422, 500)