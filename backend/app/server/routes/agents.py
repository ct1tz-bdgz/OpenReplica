"""
Agent management API routes
"""
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.agents import create_agent, get_available_agents, AgentConfig
from app.agents.base import AgentState
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

# In-memory store for demo (use database in production)
active_agents: Dict[str, Any] = {}


class CreateAgentRequest(BaseModel):
    agent_type: str
    config: Dict[str, Any] = {}
    session_id: str


class AgentResponse(BaseModel):
    agent_id: str
    agent_type: str
    state: str
    stats: Dict[str, Any]


@router.get("/types")
async def get_agent_types() -> Dict[str, List[str]]:
    """Get list of available agent types"""
    return {"agent_types": get_available_agents()}


@router.post("/create")
async def create_new_agent(request: CreateAgentRequest) -> AgentResponse:
    """Create a new agent instance"""
    try:
        # Create agent config
        config_dict = {
            "workspace_dir": f"/tmp/workspace/{request.session_id}",
            **request.config
        }
        config = AgentConfig(**config_dict)
        
        # Create agent
        agent = create_agent(request.agent_type, config)
        agent.set_session_id(request.session_id)
        
        # Generate agent ID
        agent_id = f"{request.agent_type}_{request.session_id}"
        
        # Store agent
        active_agents[agent_id] = {
            "agent": agent,
            "agent_type": request.agent_type,
            "session_id": request.session_id
        }
        
        logger.info(
            "Agent created",
            agent_id=agent_id,
            agent_type=request.agent_type,
            session_id=request.session_id
        )
        
        return AgentResponse(
            agent_id=agent_id,
            agent_type=request.agent_type,
            state=agent.state.value,
            stats=agent.get_stats()
        )
        
    except Exception as e:
        logger.error("Failed to create agent", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}")
async def get_agent(agent_id: str) -> AgentResponse:
    """Get agent information"""
    if agent_id not in active_agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent_info = active_agents[agent_id]
    agent = agent_info["agent"]
    
    return AgentResponse(
        agent_id=agent_id,
        agent_type=agent_info["agent_type"],
        state=agent.state.value,
        stats=agent.get_stats()
    )


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str) -> Dict[str, str]:
    """Delete an agent instance"""
    if agent_id not in active_agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent_info = active_agents[agent_id]
    agent = agent_info["agent"]
    
    # Reset agent before deletion
    await agent.reset()
    
    # Remove from active agents
    del active_agents[agent_id]
    
    logger.info("Agent deleted", agent_id=agent_id)
    
    return {"message": f"Agent {agent_id} deleted successfully"}


@router.post("/{agent_id}/reset")
async def reset_agent(agent_id: str) -> AgentResponse:
    """Reset an agent to initial state"""
    if agent_id not in active_agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent_info = active_agents[agent_id]
    agent = agent_info["agent"]
    
    # Reset agent
    await agent.reset()
    
    logger.info("Agent reset", agent_id=agent_id)
    
    return AgentResponse(
        agent_id=agent_id,
        agent_type=agent_info["agent_type"],
        state=agent.state.value,
        stats=agent.get_stats()
    )


@router.get("/")
async def list_agents() -> Dict[str, List[AgentResponse]]:
    """List all active agents"""
    agents = []
    for agent_id, agent_info in active_agents.items():
        agent = agent_info["agent"]
        agents.append(AgentResponse(
            agent_id=agent_id,
            agent_type=agent_info["agent_type"],
            state=agent.state.value,
            stats=agent.get_stats()
        ))
    
    return {"agents": agents}


def get_agent_by_id(agent_id: str):
    """Dependency to get agent by ID"""
    if agent_id not in active_agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    return active_agents[agent_id]["agent"]
