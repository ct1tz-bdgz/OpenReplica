"""
API routes for OpenReplica
"""
from fastapi import APIRouter
from .agents import router as agents_router
from .sessions import router as sessions_router
from .files import router as files_router
from .websocket_routes import router as websocket_router

# Main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(agents_router, prefix="/agents", tags=["agents"])
api_router.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
api_router.include_router(files_router, prefix="/files", tags=["files"])
api_router.include_router(websocket_router, prefix="/ws", tags=["websocket"])

__all__ = ["api_router"]
