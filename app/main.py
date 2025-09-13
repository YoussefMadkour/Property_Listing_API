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

from app.config import settings
from app.database import test_database_connection, close_db_connection
from app.routers import auth_router, properties_router
from app.routers.images import router as images_router
from app.utils.exceptions import APIException
from app.services.error_handler import ErrorHandlerService
from app.middleware.validation import ValidationMiddleware, RequestValidationMiddleware

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
    description="A comprehensive property listing API for rental and sales platforms",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add validation middleware
app.add_middleware(
    ValidationMiddleware,
    max_request_size=10 * 1024 * 1024,  # 10MB
    enable_request_logging=settings.debug,
    enable_rate_limiting=False  # Can be enabled in production
)

app.add_middleware(RequestValidationMiddleware)

# Include API routers
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(properties_router, prefix=settings.api_v1_prefix)
app.include_router(images_router, prefix=settings.api_v1_prefix)


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


@app.get("/")
async def root():
    """Root endpoint for basic information."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "healthy"
    }


@app.get("/health")
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


@app.get("/health/db")
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )