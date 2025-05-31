"""
WebSocket API routes for real-time communication
"""
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.websockets import WebSocketState
import json

from app.core.logging import get_logger
from app.server.websocket.manager import get_socket_manager

router = APIRouter()
logger = get_logger(__name__)


@router.websocket("/connect/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time communication"""
    socket_manager = get_socket_manager()
    
    try:
        await websocket.accept()
        await socket_manager.connect(websocket, session_id)
        
        logger.info("WebSocket connected", session_id=session_id)
        
        # Send welcome message
        await socket_manager.send_to_session(session_id, {
            "type": "connected",
            "data": {"message": "Connected to OpenReplica"},
            "session_id": session_id
        })
        
        # Listen for messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                logger.info(
                    "WebSocket message received",
                    session_id=session_id,
                    message_type=message.get("type", "unknown")
                )
                
                # Handle different message types
                await handle_websocket_message(socket_manager, session_id, message)
                
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected", session_id=session_id)
                break
            except json.JSONDecodeError:
                await socket_manager.send_to_session(session_id, {
                    "type": "error",
                    "data": {"error": "Invalid JSON format"}
                })
            except Exception as e:
                logger.error("WebSocket error", error=str(e), session_id=session_id)
                await socket_manager.send_to_session(session_id, {
                    "type": "error",
                    "data": {"error": str(e)}
                })
                
    except Exception as e:
        logger.error("WebSocket connection error", error=str(e), session_id=session_id)
    finally:
        await socket_manager.disconnect(session_id)


async def handle_websocket_message(socket_manager, session_id: str, message: Dict[str, Any]):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")
    data = message.get("data", {})
    
    if message_type == "ping":
        # Respond to ping with pong
        await socket_manager.send_to_session(session_id, {
            "type": "pong",
            "data": {"timestamp": data.get("timestamp")}
        })
        
    elif message_type == "user_message":
        # Handle user messages (would integrate with agent system)
        content = data.get("content", "")
        
        # Echo back for now (in real implementation, send to agent)
        await socket_manager.send_to_session(session_id, {
            "type": "agent_message",
            "data": {
                "content": f"Received: {content}",
                "role": "assistant"
            }
        })
        
    elif message_type == "start_agent":
        # Start agent execution
        agent_type = data.get("agent_type", "codeact")
        
        await socket_manager.send_to_session(session_id, {
            "type": "agent_started",
            "data": {
                "agent_type": agent_type,
                "status": "Agent starting..."
            }
        })
        
    elif message_type == "stop_agent":
        # Stop agent execution
        await socket_manager.send_to_session(session_id, {
            "type": "agent_stopped",
            "data": {
                "status": "Agent stopped"
            }
        })
        
    elif message_type == "file_operation":
        # Handle file operations
        operation = data.get("operation")
        
        await socket_manager.send_to_session(session_id, {
            "type": "file_operation_result",
            "data": {
                "operation": operation,
                "status": "completed",
                "message": f"File operation '{operation}' completed"
            }
        })
        
    else:
        # Unknown message type
        await socket_manager.send_to_session(session_id, {
            "type": "error",
            "data": {"error": f"Unknown message type: {message_type}"}
        })


@router.get("/status")
async def websocket_status() -> Dict[str, Any]:
    """Get WebSocket service status"""
    socket_manager = get_socket_manager()
    
    return {
        "status": "active",
        "active_connections": socket_manager.get_connection_count(),
        "active_sessions": len(socket_manager.sessions)
    }
