"""Agent manager for OpenReplica."""

from typing import Dict, Type, Optional
from openreplica.agents.base import Agent
from openreplica.agents.coder import CoderAgent
from openreplica.core.exceptions import AgentError
from openreplica.core.logger import logger


class AgentManager:
    """Manages AI agents for different session types."""
    
    def __init__(self):
        self.agent_types: Dict[str, Type[Agent]] = {
            "coder": CoderAgent,
        }
        self.active_agents: Dict[str, Agent] = {}  # session_id -> agent
        
    def register_agent_type(self, name: str, agent_class: Type[Agent]):
        """Register a new agent type."""
        self.agent_types[name] = agent_class
        logger.info("Registered agent type", name=name)
        
    def create_agent(self, session_id: str, agent_type: str, config: Dict) -> Agent:
        """Create and register an agent for a session."""
        if agent_type not in self.agent_types:
            available_types = list(self.agent_types.keys())
            raise AgentError(f"Unknown agent type: {agent_type}. Available: {available_types}")
            
        agent_class = self.agent_types[agent_type]
        agent = agent_class(session_id, config)
        
        self.active_agents[session_id] = agent
        logger.info("Created agent", session_id=session_id, agent_type=agent_type)
        
        return agent
        
    def get_agent(self, session_id: str) -> Optional[Agent]:
        """Get the agent for a session."""
        return self.active_agents.get(session_id)
        
    def remove_agent(self, session_id: str):
        """Remove an agent for a session."""
        if session_id in self.active_agents:
            del self.active_agents[session_id]
            logger.info("Removed agent", session_id=session_id)
            
    def list_agent_types(self) -> list[str]:
        """List available agent types."""
        return list(self.agent_types.keys())


# Global agent manager instance
agent_manager = AgentManager()
