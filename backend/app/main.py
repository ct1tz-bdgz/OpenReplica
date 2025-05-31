"""
OpenReplica - FastAPI main application
A complete replica of OpenHands with enhanced features
"""
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import socketio

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.server.routes import api_router
from app.server.websocket.manager import SocketManager
from app.storage.conversation import ConversationStorage

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global instances
sio_server = None
socket_manager = None
conversation_storage = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager"""
    global sio_server, socket_manager, conversation_storage
    
    logger.info("Starting OpenReplica backend...")
    
    # Initialize settings
    settings = get_settings()
    
    # Initialize storage
    conversation_storage = ConversationStorage()
    await conversation_storage.initialize()
    
    # Initialize Socket.IO
    sio_server = socketio.AsyncServer(
        cors_allowed_origins="*",
        logger=True,
        engineio_logger=True,
    )
    
    # Initialize socket manager
    socket_manager = SocketManager(sio_server)
    
    # Mount Socket.IO
    socket_app = socketio.ASGIApp(sio_server, app)
    app.mount("/ws", socket_app)
    
    logger.info("OpenReplica backend started successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down OpenReplica backend...")
    if conversation_storage:
        await conversation_storage.close()


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()
    
    app = FastAPI(
        title="OpenReplica",
        description="A complete replica of OpenHands with enhanced features",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(api_router, prefix="/api")
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "OpenReplica"}
    
    # Serve frontend static files (if available)
    if os.path.exists("../frontend/dist"):
        app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="frontend")
    
    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
