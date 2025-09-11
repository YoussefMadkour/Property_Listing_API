"""
FastAPI application entry point.
Main application setup and configuration.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import test_database_connection, close_db_connection

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