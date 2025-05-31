"""Conversation database service."""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from openreplica.models.conversation import (
    Conversation, Message, ConversationSchema, MessageSchema,
    ConversationCreateSchema, MessageCreateSchema
)
from openreplica.core.logger import logger


class ConversationService:
    """Service for conversation database operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def create_conversation(
        self, 
        session_id: str, 
        conversation_data: ConversationCreateSchema
    ) -> ConversationSchema:
        """Create a new conversation."""
        conversation = Conversation(
            session_id=session_id,
            **conversation_data.dict()
        )
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        
        logger.info("Conversation created", conversation_id=conversation.id, session_id=session_id)
        return ConversationSchema.from_orm(conversation)
        
    async def get_conversation(self, conversation_id: str) -> Optional[ConversationSchema]:
        """Get a conversation by ID."""
        stmt = select(Conversation).where(Conversation.id == conversation_id).options(
            selectinload(Conversation.messages)
        )
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        if conversation:
            return ConversationSchema.from_orm(conversation)
        return None
        
    async def list_conversations(self, session_id: str) -> List[ConversationSchema]:
        """List conversations for a session."""
        stmt = select(Conversation).where(
            Conversation.session_id == session_id
        ).order_by(Conversation.created_at.desc())
        
        result = await self.db.execute(stmt)
        conversations = result.scalars().all()
        
        return [ConversationSchema.from_orm(conv) for conv in conversations]
        
    async def add_message(
        self, 
        conversation_id: str, 
        message_data: MessageCreateSchema
    ) -> MessageSchema:
        """Add a message to a conversation."""
        message = Message(
            conversation_id=conversation_id,
            **message_data.dict()
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        
        logger.info("Message added", message_id=message.id, conversation_id=conversation_id)
        return MessageSchema.from_orm(message)
        
    async def get_messages(self, conversation_id: str, limit: int = 100) -> List[MessageSchema]:
        """Get messages for a conversation."""
        stmt = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).limit(limit)
        
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        
        return [MessageSchema.from_orm(msg) for msg in messages]
