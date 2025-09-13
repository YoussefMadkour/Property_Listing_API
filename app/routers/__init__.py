"""
API route handlers for the Property Listing API.
Provides organized routing for different API endpoints.
"""

from .auth import router as auth_router
from .properties import router as properties_router

__all__ = ["auth_router", "properties_router"]