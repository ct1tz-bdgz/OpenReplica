"""Session database service."""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from openreplica.models.session import Session, SessionSchema, SessionCreateSchema, SessionUpdateSchema
from openreplica.core.logger import logger


class SessionService:
    """Service for session database operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def create_session(self, session_data: SessionCreateSchema) -> SessionSchema:
        """Create a new session."""
        session = Session(**session_data.dict())
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        
        logger.info("Session created", session_id=session.id)
        return SessionSchema.from_orm(session)
        
    async def get_session(self, session_id: str) -> Optional[SessionSchema]:
        """Get a session by ID."""
        stmt = select(Session).where(Session.id == session_id).options(
            selectinload(Session.conversations)
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if session:
            return SessionSchema.from_orm(session)
        return None
        
    async def list_sessions(self, user_id: Optional[str] = None, limit: int = 50) -> List[SessionSchema]:
        """List sessions with optional user filter."""
        stmt = select(Session).order_by(Session.created_at.desc()).limit(limit)
        
        if user_id:
            stmt = stmt.where(Session.user_id == user_id)
            
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()
        
        return [SessionSchema.from_orm(session) for session in sessions]
        
    async def update_session(self, session_id: str, update_data: SessionUpdateSchema) -> Optional[SessionSchema]:
        """Update a session."""
        stmt = update(Session).where(Session.id == session_id).values(
            **{k: v for k, v in update_data.dict().items() if v is not None}
        ).returning(Session)
        
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if session:
            await self.db.commit()
            await self.db.refresh(session)
            logger.info("Session updated", session_id=session_id)
            return SessionSchema.from_orm(session)
            
        return None
        
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        stmt = delete(Session).where(Session.id == session_id)
        result = await self.db.execute(stmt)
        
        if result.rowcount > 0:
            await self.db.commit()
            logger.info("Session deleted", session_id=session_id)
            return True
            
        return False
