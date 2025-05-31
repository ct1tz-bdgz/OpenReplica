"""
Base MCP (Model Context Protocol) classes for OpenReplica
"""
import asyncio
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union, Callable
from pydantic import BaseModel, Field
from enum import Enum
import uuid

from app.core.logging import LoggerMixin


class MCPMessageType(str, Enum):
    """MCP message types"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"


class MCPMethod(str, Enum):
    """Standard MCP methods"""
    INITIALIZE = "initialize"
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"
    COMPLETION = "completion/complete"
    SAMPLING = "sampling/createMessage"


class MCPMessage(BaseModel):
    """Base MCP message"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "allow"


class MCPError(BaseModel):
    """MCP error response"""
    code: int
    message: str
    data: Optional[Any] = None


class MCPToolParameter(BaseModel):
    """MCP tool parameter definition"""
    type: str
    description: str
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[str]] = None


class MCPTool(BaseModel):
    """MCP tool definition"""
    name: str
    description: str
    parameters: Dict[str, MCPToolParameter] = Field(default_factory=dict)
    
    def to_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function schema"""
        properties = {}
        required = []
        
        for param_name, param in self.parameters.items():
            prop = {
                "type": param.type,
                "description": param.description
            }
            
            if param.enum:
                prop["enum"] = param.enum
                
            if param.default is not None:
                prop["default"] = param.default
                
            properties[param_name] = prop
            
            if param.required:
                required.append(param_name)
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }


class MCPResource(BaseModel):
    """MCP resource definition"""
    uri: str
    name: str
    description: str
    mimeType: Optional[str] = None


class MCPPrompt(BaseModel):
    """MCP prompt template"""
    name: str
    description: str
    arguments: Optional[List[Dict[str, Any]]] = None


class MCPCapabilities(BaseModel):
    """MCP capabilities"""
    tools: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
    sampling: Optional[Dict[str, Any]] = None


class MCPImplementation(BaseModel):
    """MCP implementation info"""
    name: str
    version: str


class MCPInitializeParams(BaseModel):
    """MCP initialize parameters"""
    protocolVersion: str = "2024-11-05"
    capabilities: MCPCapabilities
    clientInfo: MCPImplementation


class MCPInitializeResult(BaseModel):
    """MCP initialize result"""
    protocolVersion: str = "2024-11-05"
    capabilities: MCPCapabilities
    serverInfo: MCPImplementation


class MCPClient(ABC, LoggerMixin):
    """Base MCP client interface"""
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.capabilities = MCPCapabilities()
        self.is_initialized = False
        self.request_id = 0
        
    @abstractmethod
    async def connect(self, server_uri: str) -> None:
        """Connect to MCP server"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from MCP server"""
        pass
    
    @abstractmethod
    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Send request to server"""
        pass
    
    @abstractmethod
    async def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send notification to server"""
        pass
    
    async def initialize(self) -> MCPInitializeResult:
        """Initialize MCP connection"""
        params = MCPInitializeParams(
            capabilities=self.capabilities,
            clientInfo=MCPImplementation(
                name=self.name,
                version=self.version
            )
        )
        
        result = await self.send_request(MCPMethod.INITIALIZE, params.dict())
        self.is_initialized = True
        return MCPInitializeResult(**result)
    
    async def list_tools(self) -> List[MCPTool]:
        """List available tools"""
        result = await self.send_request(MCPMethod.TOOLS_LIST)
        tools = []
        for tool_data in result.get("tools", []):
            tools.append(MCPTool(**tool_data))
        return tools
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool"""
        params = {
            "name": name,
            "arguments": arguments
        }
        return await self.send_request(MCPMethod.TOOLS_CALL, params)
    
    async def list_resources(self) -> List[MCPResource]:
        """List available resources"""
        result = await self.send_request(MCPMethod.RESOURCES_LIST)
        resources = []
        for resource_data in result.get("resources", []):
            resources.append(MCPResource(**resource_data))
        return resources
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource"""
        params = {"uri": uri}
        return await self.send_request(MCPMethod.RESOURCES_READ, params)
    
    async def list_prompts(self) -> List[MCPPrompt]:
        """List available prompts"""
        result = await self.send_request(MCPMethod.PROMPTS_LIST)
        prompts = []
        for prompt_data in result.get("prompts", []):
            prompts.append(MCPPrompt(**prompt_data))
        return prompts
    
    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get a prompt"""
        params = {"name": name}
        if arguments:
            params["arguments"] = arguments
        return await self.send_request(MCPMethod.PROMPTS_GET, params)
    
    def _next_request_id(self) -> int:
        """Get next request ID"""
        self.request_id += 1
        return self.request_id


class MCPServer(ABC, LoggerMixin):
    """Base MCP server interface"""
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.capabilities = MCPCapabilities()
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.prompts: Dict[str, MCPPrompt] = {}
        self.handlers: Dict[str, Callable] = {}
        self.is_running = False
        
    @abstractmethod
    async def start(self, host: str = "localhost", port: int = 3000) -> None:
        """Start the MCP server"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the MCP server"""
        pass
    
    @abstractmethod
    async def handle_message(self, message: MCPMessage) -> Optional[MCPMessage]:
        """Handle incoming message"""
        pass
    
    def register_tool(self, tool: MCPTool, handler: Callable) -> None:
        """Register a tool with handler"""
        self.tools[tool.name] = tool
        self.handlers[f"tool_{tool.name}"] = handler
        
    def register_resource(self, resource: MCPResource, handler: Callable) -> None:
        """Register a resource with handler"""
        self.resources[resource.uri] = resource
        self.handlers[f"resource_{resource.uri}"] = handler
        
    def register_prompt(self, prompt: MCPPrompt, handler: Callable) -> None:
        """Register a prompt with handler"""
        self.prompts[prompt.name] = prompt
        self.handlers[f"prompt_{prompt.name}"] = handler
    
    async def _handle_initialize(self, params: Dict[str, Any]) -> MCPInitializeResult:
        """Handle initialize request"""
        return MCPInitializeResult(
            capabilities=self.capabilities,
            serverInfo=MCPImplementation(
                name=self.name,
                version=self.version
            )
        )
    
    async def _handle_tools_list(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle tools/list request"""
        return {
            "tools": [tool.dict() for tool in self.tools.values()]
        }
    
    async def _handle_tools_call(self, params: Dict[str, Any]) -> Any:
        """Handle tools/call request"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tools:
            raise ValueError(f"Tool not found: {tool_name}")
        
        handler = self.handlers.get(f"tool_{tool_name}")
        if not handler:
            raise ValueError(f"No handler for tool: {tool_name}")
        
        return await handler(arguments)
    
    async def _handle_resources_list(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle resources/list request"""
        return {
            "resources": [resource.dict() for resource in self.resources.values()]
        }
    
    async def _handle_resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request"""
        uri = params.get("uri")
        
        if uri not in self.resources:
            raise ValueError(f"Resource not found: {uri}")
        
        handler = self.handlers.get(f"resource_{uri}")
        if not handler:
            raise ValueError(f"No handler for resource: {uri}")
        
        return await handler(params)
    
    async def _handle_prompts_list(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle prompts/list request"""
        return {
            "prompts": [prompt.dict() for prompt in self.prompts.values()]
        }
    
    async def _handle_prompts_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/get request"""
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if prompt_name not in self.prompts:
            raise ValueError(f"Prompt not found: {prompt_name}")
        
        handler = self.handlers.get(f"prompt_{prompt_name}")
        if not handler:
            raise ValueError(f"No handler for prompt: {prompt_name}")
        
        return await handler(arguments)


class MCPTransport(ABC):
    """Base transport for MCP communication"""
    
    @abstractmethod
    async def send(self, message: MCPMessage) -> None:
        """Send message"""
        pass
    
    @abstractmethod
    async def receive(self) -> MCPMessage:
        """Receive message"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close transport"""
        pass


class MCPWebSocketTransport(MCPTransport):
    """WebSocket transport for MCP"""
    
    def __init__(self, websocket):
        self.websocket = websocket
        
    async def send(self, message: MCPMessage) -> None:
        """Send message via WebSocket"""
        await self.websocket.send(message.json())
        
    async def receive(self) -> MCPMessage:
        """Receive message via WebSocket"""
        data = await self.websocket.recv()
        return MCPMessage.parse_raw(data)
        
    async def close(self) -> None:
        """Close WebSocket"""
        await self.websocket.close()


class MCPStdioTransport(MCPTransport):
    """Standard I/O transport for MCP"""
    
    def __init__(self, process):
        self.process = process
        
    async def send(self, message: MCPMessage) -> None:
        """Send message via stdio"""
        data = message.json() + "\n"
        self.process.stdin.write(data.encode())
        await self.process.stdin.drain()
        
    async def receive(self) -> MCPMessage:
        """Receive message via stdio"""
        line = await self.process.stdout.readline()
        data = line.decode().strip()
        return MCPMessage.parse_raw(data)
        
    async def close(self) -> None:
        """Close stdio"""
        self.process.terminate()
        await self.process.wait()
