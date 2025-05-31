"""Base agent class for OpenReplica."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator
from openreplica.core.logger import logger
from openreplica.events.base import Event, EventType
from openreplica.events.manager import event_manager
from openreplica.llm.manager import llm_manager


class Agent(ABC):
    """Abstract base class for AI agents."""
    
    def __init__(self, session_id: str, config: Dict[str, Any]):
        self.session_id = session_id
        self.config = config
        self.conversation_history: List[Dict[str, str]] = []
        
    @abstractmethod
    async def process_message(self, message: str, **kwargs) -> AsyncGenerator[str, None]:
        """Process a user message and generate responses."""
        pass
        
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        pass
        
    async def _emit_event(self, event_type: EventType, data: Dict[str, Any]):
        """Emit an event."""
        event = Event(
            type=event_type,
            session_id=self.session_id,
            data=data
        )
        await event_manager.emit_event(event)
        
    async def _generate_response(
        self, 
        messages: List[Dict[str, str]], 
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """Generate a response using the LLM."""
        try:
            provider_name = self.config.get("llm_provider", "openai")
            
            if stream:
                async for chunk in llm_manager.stream_complete(
                    messages, 
                    provider_name=provider_name,
                    temperature=self.config.get("temperature", "0.1"),
                    max_tokens=self.config.get("max_tokens", 4000)
                ):
                    yield chunk
            else:
                response = await llm_manager.complete(
                    messages,
                    provider_name=provider_name,
                    temperature=self.config.get("temperature", "0.1"),
                    max_tokens=self.config.get("max_tokens", 4000)
                )
                yield response
                
        except Exception as e:
            logger.error("LLM response generation failed", error=str(e))
            await self._emit_event(EventType.AGENT_ERROR, {"error": str(e)})
            yield f"Sorry, I encountered an error: {str(e)}"
            
    def add_to_history(self, role: str, content: str):
        """Add a message to conversation history."""
        self.conversation_history.append({"role": role, "content": content})
        
        # Keep history manageable (last 20 messages)
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
