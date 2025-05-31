"""
Base runtime classes for OpenReplica
"""
import asyncio
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncGenerator
from pydantic import BaseModel, Field
from enum import Enum

from app.events.base import Event
from app.events.action import Action
from app.events.observation import Observation, create_observation, ObservationType
from app.core.logging import LoggerMixin


class RuntimeType(str, Enum):
    """Types of runtimes available"""
    DOCKER = "docker"
    LOCAL = "local"
    E2B = "e2b"


class RuntimeConfig(BaseModel):
    """Configuration for runtime environments"""
    
    # Basic settings
    runtime_type: RuntimeType = RuntimeType.DOCKER
    workspace_dir: str = "/workspace"
    timeout: int = 300  # 5 minutes default
    
    # Docker settings
    container_image: str = "python:3.12-slim"
    container_name_prefix: str = "openreplica"
    memory_limit: str = "2g"
    cpu_limit: str = "1"
    
    # Network settings
    enable_networking: bool = True
    dns_servers: List[str] = Field(default_factory=lambda: ["8.8.8.8", "8.8.4.4"])
    
    # Security settings
    user_id: int = 1000
    group_id: int = 1000
    read_only_root: bool = False
    
    # Environment variables
    environment: Dict[str, str] = Field(default_factory=dict)
    
    # File system settings
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_extensions: List[str] = Field(default_factory=lambda: [
        ".py", ".js", ".ts", ".html", ".css", ".json", ".md", ".txt", ".sh"
    ])
    
    # Command settings
    shell: str = "/bin/bash"
    working_directory: str = "/workspace"
    
    class Config:
        extra = "allow"


class Runtime(ABC, LoggerMixin):
    """Base class for all runtime environments"""
    
    def __init__(self, config: RuntimeConfig):
        self.config = config
        self.session_id: Optional[str] = None
        self.is_running = False
        self.container_id: Optional[str] = None
        
    @abstractmethod
    async def start(self, session_id: str) -> None:
        """Start the runtime environment"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the runtime environment"""
        pass
    
    @abstractmethod
    async def execute_action(self, action: Action) -> Observation:
        """Execute an action and return an observation"""
        pass
    
    @abstractmethod
    async def read_file(self, path: str) -> str:
        """Read file content"""
        pass
    
    @abstractmethod
    async def write_file(self, path: str, content: str) -> None:
        """Write file content"""
        pass
    
    @abstractmethod
    async def list_files(self, path: str = ".") -> List[Dict[str, Any]]:
        """List files in directory"""
        pass
    
    @abstractmethod
    async def run_command(self, command: str, background: bool = False) -> Observation:
        """Run shell command"""
        pass
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self.is_running:
            await self.stop()
    
    def get_status(self) -> Dict[str, Any]:
        """Get runtime status"""
        return {
            "runtime_type": self.config.runtime_type,
            "session_id": self.session_id,
            "is_running": self.is_running,
            "container_id": self.container_id,
            "workspace_dir": self.config.workspace_dir,
        }


class CommandResult(BaseModel):
    """Result from command execution"""
    
    command: str
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    pid: Optional[int] = None
    working_dir: str
    
    @property
    def success(self) -> bool:
        return self.exit_code == 0


class FileInfo(BaseModel):
    """Information about a file or directory"""
    
    name: str
    path: str
    size: int
    modified: float
    is_directory: bool
    permissions: str
    owner: str
    group: str


class RuntimeManager:
    """Manages multiple runtime instances"""
    
    def __init__(self):
        self.runtimes: Dict[str, Runtime] = {}
        self.active_sessions: Dict[str, str] = {}  # session_id -> runtime_id
    
    async def create_runtime(self, session_id: str, config: RuntimeConfig) -> Runtime:
        """Create and start a new runtime"""
        from app.runtime import create_runtime
        
        runtime = create_runtime(config.runtime_type.value, config)
        await runtime.start(session_id)
        
        runtime_id = f"{config.runtime_type}_{session_id}"
        self.runtimes[runtime_id] = runtime
        self.active_sessions[session_id] = runtime_id
        
        return runtime
    
    async def get_runtime(self, session_id: str) -> Optional[Runtime]:
        """Get runtime for session"""
        runtime_id = self.active_sessions.get(session_id)
        if runtime_id:
            return self.runtimes.get(runtime_id)
        return None
    
    async def stop_runtime(self, session_id: str) -> None:
        """Stop runtime for session"""
        runtime_id = self.active_sessions.get(session_id)
        if runtime_id and runtime_id in self.runtimes:
            runtime = self.runtimes[runtime_id]
            await runtime.stop()
            del self.runtimes[runtime_id]
            del self.active_sessions[session_id]
    
    async def cleanup_all(self) -> None:
        """Cleanup all runtimes"""
        for runtime in self.runtimes.values():
            await runtime.cleanup()
        self.runtimes.clear()
        self.active_sessions.clear()
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        return list(self.active_sessions.keys())


# Global runtime manager instance
_runtime_manager: Optional[RuntimeManager] = None


def get_runtime_manager() -> RuntimeManager:
    """Get the global runtime manager instance"""
    global _runtime_manager
    if _runtime_manager is None:
        _runtime_manager = RuntimeManager()
    return _runtime_manager


async def execute_action_in_runtime(session_id: str, action: Action) -> Observation:
    """Execute an action in the runtime for a session"""
    runtime_manager = get_runtime_manager()
    runtime = await runtime_manager.get_runtime(session_id)
    
    if not runtime:
        return create_observation(
            ObservationType.ERROR,
            error_message="No runtime available for session",
            success=False
        )
    
    try:
        return await runtime.execute_action(action)
    except Exception as e:
        return create_observation(
            ObservationType.ERROR,
            error_message=str(e),
            success=False
        )
