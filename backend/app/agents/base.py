"""
Base agent classes for OpenReplica
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncGenerator
from pydantic import BaseModel, Field
from enum import Enum

from app.events.base import Event
from app.events.action import Action
from app.events.observation import Observation
from app.core.logging import LoggerMixin


class AgentState(str, Enum):
    """Agent execution states"""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING = "waiting"
    FINISHED = "finished"
    ERROR = "error"


class AgentConfig(BaseModel):
    """Configuration for agents"""
    
    # LLM settings
    llm_provider: str = "openai"
    llm_model: str = "gpt-4"
    temperature: float = 0.1
    max_tokens: int = 4000
    
    # Agent behavior
    max_iterations: int = 100
    max_budget_per_task: float = 4.0
    
    # Environment settings
    workspace_dir: str = "/tmp/workspace"
    container_image: Optional[str] = None
    
    # Agent-specific settings
    agent_specific_config: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        extra = "allow"


class Agent(ABC, LoggerMixin):
    """Base class for all agents"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.state = AgentState.IDLE
        self.iteration_count = 0
        self.total_cost = 0.0
        self.session_id: Optional[str] = None
        self.workspace_dir = config.workspace_dir
        
    @abstractmethod
    async def step(self, observation: Observation) -> Action:
        """
        Take a single step given an observation.
        
        Args:
            observation: The observation from the environment
            
        Returns:
            The action to take next
        """
        pass
    
    @abstractmethod
    async def reset(self) -> None:
        """Reset the agent to initial state"""
        pass
    
    async def run(self, 
                 initial_observation: Observation,
                 max_iterations: Optional[int] = None) -> AsyncGenerator[Event, None]:
        """
        Run the agent for multiple steps.
        
        Args:
            initial_observation: The initial observation
            max_iterations: Maximum number of iterations (overrides config)
            
        Yields:
            Events generated during execution
        """
        self.state = AgentState.THINKING
        max_iters = max_iterations or self.config.max_iterations
        current_observation = initial_observation
        
        yield current_observation
        
        for i in range(max_iters):
            self.iteration_count = i + 1
            
            try:
                # Check budget
                if self.total_cost > self.config.max_budget_per_task:
                    self.logger.warning(
                        "Budget exceeded",
                        cost=self.total_cost,
                        budget=self.config.max_budget_per_task
                    )
                    break
                
                # Take a step
                self.state = AgentState.THINKING
                action = await self.step(current_observation)
                
                self.state = AgentState.ACTING
                action.session_id = self.session_id
                yield action
                
                # Check if agent wants to finish
                if action.action_type.value == "finish":
                    self.state = AgentState.FINISHED
                    break
                
                # Wait for next observation (this would be provided by the runtime)
                self.state = AgentState.WAITING
                
                # In a real implementation, this would be provided by the environment
                # For now, we'll simulate receiving a null observation
                from app.events.observation import create_observation, ObservationType
                current_observation = create_observation(
                    ObservationType.NULL,
                    content="Step completed"
                )
                
            except Exception as e:
                self.logger.error("Error during agent step", error=str(e))
                self.state = AgentState.ERROR
                
                from app.events.observation import create_observation, ObservationType
                error_obs = create_observation(
                    ObservationType.ERROR,
                    error_message=str(e),
                    success=False
                )
                yield error_obs
                break
        
        if self.state != AgentState.FINISHED:
            self.state = AgentState.FINISHED
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent execution statistics"""
        return {
            "state": self.state.value,
            "iteration_count": self.iteration_count,
            "total_cost": self.total_cost,
            "session_id": self.session_id
        }
    
    def set_session_id(self, session_id: str) -> None:
        """Set the session ID for this agent"""
        self.session_id = session_id
    
    @property
    def agent_type(self) -> str:
        """Get the agent type name"""
        return self.__class__.__name__.lower().replace("agent", "")


class LLMAgent(Agent):
    """Base class for LLM-powered agents"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.conversation_history: List[Dict[str, str]] = []
    
    async def call_llm(self, 
                      messages: List[Dict[str, str]], 
                      temperature: Optional[float] = None) -> str:
        """
        Call the LLM with the given messages.
        
        Args:
            messages: List of messages in OpenAI format
            temperature: Override temperature for this call
            
        Returns:
            The LLM response
        """
        # This would be implemented to call the actual LLM
        # For now, return a placeholder
        temp = temperature or self.config.temperature
        
        self.logger.info(
            "LLM call",
            provider=self.config.llm_provider,
            model=self.config.llm_model,
            messages_count=len(messages),
            temperature=temp
        )
        
        # Simulate cost calculation
        estimated_tokens = sum(len(msg.get("content", "")) for msg in messages) // 4
        estimated_cost = estimated_tokens * 0.00003  # Rough estimate
        self.total_cost += estimated_cost
        
        # Return a placeholder response
        return "This is a placeholder LLM response"
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
    
    def clear_history(self) -> None:
        """Clear the conversation history"""
        self.conversation_history.clear()
    
    async def reset(self) -> None:
        """Reset the LLM agent"""
        await super().reset()
        self.clear_history()
