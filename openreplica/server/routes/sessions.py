"""Session management routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from openreplica.database.connection import get_db
from openreplica.database.session import SessionService
from openreplica.models.session import SessionSchema, SessionCreateSchema, SessionUpdateSchema
from openreplica.runtime.manager import runtime_manager
from openreplica.core.logger import logger

router = APIRouter()


@router.post("/", response_model=SessionSchema, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: SessionCreateSchema,
    db: AsyncSession = Depends(get_db)
):
    """Create a new coding session."""
    service = SessionService(db)
    session = await service.create_session(session_data)
    
    # Create workspace for the session
    await runtime_manager.create_workspace(session.id)
    
    logger.info("Session created via API", session_id=session.id)
    return session


@router.get("/", response_model=List[SessionSchema])
async def list_sessions(
    user_id: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """List sessions with optional user filter."""
    service = SessionService(db)
    return await service.list_sessions(user_id=user_id, limit=limit)


@router.get("/{session_id}", response_model=SessionSchema)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a session by ID."""
    service = SessionService(db)
    session = await service.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
        
    return session


@router.patch("/{session_id}", response_model=SessionSchema)
async def update_session(
    session_id: str,
    update_data: SessionUpdateSchema,
    db: AsyncSession = Depends(get_db)
):
    """Update a session."""
    service = SessionService(db)
    session = await service.update_session(session_id, update_data)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
        
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a session."""
    service = SessionService(db)
    deleted = await service.delete_session(session_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Clean up workspace
    await runtime_manager.cleanup_workspace(session_id)
    
    logger.info("Session deleted via API", session_id=session_id)
