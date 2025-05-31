"""
Dummy agent for testing and development
"""
import asyncio
from typing import Dict, Any

from app.agents.base import Agent, AgentConfig
from app.events.action import Action, create_action, ActionType
from app.events.observation import Observation


class DummyAgent(Agent):
    """
    A simple dummy agent for testing purposes.
    Always responds with think actions and finishes after a few steps.
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.steps_taken = 0
        self.max_steps = 3
    
    async def step(self, observation: Observation) -> Action:
        """Take a dummy step"""
        self.steps_taken += 1
        
        self.logger.info(
            "Dummy agent step",
            step=self.steps_taken,
            observation_type=observation.observation_type
        )
        
        # Simulate thinking time
        await asyncio.sleep(0.1)
        
        if self.steps_taken >= self.max_steps:
            return create_action(
                ActionType.FINISH,
                thought=f"Dummy agent finished after {self.steps_taken} steps",
                success=True,
                message="Dummy task completed successfully"
            )
        
        return create_action(
            ActionType.THINK,
            thought=f"Dummy agent thinking... step {self.steps_taken}",
            content=f"This is dummy thought #{self.steps_taken}. "
                   f"I'm processing observation: {observation.observation_type}"
        )
    
    async def reset(self) -> None:
        """Reset the dummy agent"""
        self.state = self.state.__class__.IDLE
        self.steps_taken = 0
        self.iteration_count = 0
        self.total_cost = 0.0
        
        self.logger.info("Dummy agent reset")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get dummy agent statistics"""
        stats = super().get_stats()
        stats.update({
            "steps_taken": self.steps_taken,
            "max_steps": self.max_steps
        })
        return stats
