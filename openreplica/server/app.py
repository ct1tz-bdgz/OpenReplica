"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from openreplica.core.config import settings
from openreplica.core.logger import logger
from openreplica.database.connection import init_db
from openreplica.server.routes import api_router
from openreplica.server.websocket import websocket_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="OpenReplica",
        description="A beautiful replica of OpenHands with enhanced UI",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(websocket_router)
    
    # Serve static files for frontend
    try:
        app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
    except RuntimeError:
        # Frontend not built yet, will serve API only
        logger.warning("Frontend static files not found. Serving API only.")
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize application on startup."""
        logger.info("Starting OpenReplica server", version="1.0.0")
        await init_db()
        logger.info("Server started successfully", host=settings.host, port=settings.port)
        
    @app.on_event("shutdown")
    async def shutdown_event():
        """Clean up on shutdown."""
        logger.info("Shutting down OpenReplica server")
        
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": "1.0.0"}
        
    return app
