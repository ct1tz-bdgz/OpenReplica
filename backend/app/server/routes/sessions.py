"""
Session management API routes
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid

from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

# In-memory store for demo (use database in production)
active_sessions: Dict[str, Dict[str, Any]] = {}


class CreateSessionRequest(BaseModel):
    workspace_name: Optional[str] = None
    agent_type: str = "codeact"
    llm_provider: str = "openai"
    llm_model: str = "gpt-4"


class SessionResponse(BaseModel):
    session_id: str
    workspace_name: str
    agent_type: str
    llm_provider: str
    llm_model: str
    status: str
    created_at: datetime
    last_activity: datetime
    message_count: int


class SessionMessage(BaseModel):
    message_id: str
    content: str
    role: str  # "user" or "assistant"
    timestamp: datetime
    event_type: Optional[str] = None


@router.post("/create")
async def create_session(request: CreateSessionRequest) -> SessionResponse:
    """Create a new session"""
    session_id = str(uuid.uuid4())
    workspace_name = request.workspace_name or f"workspace_{session_id[:8]}"
    
    session_data = {
        "session_id": session_id,
        "workspace_name": workspace_name,
        "agent_type": request.agent_type,
        "llm_provider": request.llm_provider,
        "llm_model": request.llm_model,
        "status": "active",
        "created_at": datetime.utcnow(),
        "last_activity": datetime.utcnow(),
        "messages": [],
        "events": [],
        "agent_id": None
    }
    
    active_sessions[session_id] = session_data
    
    logger.info(
        "Session created",
        session_id=session_id,
        workspace_name=workspace_name,
        agent_type=request.agent_type
    )
    
    return SessionResponse(
        session_id=session_id,
        workspace_name=workspace_name,
        agent_type=request.agent_type,
        llm_provider=request.llm_provider,
        llm_model=request.llm_model,
        status="active",
        created_at=session_data["created_at"],
        last_activity=session_data["last_activity"],
        message_count=0
    )


@router.get("/{session_id}")
async def get_session(session_id: str) -> SessionResponse:
    """Get session information"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    
    return SessionResponse(
        session_id=session_id,
        workspace_name=session["workspace_name"],
        agent_type=session["agent_type"],
        llm_provider=session["llm_provider"],
        llm_model=session["llm_model"],
        status=session["status"],
        created_at=session["created_at"],
        last_activity=session["last_activity"],
        message_count=len(session["messages"])
    )


@router.get("/")
async def list_sessions() -> Dict[str, List[SessionResponse]]:
    """List all active sessions"""
    sessions = []
    for session_id, session_data in active_sessions.items():
        sessions.append(SessionResponse(
            session_id=session_id,
            workspace_name=session_data["workspace_name"],
            agent_type=session_data["agent_type"],
            llm_provider=session_data["llm_provider"],
            llm_model=session_data["llm_model"],
            status=session_data["status"],
            created_at=session_data["created_at"],
            last_activity=session_data["last_activity"],
            message_count=len(session_data["messages"])
        ))
    
    return {"sessions": sessions}


@router.delete("/{session_id}")
async def delete_session(session_id: str) -> Dict[str, str]:
    """Delete a session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Mark as inactive first
    active_sessions[session_id]["status"] = "deleted"
    
    # Remove from active sessions
    del active_sessions[session_id]
    
    logger.info("Session deleted", session_id=session_id)
    
    return {"message": f"Session {session_id} deleted successfully"}


@router.get("/{session_id}/messages")
async def get_session_messages(session_id: str) -> Dict[str, List[SessionMessage]]:
    """Get messages for a session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    messages = []
    
    for msg in session["messages"]:
        messages.append(SessionMessage(**msg))
    
    return {"messages": messages}


@router.post("/{session_id}/messages")
async def add_session_message(
    session_id: str, 
    content: str,
    role: str = "user"
) -> SessionMessage:
    """Add a message to a session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if role not in ["user", "assistant"]:
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'assistant'")
    
    session = active_sessions[session_id]
    
    message = {
        "message_id": str(uuid.uuid4()),
        "content": content,
        "role": role,
        "timestamp": datetime.utcnow(),
        "event_type": None
    }
    
    session["messages"].append(message)
    session["last_activity"] = datetime.utcnow()
    
    logger.info(
        "Message added to session",
        session_id=session_id,
        role=role,
        content_length=len(content)
    )
    
    return SessionMessage(**message)


@router.get("/{session_id}/events")
async def get_session_events(session_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Get events for a session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    return {"events": session["events"]}


@router.post("/{session_id}/events")
async def add_session_event(
    session_id: str,
    event_data: Dict[str, Any]
) -> Dict[str, str]:
    """Add an event to a session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow(),
        **event_data
    }
    
    session["events"].append(event)
    session["last_activity"] = datetime.utcnow()
    
    logger.info(
        "Event added to session",
        session_id=session_id,
        event_type=event_data.get("event_type", "unknown")
    )
    
    return {"message": "Event added successfully"}


def get_session_by_id(session_id: str) -> Dict[str, Any]:
    """Dependency to get session by ID"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return active_sessions[session_id]
