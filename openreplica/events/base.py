"""Base event classes for OpenReplica."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import uuid


class EventType(str, Enum):
    """Event types for the OpenReplica system."""
    
    # User events
    USER_MESSAGE = "user_message"
    USER_COMMAND = "user_command"
    
    # Agent events
    AGENT_THINKING = "agent_thinking"
    AGENT_ACTION = "agent_action"
    AGENT_RESPONSE = "agent_response"
    AGENT_ERROR = "agent_error"
    
    # Runtime events
    CODE_EXECUTION = "code_execution"
    CODE_RESULT = "code_result"
    FILE_CHANGE = "file_change"
    WORKSPACE_UPDATE = "workspace_update"
    
    # System events
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_LOST = "connection_lost"
    
    # LLM events
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    LLM_ERROR = "llm_error"


class Event(BaseModel):
    """Base event class."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: str
    conversation_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class UserMessageEvent(Event):
    """Event for user messages."""
    
    type: EventType = EventType.USER_MESSAGE
    
    def __init__(self, session_id: str, message: str, **kwargs):
        super().__init__(
            session_id=session_id,
            data={"message": message},
            **kwargs
        )


class AgentResponseEvent(Event):
    """Event for agent responses."""
    
    type: EventType = EventType.AGENT_RESPONSE
    
    def __init__(self, session_id: str, response: str, **kwargs):
        super().__init__(
            session_id=session_id,
            data={"response": response},
            **kwargs
        )


class CodeExecutionEvent(Event):
    """Event for code execution."""
    
    type: EventType = EventType.CODE_EXECUTION
    
    def __init__(self, session_id: str, code: str, language: str = "python", **kwargs):
        super().__init__(
            session_id=session_id,
            data={"code": code, "language": language},
            **kwargs
        )


class CodeResultEvent(Event):
    """Event for code execution results."""
    
    type: EventType = EventType.CODE_RESULT
    
    def __init__(self, session_id: str, result: str, success: bool = True, **kwargs):
        super().__init__(
            session_id=session_id,
            data={"result": result, "success": success},
            **kwargs
        )


class FileChangeEvent(Event):
    """Event for file changes."""
    
    type: EventType = EventType.FILE_CHANGE
    
    def __init__(self, session_id: str, filepath: str, action: str, content: Optional[str] = None, **kwargs):
        super().__init__(
            session_id=session_id,
            data={"filepath": filepath, "action": action, "content": content},
            **kwargs
        )
