"""
Base event classes for OpenReplica
"""
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of events in the system"""
    ACTION = "action"
    OBSERVATION = "observation"


class Event(BaseModel, ABC):
    """Base class for all events in the system"""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: EventType
    source: Optional[str] = None
    session_id: Optional[str] = None
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        pass
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary"""
        pass
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id})"
    
    def __repr__(self) -> str:
        return self.__str__()


class EventHandler(ABC):
    """Base class for event handlers"""
    
    @abstractmethod
    async def handle(self, event: Event) -> Optional[Event]:
        """Handle an event and optionally return a response event"""
        pass
    
    @abstractmethod
    def can_handle(self, event: Event) -> bool:
        """Check if this handler can process the given event"""
        pass


class EventBus:
    """Simple event bus for handling events"""
    
    def __init__(self):
        self.handlers: list[EventHandler] = []
        self.middleware: list[callable] = []
    
    def register_handler(self, handler: EventHandler) -> None:
        """Register an event handler"""
        self.handlers.append(handler)
    
    def register_middleware(self, middleware: callable) -> None:
        """Register middleware function"""
        self.middleware.append(middleware)
    
    async def publish(self, event: Event) -> list[Event]:
        """Publish an event to all appropriate handlers"""
        # Apply middleware
        for middleware in self.middleware:
            event = await middleware(event)
            if event is None:
                return []
        
        results = []
        for handler in self.handlers:
            if handler.can_handle(event):
                try:
                    result = await handler.handle(event)
                    if result:
                        results.append(result)
                except Exception as e:
                    # Log error but don't stop processing
                    print(f"Error in handler {handler.__class__.__name__}: {e}")
        
        return results


# Global event bus instance
event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    return event_bus
