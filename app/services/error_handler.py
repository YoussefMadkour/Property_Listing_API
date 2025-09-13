"""
Error handling service for consistent error response formatting and logging.
Provides centralized error handling with structured responses and appropriate logging.
"""

from typing import Dict, Any, Optional, List
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError as PydanticValidationError
from app.utils.exceptions import APIException, ValidationError
import logging
import traceback
import uuid

logger = logging.getLogger(__name__)


class ErrorHandlerService:
    """
    Service for handling and formatting errors consistently across the application.
    Provides structured error responses with appropriate logging and error codes.
    """
    
    @staticmethod
    def format_error_response(
        error_code: str,
        message: str,
        details: Optional[List[Dict[str, Any]]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Format error response in a consistent structure.
        
        Args:
            error_code: Error code identifier
            message: Human-readable error message
            details: Optional list of detailed error information
            request_id: Optional request identifier for tracking
            
        Returns:
            Formatted error response dictionary
        """
        response = {
            "error": {
                "code": error_code,
                "message": message,
                "timestamp": ErrorHandlerService._get_current_timestamp(),
            }
        }
        
        if details:
            response["error"]["details"] = details
        
        if request_id:
            response["error"]["request_id"] = request_id
        
        return response
    
    @staticmethod
    def handle_api_exception(
        exception: APIException,
        request: Optional[Request] = None
    ) -> JSONResponse:
        """
        Handle custom API exceptions with structured response.
        
        Args:
            exception: API exception instance
            request: Optional FastAPI request object
            
        Returns:
            JSON response with formatted error
        """
        request_id = ErrorHandlerService._generate_request_id()
        
        # Log the error
        logger.warning(
            f"API Exception [{request_id}]: {exception.error_code} - {exception.detail}",
            extra={
                "error_code": exception.error_code,
                "status_code": exception.status_code,
                "request_id": request_id,
                "path": request.url.path if request else None
            }
        )
        
        # Format response
        error_response = ErrorHandlerService.format_error_response(
            error_code=exception.error_code or "API_ERROR",
            message=exception.detail,
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=exception.status_code,
            content=error_response,
            headers=exception.headers
        )
    
    @staticmethod
    def handle_validation_error(
        exception: PydanticValidationError,
        request: Optional[Request] = None
    ) -> JSONResponse:
        """
        Handle Pydantic validation errors with detailed field information.
        
        Args:
            exception: Pydantic validation error
            request: Optional FastAPI request object
            
        Returns:
            JSON response with validation error details
        """
        request_id = ErrorHandlerService._generate_request_id()
        
        # Extract validation details
        validation_details = []
        for error in exception.errors():
            field_path = " -> ".join(str(loc) for loc in error["loc"])
            validation_details.append({
                "field": field_path,
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input")
            })
        
        # Log the validation error
        logger.warning(
            f"Validation Error [{request_id}]: {len(validation_details)} field errors",
            extra={
                "error_count": len(validation_details),
                "request_id": request_id,
                "path": request.url.path if request else None,
                "validation_errors": validation_details
            }
        )
        
        # Format response
        error_response = ErrorHandlerService.format_error_response(
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            details=validation_details,
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=422,
            content=error_response
        )
    
    @staticmethod
    def handle_database_error(
        exception: SQLAlchemyError,
        request: Optional[Request] = None
    ) -> JSONResponse:
        """
        Handle database errors with appropriate error responses.
        
        Args:
            exception: SQLAlchemy error
            request: Optional FastAPI request object
            
        Returns:
            JSON response with database error information
        """
        request_id = ErrorHandlerService._generate_request_id()
        
        # Determine error type and message
        if isinstance(exception, IntegrityError):
            error_code = "INTEGRITY_ERROR"
            message = "Data integrity constraint violation"
            status_code = 409
            
            # Extract constraint information if available
            constraint_info = ErrorHandlerService._extract_constraint_info(exception)
            if constraint_info:
                message = f"Constraint violation: {constraint_info}"
        else:
            error_code = "DATABASE_ERROR"
            message = "Database operation failed"
            status_code = 500
        
        # Log the database error
        logger.error(
            f"Database Error [{request_id}]: {error_code} - {str(exception)}",
            extra={
                "error_code": error_code,
                "request_id": request_id,
                "path": request.url.path if request else None,
                "exception_type": type(exception).__name__
            },
            exc_info=True
        )
        
        # Format response (don't expose internal database details in production)
        error_response = ErrorHandlerService.format_error_response(
            error_code=error_code,
            message=message,
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=status_code,
            content=error_response
        )
    
    @staticmethod
    def handle_http_exception(
        exception: HTTPException,
        request: Optional[Request] = None
    ) -> JSONResponse:
        """
        Handle FastAPI HTTP exceptions.
        
        Args:
            exception: HTTP exception
            request: Optional FastAPI request object
            
        Returns:
            JSON response with HTTP error information
        """
        request_id = ErrorHandlerService._generate_request_id()
        
        # Log the HTTP error
        logger.warning(
            f"HTTP Exception [{request_id}]: {exception.status_code} - {exception.detail}",
            extra={
                "status_code": exception.status_code,
                "request_id": request_id,
                "path": request.url.path if request else None
            }
        )
        
        # Format response
        error_response = ErrorHandlerService.format_error_response(
            error_code=f"HTTP_{exception.status_code}",
            message=exception.detail,
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=exception.status_code,
            content=error_response,
            headers=exception.headers
        )
    
    @staticmethod
    def handle_unexpected_error(
        exception: Exception,
        request: Optional[Request] = None
    ) -> JSONResponse:
        """
        Handle unexpected errors with secure error responses.
        
        Args:
            exception: Unexpected exception
            request: Optional FastAPI request object
            
        Returns:
            JSON response with generic error message
        """
        request_id = ErrorHandlerService._generate_request_id()
        
        # Log the unexpected error with full traceback
        logger.error(
            f"Unexpected Error [{request_id}]: {type(exception).__name__} - {str(exception)}",
            extra={
                "request_id": request_id,
                "path": request.url.path if request else None,
                "exception_type": type(exception).__name__,
                "traceback": traceback.format_exc()
            },
            exc_info=True
        )
        
        # Format response (don't expose internal details)
        error_response = ErrorHandlerService.format_error_response(
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred. Please try again later.",
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response
        )
    
    @staticmethod
    def create_business_rule_error(
        rule_name: str,
        message: str,
        field: Optional[str] = None
    ) -> ValidationError:
        """
        Create a business rule validation error.
        
        Args:
            rule_name: Name of the business rule
            message: Error message
            field: Optional field name
            
        Returns:
            ValidationError instance
        """
        details = [{
            "rule": rule_name,
            "message": message,
            "field": field
        }] if field else None
        
        return ValidationError(
            detail=f"Business rule violation: {rule_name}",
            field_errors=details
        )
    
    @staticmethod
    def _generate_request_id() -> str:
        """Generate a unique request ID for error tracking."""
        return str(uuid.uuid4())[:8]
    
    @staticmethod
    def _get_current_timestamp() -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
    
    @staticmethod
    def _extract_constraint_info(exception: IntegrityError) -> Optional[str]:
        """
        Extract constraint information from integrity error.
        
        Args:
            exception: SQLAlchemy integrity error
            
        Returns:
            Constraint information string or None
        """
        try:
            error_msg = str(exception.orig)
            
            # Common constraint patterns
            if "unique constraint" in error_msg.lower():
                return "Duplicate value for unique field"
            elif "foreign key constraint" in error_msg.lower():
                return "Referenced record does not exist"
            elif "not null constraint" in error_msg.lower():
                return "Required field cannot be empty"
            elif "check constraint" in error_msg.lower():
                return "Value does not meet validation requirements"
            
            return None
        except Exception:
            return None


# Global error response schemas for documentation
ERROR_RESPONSES = {
    400: {
        "description": "Bad Request",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "Invalid request parameters",
                        "timestamp": "2023-01-01T00:00:00Z",
                        "request_id": "abc12345"
                    }
                }
            }
        }
    },
    401: {
        "description": "Unauthorized",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "Authentication required",
                        "timestamp": "2023-01-01T00:00:00Z",
                        "request_id": "abc12345"
                    }
                }
            }
        }
    },
    403: {
        "description": "Forbidden",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "Access forbidden",
                        "timestamp": "2023-01-01T00:00:00Z",
                        "request_id": "abc12345"
                    }
                }
            }
        }
    },
    404: {
        "description": "Not Found",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Resource not found",
                        "timestamp": "2023-01-01T00:00:00Z",
                        "request_id": "abc12345"
                    }
                }
            }
        }
    },
    422: {
        "description": "Validation Error",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Request validation failed",
                        "timestamp": "2023-01-01T00:00:00Z",
                        "request_id": "abc12345",
                        "details": [
                            {
                                "field": "email",
                                "message": "Invalid email format",
                                "type": "value_error.email"
                            }
                        ]
                    }
                }
            }
        }
    },
    500: {
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred",
                        "timestamp": "2023-01-01T00:00:00Z",
                        "request_id": "abc12345"
                    }
                }
            }
        }
    }
}