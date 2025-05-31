"""
WebSocket connection manager for OpenReplica
"""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        # Map of session_id to WebSocket connections
        self.sessions: Dict[str, List[WebSocket]] = {}
        # Map of WebSocket to session_id for cleanup
        self.connection_map: Dict[WebSocket, str] = {}
        
    async def connect(self, websocket: WebSocket, session_id: str):
        """Connect a WebSocket to a session"""
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        
        self.sessions[session_id].append(websocket)
        self.connection_map[websocket] = session_id
        
        logger.info(
            "WebSocket connection added",
            session_id=session_id,
            connections_for_session=len(self.sessions[session_id])
        )
    
    async def disconnect(self, session_id: str, websocket: Optional[WebSocket] = None):
        """Disconnect WebSocket(s) from a session"""
        if session_id in self.sessions:
            if websocket:
                # Remove specific connection
                if websocket in self.sessions[session_id]:
                    self.sessions[session_id].remove(websocket)
                if websocket in self.connection_map:
                    del self.connection_map[websocket]
            else:
                # Remove all connections for session
                for ws in self.sessions[session_id]:
                    if ws in self.connection_map:
                        del self.connection_map[ws]
                del self.sessions[session_id]
            
            # Clean up empty sessions
            if session_id in self.sessions and not self.sessions[session_id]:
                del self.sessions[session_id]
        
        logger.info("WebSocket disconnected", session_id=session_id)
    
    async def send_to_session(self, session_id: str, message: Dict[str, Any]):
        """Send message to all connections in a session"""
        if session_id not in self.sessions:
            logger.warning("Attempted to send to non-existent session", session_id=session_id)
            return
        
        message_str = json.dumps({
            **message,
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id
        })
        
        # Send to all connections in session
        disconnected = []
        for websocket in self.sessions[session_id]:
            try:
                await websocket.send_text(message_str)
            except Exception as e:
                logger.error("Failed to send WebSocket message", error=str(e))
                disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            await self.disconnect(session_id, websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected sessions"""
        for session_id in list(self.sessions.keys()):
            await self.send_to_session(session_id, message)
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return sum(len(connections) for connections in self.sessions.values())
    
    def get_session_connection_count(self, session_id: str) -> int:
        """Get number of connections for a specific session"""
        return len(self.sessions.get(session_id, []))
    
    async def send_event(self, session_id: str, event_type: str, data: Any):
        """Send an event to a session"""
        await self.send_to_session(session_id, {
            "type": "event",
            "event_type": event_type,
            "data": data
        })
    
    async def send_error(self, session_id: str, error: str, error_type: str = "error"):
        """Send an error message to a session"""
        await self.send_to_session(session_id, {
            "type": "error",
            "error_type": error_type,
            "data": {"error": error}
        })
    
    async def send_status(self, session_id: str, status: str, data: Any = None):
        """Send a status update to a session"""
        await self.send_to_session(session_id, {
            "type": "status",
            "status": status,
            "data": data or {}
        })


class SocketManager:
    """High-level socket manager with additional features"""
    
    def __init__(self, sio_server=None):
        self.connection_manager = ConnectionManager()
        self.sio_server = sio_server
        self.event_handlers = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Connect a WebSocket"""
        await self.connection_manager.connect(websocket, session_id)
    
    async def disconnect(self, session_id: str, websocket: Optional[WebSocket] = None):
        """Disconnect WebSocket(s)"""
        await self.connection_manager.disconnect(session_id, websocket)
    
    async def send_to_session(self, session_id: str, message: Dict[str, Any]):
        """Send message to session"""
        await self.connection_manager.send_to_session(session_id, message)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast to all sessions"""
        await self.connection_manager.broadcast(message)
    
    def get_connection_count(self) -> int:
        """Get total connection count"""
        return self.connection_manager.get_connection_count()
    
    @property
    def sessions(self) -> Dict[str, List[WebSocket]]:
        """Get sessions dict"""
        return self.connection_manager.sessions
    
    async def send_agent_event(self, session_id: str, event_data: Dict[str, Any]):
        """Send agent-related event"""
        await self.send_to_session(session_id, {
            "type": "agent_event",
            "data": event_data
        })
    
    async def send_file_event(self, session_id: str, file_data: Dict[str, Any]):
        """Send file-related event"""
        await self.send_to_session(session_id, {
            "type": "file_event", 
            "data": file_data
        })
    
    async def send_terminal_output(self, session_id: str, output: str):
        """Send terminal output"""
        await self.send_to_session(session_id, {
            "type": "terminal_output",
            "data": {"output": output}
        })
    
    def register_event_handler(self, event_type: str, handler):
        """Register custom event handler"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def handle_event(self, event_type: str, session_id: str, data: Any):
        """Handle custom events"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    await handler(session_id, data)
                except Exception as e:
                    logger.error("Event handler error", error=str(e), event_type=event_type)


# Global socket manager instance
_socket_manager: Optional[SocketManager] = None


def get_socket_manager() -> SocketManager:
    """Get the global socket manager instance"""
    global _socket_manager
    if _socket_manager is None:
        _socket_manager = SocketManager()
    return _socket_manager


def set_socket_manager(manager: SocketManager):
    """Set the global socket manager instance"""
    global _socket_manager
    _socket_manager = manager
