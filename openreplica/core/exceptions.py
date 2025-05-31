"""Custom exceptions for OpenReplica."""

from typing import Any, Dict, Optional


class OpenReplicaError(Exception):
    """Base exception for OpenReplica."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(OpenReplicaError):
    """Configuration-related errors."""
    pass


class RuntimeError(OpenReplicaError):
    """Runtime execution errors."""
    pass


class LLMError(OpenReplicaError):
    """LLM provider errors."""
    pass


class SecurityError(OpenReplicaError):
    """Security-related errors."""
    pass


class WorkspaceError(OpenReplicaError):
    """Workspace and file system errors."""
    pass


class SessionError(OpenReplicaError):
    """Session management errors."""
    pass


class AgentError(OpenReplicaError):
    """AI agent errors."""
    pass
