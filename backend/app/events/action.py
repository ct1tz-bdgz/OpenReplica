"""
Action events for OpenReplica
"""
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import Field

from .base import Event, EventType


class ActionType(str, Enum):
    """Types of actions that can be performed"""
    # Code actions
    WRITE = "write"
    READ = "read"
    EDIT = "edit"
    DELETE = "delete"
    
    # Terminal actions
    RUN = "run"
    KILL = "kill"
    
    # Browser actions
    BROWSE = "browse"
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    
    # Agent actions
    THINK = "think"
    DELEGATE = "delegate"
    FINISH = "finish"
    
    # File system actions
    CREATE_FILE = "create_file"
    CREATE_DIRECTORY = "create_directory"
    MOVE = "move"
    COPY = "copy"
    
    # Search actions
    SEARCH = "search"
    GREP = "grep"


class Action(Event):
    """Base class for all actions"""
    
    event_type: EventType = EventType.ACTION
    action_type: ActionType
    thought: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Action":
        return cls(**data)


class WriteAction(Action):
    """Action to write content to a file"""
    
    action_type: ActionType = ActionType.WRITE
    path: str = Field(..., description="Path to the file to write")
    content: str = Field(..., description="Content to write to the file")
    encoding: str = Field(default="utf-8", description="File encoding")


class ReadAction(Action):
    """Action to read content from a file"""
    
    action_type: ActionType = ActionType.READ
    path: str = Field(..., description="Path to the file to read")
    start_line: Optional[int] = Field(None, description="Start line (1-indexed)")
    end_line: Optional[int] = Field(None, description="End line (1-indexed)")


class EditAction(Action):
    """Action to edit a file"""
    
    action_type: ActionType = ActionType.EDIT
    path: str = Field(..., description="Path to the file to edit")
    old_str: str = Field(..., description="String to replace")
    new_str: str = Field(..., description="Replacement string")


class RunAction(Action):
    """Action to run a command"""
    
    action_type: ActionType = ActionType.RUN
    command: str = Field(..., description="Command to execute")
    working_dir: Optional[str] = Field(None, description="Working directory")
    timeout: Optional[int] = Field(30, description="Timeout in seconds")
    background: bool = Field(False, description="Run in background")


class BrowseAction(Action):
    """Action to browse a URL"""
    
    action_type: ActionType = ActionType.BROWSE
    url: str = Field(..., description="URL to browse")
    wait_for: Optional[str] = Field(None, description="Element to wait for")


class ThinkAction(Action):
    """Action representing agent thinking/reasoning"""
    
    action_type: ActionType = ActionType.THINK
    content: str = Field(..., description="Thought content")


class DelegateAction(Action):
    """Action to delegate to another agent"""
    
    action_type: ActionType = ActionType.DELEGATE
    agent_type: str = Field(..., description="Type of agent to delegate to")
    task: str = Field(..., description="Task to delegate")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class FinishAction(Action):
    """Action to finish the current task"""
    
    action_type: ActionType = ActionType.FINISH
    outputs: Optional[Dict[str, Any]] = Field(None, description="Final outputs")
    success: bool = Field(True, description="Whether task was successful")
    message: Optional[str] = Field(None, description="Final message")


class SearchAction(Action):
    """Action to search for files or content"""
    
    action_type: ActionType = ActionType.SEARCH
    query: str = Field(..., description="Search query")
    path: Optional[str] = Field(None, description="Path to search in")
    file_pattern: Optional[str] = Field(None, description="File pattern to match")
    case_sensitive: bool = Field(False, description="Case sensitive search")


class CreateFileAction(Action):
    """Action to create a new file"""
    
    action_type: ActionType = ActionType.CREATE_FILE
    path: str = Field(..., description="Path for the new file")
    content: str = Field(default="", description="Initial content")


class CreateDirectoryAction(Action):
    """Action to create a new directory"""
    
    action_type: ActionType = ActionType.CREATE_DIRECTORY
    path: str = Field(..., description="Path for the new directory")


# Map action types to their corresponding classes
ACTION_TYPE_MAP = {
    ActionType.WRITE: WriteAction,
    ActionType.READ: ReadAction,
    ActionType.EDIT: EditAction,
    ActionType.RUN: RunAction,
    ActionType.BROWSE: BrowseAction,
    ActionType.THINK: ThinkAction,
    ActionType.DELEGATE: DelegateAction,
    ActionType.FINISH: FinishAction,
    ActionType.SEARCH: SearchAction,
    ActionType.CREATE_FILE: CreateFileAction,
    ActionType.CREATE_DIRECTORY: CreateDirectoryAction,
}


def create_action(action_type: ActionType, **kwargs) -> Action:
    """Factory function to create actions"""
    action_class = ACTION_TYPE_MAP.get(action_type, Action)
    return action_class(action_type=action_type, **kwargs)
