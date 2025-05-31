"""
Model Context Protocol (MCP) integration for OpenReplica
Enables LLMs to use tools and connect to external services
"""
from .base import MCPClient, MCPServer, MCPTool
from .client import MCPClientManager
from .tools import ToolRegistry, register_tool
from .integrations import get_mcp_integrations

__all__ = [
    "MCPClient",
    "MCPServer", 
    "MCPTool",
    "MCPClientManager",
    "ToolRegistry",
    "register_tool",
    "get_mcp_integrations"
]
