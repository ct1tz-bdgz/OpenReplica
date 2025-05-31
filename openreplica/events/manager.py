"""Event manager for OpenReplica."""

import asyncio
from typing import Dict, List, Callable, Awaitable
from openreplica.events.base import Event, EventType
from openreplica.core.logger import logger


class EventManager:
    """Manages events and WebSocket connections."""
    
    def __init__(self):
        self.connections: Dict[str, List] = {}  # session_id -> list of websockets
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        
    def add_connection(self, session_id: str, websocket):
        """Add a WebSocket connection for a session."""
        if session_id not in self.connections:
            self.connections[session_id] = []
        self.connections[session_id].append(websocket)
        logger.info("WebSocket connected", session_id=session_id)
        
    def remove_connection(self, session_id: str, websocket):
        """Remove a WebSocket connection."""
        if session_id in self.connections:
            try:
                self.connections[session_id].remove(websocket)
                if not self.connections[session_id]:
                    del self.connections[session_id]
                logger.info("WebSocket disconnected", session_id=session_id)
            except ValueError:
                pass
                
    def register_handler(self, event_type: EventType, handler: Callable[[Event], Awaitable[None]]):
        """Register an event handler."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        
    async def emit_event(self, event: Event):
        """Emit an event to all relevant connections and handlers."""
        # Send to WebSocket connections
        await self._send_to_websockets(event)
        
        # Call registered handlers
        await self._call_handlers(event)
        
    async def _send_to_websockets(self, event: Event):
        """Send event to WebSocket connections."""
        if event.session_id in self.connections:
            connections = self.connections[event.session_id].copy()
            for websocket in connections:
                try:
                    await websocket.send_json(event.dict())
                except Exception as e:
                    logger.error("Failed to send event to WebSocket", error=str(e))
                    self.remove_connection(event.session_id, websocket)
                    
    async def _call_handlers(self, event: Event):
        """Call registered event handlers."""
        if event.type in self.event_handlers:
            for handler in self.event_handlers[event.type]:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error("Event handler failed", event_type=event.type, error=str(e))


# Global event manager instance
event_manager = EventManager()
