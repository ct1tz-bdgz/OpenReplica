"""WebSocket endpoints for real-time communication."""

import json
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from openreplica.database.connection import get_db
from openreplica.database.conversation import ConversationService
from openreplica.events.manager import event_manager
from openreplica.events.base import UserMessageEvent, EventType
from openreplica.agents.manager import agent_manager
from openreplica.models.conversation import MessageCreateSchema, ConversationCreateSchema
from openreplica.core.logger import logger

router = APIRouter()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str
):
    """WebSocket endpoint for real-time communication with agents."""
    await websocket.accept()
    event_manager.add_connection(session_id, websocket)
    
    try:
        # Get or create agent for this session
        agent = agent_manager.get_agent(session_id)
        if not agent:
            # Create default coder agent
            agent = agent_manager.create_agent(
                session_id=session_id,
                agent_type="coder",
                config={
                    "llm_provider": "openai",
                    "llm_model": "gpt-4",
                    "temperature": "0.1",
                    "max_tokens": 4000,
                    "workspace_path": f"./workspaces/{session_id}"
                }
            )
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            message_type = message_data.get("type", "message")
            content = message_data.get("content", "")
            conversation_id = message_data.get("conversation_id")
            
            if message_type == "message" and content.strip():
                # Emit user message event
                await event_manager.emit_event(
                    UserMessageEvent(session_id=session_id, message=content)
                )
                
                # Process message with agent and stream response
                full_response = ""
                await websocket.send_json({
                    "type": "agent_response_start",
                    "session_id": session_id
                })
                
                async for chunk in agent.process_message(content):
                    full_response += chunk
                    await websocket.send_json({
                        "type": "agent_response_chunk",
                        "content": chunk,
                        "session_id": session_id
                    })
                
                await websocket.send_json({
                    "type": "agent_response_end",
                    "session_id": session_id,
                    "full_response": full_response
                })
                
            elif message_type == "ping":
                # Health check
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": message_data.get("timestamp")
                })
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", session_id=session_id)
    except Exception as e:
        logger.error("WebSocket error", session_id=session_id, error=str(e))
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"An error occurred: {str(e)}"
            })
        except:
            pass
    finally:
        event_manager.remove_connection(session_id, websocket)


@router.websocket("/events/{session_id}")
async def events_websocket(
    websocket: WebSocket,
    session_id: str
):
    """WebSocket endpoint for receiving system events."""
    await websocket.accept()
    event_manager.add_connection(session_id, websocket)
    
    try:
        while True:
            # Keep connection alive and handle pings
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": message_data.get("timestamp")
                })
                
    except WebSocketDisconnect:
        logger.info("Events WebSocket disconnected", session_id=session_id)
    except Exception as e:
        logger.error("Events WebSocket error", session_id=session_id, error=str(e))
    finally:
        event_manager.remove_connection(session_id, websocket)
