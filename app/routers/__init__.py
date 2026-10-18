"""
Application route modules.
"""
from app.routers.auth import router as auth_router
from app.routers.views import router as views_router
from app.routers.api import router as api_router

__all__ = ["auth_router", "views_router", "api_router"]
