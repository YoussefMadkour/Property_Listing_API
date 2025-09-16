"""
FastAPI application entry point.
Main application setup and configuration.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError as PydanticValidationError
import logging
import time

from app.config import settings
from app.database import test_database_connection, close_db_connection
from app.routers import auth_router, properties_router, images_router
from app.routers.monitoring import router as monitoring_router
from app.utils.exceptions import APIException
from app.services.error_handler import ErrorHandlerService
from app.middleware.validation import ValidationMiddleware, RequestValidationMiddleware
from app.middleware.performance import PerformanceMonitoringMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    
    # Test database connection on startup
    db_connected = await test_database_connection()
    if not db_connected:
        logger.error("Failed to connect to database on startup")
        # In production, you might want to exit here
        # For development, we'll continue but log the error
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    await close_db_connection()


# Create FastAPI application instance
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    A comprehensive property listing API for rental and sales platforms.
    
    ## Features
    
    * **Property Management**: Complete CRUD operations for property listings
    * **Advanced Search**: Filter properties by location, price, bedrooms, and more
    * **Image Upload**: Support for multiple property images with validation
    * **Authentication**: JWT-based authentication with role-based access control
    * **Performance Optimized**: Database indexing and query optimization
    * **Docker Ready**: Fully containerized with Docker Compose support
    
    ## Authentication
    
    Most endpoints require authentication. Use the `/api/v1/auth/login` endpoint to obtain a JWT token,
    then include it in the Authorization header as `Bearer <token>`.
    
    ## Rate Limiting
    
    API requests are rate limited to prevent abuse. Check response headers for rate limit information.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "User authentication and token management"
        },
        {
            "name": "Properties",
            "description": "Property listing management and search operations"
        },
        {
            "name": "Images",
            "description": "Property image upload and management"
        },
        {
            "name": "Health",
            "description": "System health and monitoring endpoints"
        }
    ],
    contact={
        "name": "Property Listing API Support",
        "email": "support@propertyapi.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Processing-Time", "X-CPU-Time"],
)

# Add performance monitoring middleware
app.add_middleware(
    PerformanceMonitoringMiddleware,
    enable_detailed_logging=settings.debug,
    enable_metrics_collection=True,
    slow_request_threshold=2.0,  # Log requests slower than 2 seconds
    enable_system_monitoring=not settings.is_testing,  # Disable in tests for performance
)

# Add validation middleware
app.add_middleware(
    ValidationMiddleware,
    max_request_size=10 * 1024 * 1024,  # 10MB
    enable_request_logging=settings.debug,
    enable_rate_limiting=settings.is_production  # Enable rate limiting in production
)

app.add_middleware(RequestValidationMiddleware)

# Include API routers
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(properties_router, prefix=settings.api_v1_prefix)
app.include_router(images_router, prefix=settings.api_v1_prefix)
app.include_router(monitoring_router, prefix=settings.api_v1_prefix)


# Global exception handlers using ErrorHandlerService
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    """Handle custom API exceptions with structured error responses."""
    return ErrorHandlerService.handle_api_exception(exc, request)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI request validation errors with detailed field information."""
    return ErrorHandlerService.handle_validation_error(exc, request)


@app.exception_handler(PydanticValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: PydanticValidationError):
    """Handle Pydantic validation errors with detailed field information."""
    return ErrorHandlerService.handle_validation_error(exc, request)


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors with appropriate error responses."""
    return ErrorHandlerService.handle_database_error(exc, request)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions with structured error responses."""
    return ErrorHandlerService.handle_http_exception(exc, request)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with secure error responses."""
    return ErrorHandlerService.handle_unexpected_error(exc, request)


@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint providing basic API information.
    
    Returns general information about the API including version,
    environment, and basic status information.
    """
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "healthy",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        },
        "api_prefix": settings.api_v1_prefix
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint with database connectivity test.
    Used by Docker health checks and load balancers.
    """
    try:
        # Test database connection
        db_healthy = await test_database_connection()
        
        if not db_healthy:
            raise HTTPException(
                status_code=503,
                detail="Database connection failed"
            )
        
        return {
            "status": "healthy",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )


@app.get("/health/db", tags=["Health"])
async def database_health_check():
    """
    Dedicated database health check endpoint.
    """
    try:
        db_healthy = await test_database_connection()
        
        if not db_healthy:
            raise HTTPException(
                status_code=503,
                detail="Database connection failed"
            )
        
        return {
            "status": "healthy",
            "database": "connected",
            "database_url": settings.database_url.split("@")[1] if "@" in settings.database_url else "hidden"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Database unhealthy: {str(e)}"
        )


@app.get("/metrics", tags=["Health"])
async def get_performance_metrics():
    """
    Get application performance metrics and statistics.
    
    Returns detailed performance information including:
    - Request statistics per endpoint
    - System resource usage
    - Error rates and response times
    - Recent slow requests
    
    Note: This endpoint should be secured in production environments.
    """
    try:
        # Get performance middleware instance
        performance_middleware = None
        for middleware in app.user_middleware:
            if isinstance(middleware.cls, type) and issubclass(middleware.cls, PerformanceMonitoringMiddleware):
                # Find the actual middleware instance
                for layer in app.middleware_stack:
                    if hasattr(layer, 'app') and isinstance(layer.app, PerformanceMonitoringMiddleware):
                        performance_middleware = layer.app
                        break
                break
        
        if not performance_middleware:
            return {
                "error": "Performance monitoring not enabled",
                "message": "Performance metrics are not available"
            }
        
        # Get comprehensive metrics
        summary = performance_middleware.get_performance_summary()
        slow_requests = performance_middleware.get_recent_slow_requests(limit=5)
        
        return {
            "timestamp": time.time(),
            "performance_summary": summary,
            "recent_slow_requests": slow_requests,
            "configuration": {
                "slow_request_threshold": performance_middleware.slow_request_threshold,
                "metrics_collection_enabled": performance_middleware.enable_metrics_collection,
                "detailed_logging_enabled": performance_middleware.enable_detailed_logging
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to retrieve performance metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve performance metrics"
        )


@app.get("/metrics/health", tags=["Health"])
async def get_system_health():
    """
    Get current system health and resource usage.
    
    Returns real-time system information including:
    - CPU usage
    - Memory usage  
    - Process statistics
    - Application uptime
    """
    try:
        result = {
            "timestamp": time.time(),
            "application": {
                "name": settings.app_name,
                "version": settings.app_version,
                "environment": settings.environment,
                "debug": settings.debug
            }
        }
        
        # Try to get system metrics if psutil is available
        try:
            import psutil
            
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            # Get process metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            
            result.update({
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_total": memory.total,
                    "memory_available": memory.available,
                    "memory_used": memory.used
                },
                "process": {
                    "memory_rss": process_memory.rss,
                    "memory_vms": process_memory.vms,
                    "cpu_percent": process.cpu_percent(),
                    "num_threads": process.num_threads(),
                    "create_time": process.create_time()
                }
            })
            
        except ImportError:
            result["system"] = {"message": "System monitoring unavailable (psutil not installed)"}
            result["process"] = {"message": "Process monitoring unavailable (psutil not installed)"}
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to retrieve system health: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve system health information"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )