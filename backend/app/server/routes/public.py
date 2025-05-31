"""
Public routes for OpenReplica matching OpenHands exactly
"""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any

from app.core.logging import get_logger
from app import __version__

logger = get_logger(__name__)

app = APIRouter(prefix='/api/public')


class StatusResponse(BaseModel):
    """Response model for status endpoint"""
    status: str
    version: str
    message: str


@app.get('/status', response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """Get public status of the service"""
    return StatusResponse(
        status="healthy",
        version=__version__,
        message="OpenReplica is running"
    )


@app.get('/version')
async def get_version() -> JSONResponse:
    """Get version information"""
    return JSONResponse({
        "version": __version__,
        "name": "OpenReplica",
        "description": "The Next Generation AI Development Platform"
    })


@app.get('/info')
async def get_info() -> JSONResponse:
    """Get public information about the service"""
    return JSONResponse({
        "name": "OpenReplica",
        "version": __version__,
        "description": "The Next Generation AI Development Platform",
        "features": [
            "AI-powered code generation",
            "Multiple LLM provider support",
            "Real-time collaboration",
            "Custom microagents",
            "Git integration",
            "VS Code session viewing",
            "File download and export"
        ],
        "supported_llm_providers": [
            "OpenAI",
            "Anthropic",
            "Google",
            "Cohere",
            "OpenRouter",
            "Ollama",
            "Together",
            "Replicate"
        ]
    })


@app.get('/health')
async def health_check() -> JSONResponse:
    """Public health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z"
    })
