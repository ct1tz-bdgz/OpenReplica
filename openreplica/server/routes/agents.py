"""Agent management routes."""

from typing import List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from openreplica.agents.manager import agent_manager

router = APIRouter()


class AgentTypeResponse(BaseModel):
    """Response model for agent types."""
    name: str
    description: str


@router.get("/types", response_model=List[str])
async def list_agent_types():
    """List available agent types."""
    return agent_manager.list_agent_types()


@router.get("/types/detailed", response_model=List[AgentTypeResponse])
async def list_agent_types_detailed():
    """List available agent types with descriptions."""
    types = agent_manager.list_agent_types()
    
    descriptions = {
        "coder": "AI coding assistant that can write, execute, and debug code"
    }
    
    return [
        AgentTypeResponse(name=name, description=descriptions.get(name, "AI assistant"))
        for name in types
    ]


@router.get("/{session_id}/status")
async def get_agent_status(session_id: str):
    """Get the status of an agent for a session."""
    agent = agent_manager.get_agent(session_id)
    
    if not agent:
        return {"status": "inactive", "type": None}
        
    return {
        "status": "active",
        "type": agent.__class__.__name__.lower().replace("agent", ""),
        "config": agent.config
    }
