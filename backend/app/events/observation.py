"""
Observation events for OpenReplica
"""
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import Field

from .base import Event, EventType


class ObservationType(str, Enum):
    """Types of observations that can be made"""
    # File system observations
    FILE_READ = "file_read"
    FILE_WRITTEN = "file_written"
    FILE_DELETED = "file_deleted"
    DIRECTORY_CREATED = "directory_created"
    
    # Command observations
    COMMAND_RESULT = "command_result"
    COMMAND_ERROR = "command_error"
    
    # Browser observations
    BROWSER_PAGE_LOADED = "browser_page_loaded"
    BROWSER_ELEMENT_FOUND = "browser_element_found"
    BROWSER_ERROR = "browser_error"
    
    # Agent observations
    AGENT_FINISHED = "agent_finished"
    AGENT_ERROR = "agent_error"
    AGENT_DELEGATED = "agent_delegated"
    
    # Search observations
    SEARCH_RESULT = "search_result"
    
    # General observations
    ERROR = "error"
    SUCCESS = "success"
    NULL = "null"


class Observation(Event):
    """Base class for all observations"""
    
    event_type: EventType = EventType.OBSERVATION
    observation_type: ObservationType
    content: str = Field(default="", description="Observation content")
    success: bool = Field(True, description="Whether operation was successful")
    
    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Observation":
        return cls(**data)


class FileReadObservation(Observation):
    """Observation for file read operations"""
    
    observation_type: ObservationType = ObservationType.FILE_READ
    path: str = Field(..., description="Path of the file read")
    content: str = Field(..., description="File content")
    encoding: str = Field(default="utf-8", description="File encoding")
    size: int = Field(..., description="File size in bytes")


class FileWrittenObservation(Observation):
    """Observation for file write operations"""
    
    observation_type: ObservationType = ObservationType.FILE_WRITTEN
    path: str = Field(..., description="Path of the file written")
    size: int = Field(..., description="Number of bytes written")


class CommandResultObservation(Observation):
    """Observation for command execution results"""
    
    observation_type: ObservationType = ObservationType.COMMAND_RESULT
    command: str = Field(..., description="Command that was executed")
    exit_code: int = Field(..., description="Exit code of the command")
    stdout: str = Field(default="", description="Standard output")
    stderr: str = Field(default="", description="Standard error")
    working_dir: Optional[str] = Field(None, description="Working directory")
    execution_time: float = Field(..., description="Execution time in seconds")


class CommandErrorObservation(Observation):
    """Observation for command execution errors"""
    
    observation_type: ObservationType = ObservationType.COMMAND_ERROR
    command: str = Field(..., description="Command that failed")
    error_message: str = Field(..., description="Error message")
    exit_code: Optional[int] = Field(None, description="Exit code if available")
    success: bool = Field(default=False)


class BrowserPageLoadedObservation(Observation):
    """Observation for browser page loads"""
    
    observation_type: ObservationType = ObservationType.BROWSER_PAGE_LOADED
    url: str = Field(..., description="URL that was loaded")
    title: str = Field(default="", description="Page title")
    content: str = Field(default="", description="Page content")
    screenshot_path: Optional[str] = Field(None, description="Path to screenshot")


class BrowserElementFoundObservation(Observation):
    """Observation for finding browser elements"""
    
    observation_type: ObservationType = ObservationType.BROWSER_ELEMENT_FOUND
    selector: str = Field(..., description="CSS selector used")
    element_count: int = Field(..., description="Number of elements found")
    elements: List[Dict[str, Any]] = Field(default_factory=list, description="Element details")


class BrowserErrorObservation(Observation):
    """Observation for browser errors"""
    
    observation_type: ObservationType = ObservationType.BROWSER_ERROR
    error_message: str = Field(..., description="Browser error message")
    url: Optional[str] = Field(None, description="URL where error occurred")
    success: bool = Field(default=False)


class AgentFinishedObservation(Observation):
    """Observation for agent completion"""
    
    observation_type: ObservationType = ObservationType.AGENT_FINISHED
    agent_type: str = Field(..., description="Type of agent that finished")
    outputs: Optional[Dict[str, Any]] = Field(None, description="Agent outputs")
    message: Optional[str] = Field(None, description="Final message")


class AgentErrorObservation(Observation):
    """Observation for agent errors"""
    
    observation_type: ObservationType = ObservationType.AGENT_ERROR
    agent_type: str = Field(..., description="Type of agent that errored")
    error_message: str = Field(..., description="Error message")
    traceback: Optional[str] = Field(None, description="Error traceback")
    success: bool = Field(default=False)


class SearchResultObservation(Observation):
    """Observation for search results"""
    
    observation_type: ObservationType = ObservationType.SEARCH_RESULT
    query: str = Field(..., description="Search query")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Search results")
    total_results: int = Field(default=0, description="Total number of results")


class ErrorObservation(Observation):
    """General error observation"""
    
    observation_type: ObservationType = ObservationType.ERROR
    error_message: str = Field(..., description="Error message")
    error_type: Optional[str] = Field(None, description="Error type")
    traceback: Optional[str] = Field(None, description="Error traceback")
    success: bool = Field(default=False)


class SuccessObservation(Observation):
    """General success observation"""
    
    observation_type: ObservationType = ObservationType.SUCCESS
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data")


class NullObservation(Observation):
    """Null observation when no action is taken"""
    
    observation_type: ObservationType = ObservationType.NULL
    content: str = Field(default="No action taken", description="Observation content")


# Map observation types to their corresponding classes
OBSERVATION_TYPE_MAP = {
    ObservationType.FILE_READ: FileReadObservation,
    ObservationType.FILE_WRITTEN: FileWrittenObservation,
    ObservationType.COMMAND_RESULT: CommandResultObservation,
    ObservationType.COMMAND_ERROR: CommandErrorObservation,
    ObservationType.BROWSER_PAGE_LOADED: BrowserPageLoadedObservation,
    ObservationType.BROWSER_ELEMENT_FOUND: BrowserElementFoundObservation,
    ObservationType.BROWSER_ERROR: BrowserErrorObservation,
    ObservationType.AGENT_FINISHED: AgentFinishedObservation,
    ObservationType.AGENT_ERROR: AgentErrorObservation,
    ObservationType.SEARCH_RESULT: SearchResultObservation,
    ObservationType.ERROR: ErrorObservation,
    ObservationType.SUCCESS: SuccessObservation,
    ObservationType.NULL: NullObservation,
}


def create_observation(observation_type: ObservationType, **kwargs) -> Observation:
    """Factory function to create observations"""
    observation_class = OBSERVATION_TYPE_MAP.get(observation_type, Observation)
    return observation_class(observation_type=observation_type, **kwargs)
