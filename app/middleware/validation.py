"""
Validation middleware for comprehensive request validation and error handling.
Provides additional validation layers and request preprocessing.
"""

from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging
import time
import uuid

from app.services.error_handler import ErrorHandlerService
from app.utils.exceptions import BadRequestError, RateLimitExceededError

logger = logging.getLogger(__name__)


class ValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request validation and preprocessing.
    Handles request validation, rate limiting, and request logging.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        max_request_size: int = 10 * 1024 * 1024,  # 10MB
        enable_request_logging: bool = True,
        enable_rate_limiting: bool = False,
        rate_limit_requests: int = 100,
        rate_limit_window: int = 60
    ):
        super().__init__(app)
        self.max_request_size = max_request_size
        self.enable_request_logging = enable_request_logging
        self.enable_rate_limiting = enable_rate_limiting
        self.rate_limit_requests = rate_limit_requests
        self.rate_limit_window = rate_limit_window
        self.request_counts: Dict[str, Dict[str, Any]] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through validation middleware.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response object
        """
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        
        start_time = time.time()
        
        try:
            # Validate request size
            await self._validate_request_size(request)
            
            # Apply rate limiting if enabled
            if self.enable_rate_limiting:
                await self._apply_rate_limiting(request)
            
            # Validate request headers
            await self._validate_headers(request)
            
            # Log request if enabled
            if self.enable_request_logging:
                self._log_request(request, request_id)
            
            # Process request
            response = await call_next(request)
            
            # Log response if enabled
            if self.enable_request_logging:
                processing_time = time.time() - start_time
                self._log_response(request, response, request_id, processing_time)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as exc:
            # Handle middleware errors
            processing_time = time.time() - start_time
            logger.error(
                f"Middleware error [{request_id}]: {type(exc).__name__} - {str(exc)}",
                extra={
                    "request_id": request_id,
                    "path": request.url.path,
                    "method": request.method,
                    "processing_time": processing_time
                },
                exc_info=True
            )
            
            # Return appropriate error response
            if isinstance(exc, (BadRequestError, RateLimitExceededError)):
                return ErrorHandlerService.handle_api_exception(exc, request)
            else:
                return ErrorHandlerService.handle_unexpected_error(exc, request)
    
    async def _validate_request_size(self, request: Request) -> None:
        """
        Validate request content length.
        
        Args:
            request: FastAPI request object
            
        Raises:
            BadRequestError: If request size exceeds limit
        """
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_request_size:
                    raise BadRequestError(
                        f"Request size {size} bytes exceeds maximum allowed size {self.max_request_size} bytes"
                    )
            except ValueError:
                raise BadRequestError("Invalid content-length header")
    
    async def _apply_rate_limiting(self, request: Request) -> None:
        """
        Apply rate limiting based on client IP.
        
        Args:
            request: FastAPI request object
            
        Raises:
            RateLimitExceededError: If rate limit is exceeded
        """
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Clean old entries
        self._clean_rate_limit_data(current_time)
        
        # Check rate limit for client
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = {
                "count": 0,
                "window_start": current_time
            }
        
        client_data = self.request_counts[client_ip]
        
        # Reset window if expired
        if current_time - client_data["window_start"] > self.rate_limit_window:
            client_data["count"] = 0
            client_data["window_start"] = current_time
        
        # Check if limit exceeded
        if client_data["count"] >= self.rate_limit_requests:
            retry_after = int(self.rate_limit_window - (current_time - client_data["window_start"]))
            raise RateLimitExceededError(retry_after)
        
        # Increment request count
        client_data["count"] += 1
    
    async def _validate_headers(self, request: Request) -> None:
        """
        Validate request headers.
        
        Args:
            request: FastAPI request object
            
        Raises:
            BadRequestError: If headers are invalid
        """
        # Validate Content-Type for POST/PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            
            # Skip validation for multipart/form-data (file uploads)
            if content_type.startswith("multipart/form-data"):
                return
            
            # Validate JSON content type for API endpoints
            if request.url.path.startswith("/api/") and not content_type.startswith("application/json"):
                if content_type and not content_type.startswith("application/x-www-form-urlencoded"):
                    raise BadRequestError(
                        f"Unsupported content type '{content_type}'. Expected 'application/json'"
                    )
        
        # Validate Accept header if present
        accept_header = request.headers.get("accept")
        if accept_header and accept_header != "*/*":
            if "application/json" not in accept_header and "text/html" not in accept_header:
                logger.warning(f"Unusual Accept header: {accept_header}")
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client IP address
        """
        # Check for forwarded headers (load balancer/proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _clean_rate_limit_data(self, current_time: float) -> None:
        """
        Clean expired rate limit data.
        
        Args:
            current_time: Current timestamp
        """
        expired_clients = []
        for client_ip, data in self.request_counts.items():
            if current_time - data["window_start"] > self.rate_limit_window * 2:
                expired_clients.append(client_ip)
        
        for client_ip in expired_clients:
            del self.request_counts[client_ip]
    
    def _log_request(self, request: Request, request_id: str) -> None:
        """
        Log incoming request details.
        
        Args:
            request: FastAPI request object
            request_id: Unique request identifier
        """
        logger.info(
            f"Request [{request_id}]: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": self._get_client_ip(request),
                "user_agent": request.headers.get("user-agent", "unknown")
            }
        )
    
    def _log_response(
        self,
        request: Request,
        response: Response,
        request_id: str,
        processing_time: float
    ) -> None:
        """
        Log response details.
        
        Args:
            request: FastAPI request object
            response: FastAPI response object
            request_id: Unique request identifier
            processing_time: Request processing time in seconds
        """
        logger.info(
            f"Response [{request_id}]: {response.status_code} - {processing_time:.3f}s",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "processing_time": processing_time,
                "path": request.url.path,
                "method": request.method
            }
        )


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware specifically for request validation and preprocessing.
    Focuses on data validation and sanitization.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through validation middleware.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response object
        """
        try:
            # Validate and sanitize query parameters
            await self._validate_query_parameters(request)
            
            # Validate path parameters
            await self._validate_path_parameters(request)
            
            # Process request
            response = await call_next(request)
            
            return response
            
        except Exception as exc:
            # Handle validation errors
            if isinstance(exc, BadRequestError):
                return ErrorHandlerService.handle_api_exception(exc, request)
            else:
                return ErrorHandlerService.handle_unexpected_error(exc, request)
    
    async def _validate_query_parameters(self, request: Request) -> None:
        """
        Validate and sanitize query parameters.
        
        Args:
            request: FastAPI request object
            
        Raises:
            BadRequestError: If query parameters are invalid
        """
        for key, value in request.query_params.items():
            # Check for potentially dangerous characters
            if any(char in value for char in ['<', '>', '"', "'", '&']):
                logger.warning(f"Potentially dangerous query parameter: {key}={value}")
            
            # Validate parameter length
            if len(value) > 1000:
                raise BadRequestError(f"Query parameter '{key}' exceeds maximum length")
            
            # Validate specific parameter formats
            if key in ['page', 'page_size', 'limit', 'offset']:
                try:
                    int_value = int(value)
                    if int_value < 0:
                        raise BadRequestError(f"Parameter '{key}' must be non-negative")
                    if key in ['page_size', 'limit'] and int_value > 100:
                        raise BadRequestError(f"Parameter '{key}' exceeds maximum value of 100")
                except ValueError:
                    raise BadRequestError(f"Parameter '{key}' must be a valid integer")
    
    async def _validate_path_parameters(self, request: Request) -> None:
        """
        Validate path parameters.
        
        Args:
            request: FastAPI request object
            
        Raises:
            BadRequestError: If path parameters are invalid
        """
        path_params = request.path_params
        
        for key, value in path_params.items():
            # Validate UUID parameters
            if key.endswith('_id') or key == 'id':
                if not self._is_valid_uuid(str(value)):
                    raise BadRequestError(f"Invalid UUID format for parameter '{key}'")
    
    def _is_valid_uuid(self, uuid_string: str) -> bool:
        """
        Validate UUID format.
        
        Args:
            uuid_string: UUID string to validate
            
        Returns:
            True if valid UUID, False otherwise
        """
        try:
            import uuid
            uuid.UUID(uuid_string)
            return True
        except ValueError:
            return False