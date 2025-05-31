"""
MCP client implementation for OpenReplica
Manages connections to MCP servers and tool usage
"""
import asyncio
import json
import subprocess
from typing import Dict, Any, Optional, List, Union
import websockets
from urllib.parse import urlparse

from app.mcp.base import (
    MCPClient, MCPMessage, MCPTool, MCPResource, MCPPrompt,
    MCPWebSocketTransport, MCPStdioTransport, MCPMethod
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class MCPWebSocketClient(MCPClient):
    """WebSocket-based MCP client"""
    
    def __init__(self, name: str = "OpenReplica", version: str = "1.0.0"):
        super().__init__(name, version)
        self.websocket = None
        self.transport = None
        self.pending_requests: Dict[Union[str, int], asyncio.Future] = {}
        self.receive_task = None
        
    async def connect(self, server_uri: str) -> None:
        """Connect to MCP server via WebSocket"""
        try:
            self.websocket = await websockets.connect(server_uri)
            self.transport = MCPWebSocketTransport(self.websocket)
            
            # Start receive task
            self.receive_task = asyncio.create_task(self._receive_loop())
            
            # Initialize connection
            await self.initialize()
            
            logger.info(f"Connected to MCP server: {server_uri}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {server_uri}: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server"""
        try:
            if self.receive_task:
                self.receive_task.cancel()
                try:
                    await self.receive_task
                except asyncio.CancelledError:
                    pass
            
            if self.transport:
                await self.transport.close()
            
            # Cancel pending requests
            for future in self.pending_requests.values():
                future.cancel()
            self.pending_requests.clear()
            
            logger.info("Disconnected from MCP server")
            
        except Exception as e:
            logger.error(f"Error disconnecting from MCP server: {e}")
    
    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Send request to server"""
        request_id = self._next_request_id()
        
        message = MCPMessage(
            id=request_id,
            method=method,
            params=params or {}
        )
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        try:
            await self.transport.send(message)
            
            # Wait for response
            response = await asyncio.wait_for(future, timeout=30.0)
            
            if response.error:
                raise RuntimeError(f"MCP error: {response.error}")
            
            return response.result
            
        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            raise TimeoutError(f"MCP request timed out: {method}")
        except Exception as e:
            self.pending_requests.pop(request_id, None)
            raise
    
    async def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send notification to server"""
        message = MCPMessage(
            method=method,
            params=params or {}
        )
        
        await self.transport.send(message)
    
    async def _receive_loop(self) -> None:
        """Receive messages from server"""
        try:
            while True:
                message = await self.transport.receive()
                await self._handle_message(message)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in MCP receive loop: {e}")
    
    async def _handle_message(self, message: MCPMessage) -> None:
        """Handle incoming message"""
        if message.id and message.id in self.pending_requests:
            # Response to our request
            future = self.pending_requests.pop(message.id)
            future.set_result(message)
        elif message.method:
            # Notification or request from server
            logger.info(f"Received MCP notification: {message.method}")
        else:
            logger.warning(f"Unknown MCP message: {message}")


class MCPStdioClient(MCPClient):
    """Stdio-based MCP client for process communication"""
    
    def __init__(self, name: str = "OpenReplica", version: str = "1.0.0"):
        super().__init__(name, version)
        self.process = None
        self.transport = None
        self.pending_requests: Dict[Union[str, int], asyncio.Future] = {}
        self.receive_task = None
        
    async def connect(self, command: List[str]) -> None:
        """Connect to MCP server via process stdio"""
        try:
            self.process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self.transport = MCPStdioTransport(self.process)
            
            # Start receive task
            self.receive_task = asyncio.create_task(self._receive_loop())
            
            # Initialize connection
            await self.initialize()
            
            logger.info(f"Connected to MCP server via stdio: {' '.join(command)}")
            
        except Exception as e:
            logger.error(f"Failed to start MCP server process: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server"""
        try:
            if self.receive_task:
                self.receive_task.cancel()
                try:
                    await self.receive_task
                except asyncio.CancelledError:
                    pass
            
            if self.transport:
                await self.transport.close()
            
            # Cancel pending requests
            for future in self.pending_requests.values():
                future.cancel()
            self.pending_requests.clear()
            
            logger.info("Disconnected from MCP server")
            
        except Exception as e:
            logger.error(f"Error disconnecting from MCP server: {e}")
    
    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Send request to server"""
        request_id = self._next_request_id()
        
        message = MCPMessage(
            id=request_id,
            method=method,
            params=params or {}
        )
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        try:
            await self.transport.send(message)
            
            # Wait for response
            response = await asyncio.wait_for(future, timeout=30.0)
            
            if response.error:
                raise RuntimeError(f"MCP error: {response.error}")
            
            return response.result
            
        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            raise TimeoutError(f"MCP request timed out: {method}")
        except Exception as e:
            self.pending_requests.pop(request_id, None)
            raise
    
    async def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send notification to server"""
        message = MCPMessage(
            method=method,
            params=params or {}
        )
        
        await self.transport.send(message)
    
    async def _receive_loop(self) -> None:
        """Receive messages from server"""
        try:
            while True:
                message = await self.transport.receive()
                await self._handle_message(message)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in MCP receive loop: {e}")
    
    async def _handle_message(self, message: MCPMessage) -> None:
        """Handle incoming message"""
        if message.id and message.id in self.pending_requests:
            # Response to our request
            future = self.pending_requests.pop(message.id)
            future.set_result(message)
        elif message.method:
            # Notification or request from server
            logger.info(f"Received MCP notification: {message.method}")
        else:
            logger.warning(f"Unknown MCP message: {message}")


class MCPClientManager:
    """Manages multiple MCP clients and their connections"""
    
    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}
        self.tools_cache: Dict[str, List[MCPTool]] = {}
        self.resources_cache: Dict[str, List[MCPResource]] = {}
        
    async def add_websocket_client(self, name: str, server_uri: str) -> MCPClient:
        """Add a WebSocket MCP client"""
        if name in self.clients:
            raise ValueError(f"Client {name} already exists")
        
        client = MCPWebSocketClient()
        await client.connect(server_uri)
        
        self.clients[name] = client
        
        # Cache tools and resources
        await self._cache_client_data(name, client)
        
        return client
    
    async def add_stdio_client(self, name: str, command: List[str]) -> MCPClient:
        """Add a stdio MCP client"""
        if name in self.clients:
            raise ValueError(f"Client {name} already exists")
        
        client = MCPStdioClient()
        await client.connect(command)
        
        self.clients[name] = client
        
        # Cache tools and resources
        await self._cache_client_data(name, client)
        
        return client
    
    async def remove_client(self, name: str) -> None:
        """Remove an MCP client"""
        if name in self.clients:
            client = self.clients[name]
            await client.disconnect()
            del self.clients[name]
            
            # Clear cache
            self.tools_cache.pop(name, None)
            self.resources_cache.pop(name, None)
    
    async def get_client(self, name: str) -> Optional[MCPClient]:
        """Get an MCP client by name"""
        return self.clients.get(name)
    
    async def list_all_tools(self) -> Dict[str, List[MCPTool]]:
        """Get all tools from all clients"""
        all_tools = {}
        
        for client_name, tools in self.tools_cache.items():
            all_tools[client_name] = tools
        
        return all_tools
    
    async def find_tool(self, tool_name: str) -> Optional[tuple[str, MCPTool]]:
        """Find a tool by name across all clients"""
        for client_name, tools in self.tools_cache.items():
            for tool in tools:
                if tool.name == tool_name:
                    return client_name, tool
        return None
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool by name"""
        result = await self.find_tool(tool_name)
        if not result:
            raise ValueError(f"Tool not found: {tool_name}")
        
        client_name, tool = result
        client = self.clients[client_name]
        
        return await client.call_tool(tool_name, arguments)
    
    async def list_all_resources(self) -> Dict[str, List[MCPResource]]:
        """Get all resources from all clients"""
        all_resources = {}
        
        for client_name, resources in self.resources_cache.items():
            all_resources[client_name] = resources
        
        return all_resources
    
    async def read_resource(self, client_name: str, uri: str) -> Dict[str, Any]:
        """Read a resource from a specific client"""
        client = self.clients.get(client_name)
        if not client:
            raise ValueError(f"Client not found: {client_name}")
        
        return await client.read_resource(uri)
    
    async def refresh_cache(self, client_name: Optional[str] = None) -> None:
        """Refresh cached data for clients"""
        if client_name:
            if client_name in self.clients:
                await self._cache_client_data(client_name, self.clients[client_name])
        else:
            for name, client in self.clients.items():
                await self._cache_client_data(name, client)
    
    async def _cache_client_data(self, name: str, client: MCPClient) -> None:
        """Cache tools and resources for a client"""
        try:
            # Cache tools
            tools = await client.list_tools()
            self.tools_cache[name] = tools
            
            # Cache resources  
            resources = await client.list_resources()
            self.resources_cache[name] = resources
            
            logger.info(f"Cached {len(tools)} tools and {len(resources)} resources for client {name}")
            
        except Exception as e:
            logger.error(f"Failed to cache data for client {name}: {e}")
    
    async def close_all(self) -> None:
        """Close all MCP clients"""
        for name in list(self.clients.keys()):
            await self.remove_client(name)


# Global MCP client manager
_mcp_manager: Optional[MCPClientManager] = None


def get_mcp_manager() -> MCPClientManager:
    """Get the global MCP client manager"""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPClientManager()
    return _mcp_manager


async def setup_default_mcp_clients() -> None:
    """Setup default MCP clients for common tools"""
    manager = get_mcp_manager()
    
    # File system tools
    try:
        await manager.add_stdio_client(
            "filesystem",
            ["python", "-m", "mcp_filesystem_server"]
        )
    except Exception as e:
        logger.warning(f"Failed to setup filesystem MCP client: {e}")
    
    # Git tools
    try:
        await manager.add_stdio_client(
            "git",
            ["python", "-m", "mcp_git_server"]
        )
    except Exception as e:
        logger.warning(f"Failed to setup git MCP client: {e}")
    
    # Web search tools
    try:
        await manager.add_stdio_client(
            "search",
            ["python", "-m", "mcp_search_server"]
        )
    except Exception as e:
        logger.warning(f"Failed to setup search MCP client: {e}")
