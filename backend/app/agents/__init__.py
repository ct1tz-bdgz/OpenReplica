"""
Agent system for OpenReplica
"""
from .base import Agent, AgentConfig
from .codeact.agent import CodeActAgent
from .browsing.agent import BrowsingAgent
from .dummy.agent import DummyAgent

# Agent registry
AGENT_REGISTRY = {
    "codeact": CodeActAgent,
    "browsing": BrowsingAgent,
    "dummy": DummyAgent,
}


def create_agent(agent_type: str, config: AgentConfig) -> Agent:
    """Factory function to create agents"""
    if agent_type not in AGENT_REGISTRY:
        raise ValueError(f"Unknown agent type: {agent_type}")
    
    agent_class = AGENT_REGISTRY[agent_type]
    return agent_class(config)


def get_available_agents() -> list[str]:
    """Get list of available agent types"""
    return list(AGENT_REGISTRY.keys())


__all__ = [
    "Agent",
    "AgentConfig", 
    "CodeActAgent",
    "BrowsingAgent",
    "DummyAgent",
    "create_agent",
    "get_available_agents",
    "AGENT_REGISTRY"
]
