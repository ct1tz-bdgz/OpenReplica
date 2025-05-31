"""API routes for OpenReplica."""

from fastapi import APIRouter
from openreplica.server.routes.sessions import router as sessions_router
from openreplica.server.routes.conversations import router as conversations_router
from openreplica.server.routes.agents import router as agents_router
from openreplica.server.routes.runtime import router as runtime_router

api_router = APIRouter()

api_router.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
api_router.include_router(conversations_router, prefix="/conversations", tags=["conversations"])
api_router.include_router(agents_router, prefix="/agents", tags=["agents"])
api_router.include_router(runtime_router, prefix="/runtime", tags=["runtime"])
