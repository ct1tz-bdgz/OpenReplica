"""
Agent Hub for OpenReplica matching OpenHands exactly
Contains all available agents
"""
from .codeact_agent import CodeActAgent
from .dummy_agent import DummyAgent
from .browsing_agent import BrowsingAgent

# Register agents
from app.controller.agent import Agent

Agent.register('CodeActAgent', CodeActAgent)
Agent.register('DummyAgent', DummyAgent) 
Agent.register('BrowsingAgent', BrowsingAgent)

__all__ = [
    "CodeActAgent",
    "DummyAgent",
    "BrowsingAgent"
]
