"""
FastAPI application entry point.
Main application setup and configuration.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import test_database_connection, close_db_connection
from app.routers import auth_router, properties_router
from app.utils.exceptions import APIException

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

# Include API routers
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(properties_router, prefix=settings.api_v1_prefix)


# Global exception handlers
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    """Handle custom API exceptions with structured error responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code or "API_ERROR",
                "message": exc.detail,
                "status_code": exc.status_code
            }
        },
        headers=exc.headers
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions with structured error responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
                "status_code": exc.status_code
            }
        },
        headers=exc.headers
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "status_code": 500
            }
        }
    )


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