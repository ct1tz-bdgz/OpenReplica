"""
WebSocket routes for OpenReplica matching OpenHands exactly
"""
import json
import time
from datetime import datetime
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.events.serialization.event import event_to_dict, event_from_dict
from app.server.shared import conversation_manager
from app.server.user_auth import get_user_id

logger = get_logger(__name__)

app = APIRouter()

# Track active WebSocket connections
active_connections: Dict[str, Set[WebSocket]] = {}


class ConnectionManager:
    """Manager for WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, conversation_id: str):
        """Accept WebSocket connection and add to conversation"""
        await websocket.accept()
        
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = set()
        
        self.active_connections[conversation_id].add(websocket)
        logger.info(f"WebSocket connected to conversation {conversation_id}")
    
    def disconnect(self, websocket: WebSocket, conversation_id: str):
        """Remove WebSocket connection"""
        if conversation_id in self.active_connections:
            self.active_connections[conversation_id].discard(websocket)
            
            # Clean up empty sets
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]
        
        logger.info(f"WebSocket disconnected from conversation {conversation_id}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific WebSocket"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def broadcast_to_conversation(self, message: str, conversation_id: str):
        """Broadcast message to all connections in a conversation"""
        if conversation_id in self.active_connections:
            disconnected = set()
            
            for websocket in self.active_connections[conversation_id]:
                try:
                    await websocket.send_text(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to websocket: {e}")
                    disconnected.add(websocket)
            
            # Remove disconnected websockets
            for websocket in disconnected:
                self.active_connections[conversation_id].discard(websocket)
    
    async def send_event(self, event: dict, conversation_id: str):
        """Send event to all connections in a conversation"""
        message = json.dumps({
            "type": "event",
            "data": event
        })
        await self.broadcast_to_conversation(message, conversation_id)
    
    async def send_status_update(self, status: str, conversation_id: str, data: dict = None):
        """Send status update to all connections in a conversation"""
        message = json.dumps({
            "type": "status",
            "status": status,
            "data": data or {}
        })
        await self.broadcast_to_conversation(message, conversation_id)


manager = ConnectionManager()


@app.websocket("/ws/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: str,
    user_id: str = Depends(get_user_id)
):
    """WebSocket endpoint for real-time conversation updates"""
    await manager.connect(websocket, conversation_id)
    
    try:
        # Send initial connection message
        await manager.send_personal_message(
            json.dumps({
                "type": "connection",
                "status": "connected",
                "conversation_id": conversation_id,
                "user_id": user_id
            }),
            websocket
        )
        
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_websocket_message(message, conversation_id, websocket)
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    json.dumps({
                        "type": "error",
                        "error": "Invalid JSON message"
                    }),
                    websocket
                )
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await manager.send_personal_message(
                    json.dumps({
                        "type": "error",
                        "error": str(e)
                    }),
                    websocket
                )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, conversation_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, conversation_id)


async def handle_websocket_message(message: dict, conversation_id: str, websocket: WebSocket):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")
    
    if message_type == "ping":
        # Respond to ping with pong
        await manager.send_personal_message(
            json.dumps({"type": "pong"}),
            websocket
        )
    
    elif message_type == "user_message":
        # Handle user message
        content = message.get("content", "")
        
        # Send user message event to conversation
        user_event = {
            "id": f"user_{int(time.time())}",
            "type": "user_message",
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "conversation_id": conversation_id
        }
        
        # Broadcast to all connections
        await manager.send_event(user_event, conversation_id)
        
        # Send to conversation manager for processing
        conversation_manager.send_to_event_stream(conversation_id, user_event)
    
    elif message_type == "action":
        # Handle action request
        action_data = message.get("action", {})
        
        # Send action to conversation manager
        conversation_manager.send_to_event_stream(conversation_id, {
            "type": "action",
            "action": action_data,
            "conversation_id": conversation_id
        })
    
    elif message_type == "subscribe_events":
        # Subscribe to specific event types
        event_types = message.get("event_types", [])
        
        # Store subscription info (implementation would depend on requirements)
        await manager.send_personal_message(
            json.dumps({
                "type": "subscription_confirmed",
                "event_types": event_types
            }),
            websocket
        )
    
    else:
        # Unknown message type
        await manager.send_personal_message(
            json.dumps({
                "type": "error",
                "error": f"Unknown message type: {message_type}"
            }),
            websocket
        )


@app.post("/ws/broadcast/{conversation_id}")
async def broadcast_message(
    conversation_id: str,
    message: dict,
    user_id: str = Depends(get_user_id)
) -> JSONResponse:
    """Broadcast a message to all WebSocket connections for a conversation"""
    try:
        await manager.broadcast_to_conversation(
            json.dumps(message),
            conversation_id
        )
        
        return JSONResponse({
            "success": True,
            "message": "Message broadcasted successfully"
        })
        
    except Exception as e:
        logger.error(f"Error broadcasting message: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Error broadcasting message: {e}"}
        )


@app.get("/ws/status/{conversation_id}")
async def get_websocket_status(
    conversation_id: str,
    user_id: str = Depends(get_user_id)
) -> JSONResponse:
    """Get WebSocket connection status for a conversation"""
    try:
        connection_count = len(manager.active_connections.get(conversation_id, set()))
        
        return JSONResponse({
            "conversation_id": conversation_id,
            "active_connections": connection_count,
            "status": "active" if connection_count > 0 else "inactive"
        })
        
    except Exception as e:
        logger.error(f"Error getting WebSocket status: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Error getting WebSocket status: {e}"}
        )


@app.post("/ws/send-event/{conversation_id}")
async def send_event_to_websockets(
    conversation_id: str,
    event: dict,
    user_id: str = Depends(get_user_id)
) -> JSONResponse:
    """Send an event to all WebSocket connections for a conversation"""
    try:
        await manager.send_event(event, conversation_id)
        
        return JSONResponse({
            "success": True,
            "message": "Event sent successfully"
        })
        
    except Exception as e:
        logger.error(f"Error sending event to WebSockets: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Error sending event: {e}"}
        )


@app.post("/ws/status-update/{conversation_id}")
async def send_status_update(
    conversation_id: str,
    status_data: dict,
    user_id: str = Depends(get_user_id)
) -> JSONResponse:
    """Send a status update to all WebSocket connections for a conversation"""
    try:
        status = status_data.get("status", "unknown")
        data = status_data.get("data", {})
        
        await manager.send_status_update(status, conversation_id, data)
        
        return JSONResponse({
            "success": True,
            "message": "Status update sent successfully"
        })
        
    except Exception as e:
        logger.error(f"Error sending status update: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Error sending status update: {e}"}
        )


# Make manager available for other modules
def get_websocket_manager():
    """Get the WebSocket manager instance"""
    return manager


# Integration with conversation manager
def setup_websocket_integration():
    """Setup integration between WebSocket manager and conversation manager"""
    
    async def on_event(conversation_id: str, event: dict):
        """Called when conversation manager has new event"""
        await manager.send_event(event, conversation_id)
    
    async def on_status_change(conversation_id: str, status: str, data: dict = None):
        """Called when conversation status changes"""
        await manager.send_status_update(status, conversation_id, data)
    
    # Register callbacks with conversation manager
    if hasattr(conversation_manager, 'register_event_callback'):
        conversation_manager.register_event_callback(on_event)
        conversation_manager.register_status_callback(on_status_change)


# Initialize integration on import
setup_websocket_integration()
