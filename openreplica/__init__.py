"""
OpenReplica - A beautiful replica of OpenHands with enhanced UI.

This package provides an AI-powered coding assistant with:
- Advanced AI agents for code generation and assistance
- Secure Docker-based runtime environment
- Real-time WebSocket communication
- Modern web interface
- Multi-LLM provider support
"""

__version__ = "1.0.0"
__author__ = "OpenReplica Team"
__email__ = "team@openreplica.dev"

from openreplica.core.config import settings
from openreplica.core.logger import logger

__all__ = ["settings", "logger"]
