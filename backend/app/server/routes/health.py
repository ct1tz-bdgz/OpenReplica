"""
Health check routes for OpenReplica matching OpenHands exactly
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import psutil
import os
from datetime import datetime

from app.core.logging import get_logger
from app.server.shared import config
from app import __version__

logger = get_logger(__name__)


def add_health_endpoints(app):
    """Add health check endpoints to the app"""
    
    @app.get("/health")
    async def health_check():
        """Basic health check endpoint"""
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": __version__,
                "service": "OpenReplica"
            }
        )
    
    @app.get("/health/detailed")
    async def detailed_health_check():
        """Detailed health check with system metrics"""
        try:
            # System metrics
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Check if critical services are running
            services_status = {
                "runtime": "healthy",  # Would check runtime connectivity
                "database": "healthy",  # Would check database connectivity
                "mcp": "healthy",  # Would check MCP service
            }
            
            health_data = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": __version__,
                "service": "OpenReplica",
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory": {
                        "total": memory.total,
                        "available": memory.available,
                        "percent": memory.percent,
                        "used": memory.used
                    },
                    "disk": {
                        "total": disk.total,
                        "free": disk.free,
                        "used": disk.used,
                        "percent": (disk.used / disk.total) * 100
                    }
                },
                "services": services_status,
                "configuration": {
                    "workspace_base": getattr(config, 'workspace_base', '/tmp'),
                    "max_iterations": getattr(config, 'max_iterations', 100),
                    "runtime_container_image": getattr(config, 'runtime_container_image', 'openreplica-runtime')
                }
            }
            
            # Determine overall status
            overall_status = "healthy"
            if cpu_percent > 90:
                overall_status = "degraded"
            if memory.percent > 90:
                overall_status = "degraded"
            if any(status != "healthy" for status in services_status.values()):
                overall_status = "unhealthy"
            
            health_data["status"] = overall_status
            
            status_code = 200 if overall_status in ["healthy", "degraded"] else 503
            
            return JSONResponse(
                status_code=status_code,
                content=health_data
            )
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": str(e),
                    "service": "OpenReplica"
                }
            )
    
    @app.get("/health/ready")
    async def readiness_check():
        """Kubernetes readiness probe endpoint"""
        try:
            # Check if all required services are ready
            ready = True
            checks = {
                "runtime": True,  # Would check if runtime is ready
                "storage": True,  # Would check if storage is ready
                "llm": True,  # Would check if LLM is configured
            }
            
            if not all(checks.values()):
                ready = False
            
            return JSONResponse(
                status_code=200 if ready else 503,
                content={
                    "ready": ready,
                    "checks": checks,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return JSONResponse(
                status_code=503,
                content={
                    "ready": False,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    @app.get("/health/live")
    async def liveness_check():
        """Kubernetes liveness probe endpoint"""
        return JSONResponse(
            status_code=200,
            content={
                "alive": True,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    @app.get("/version")
    async def version_info():
        """Get version information"""
        return JSONResponse(
            content={
                "version": __version__,
                "service": "OpenReplica",
                "description": "The Next Generation AI Development Platform",
                "build_time": datetime.utcnow().isoformat()
            }
        )
