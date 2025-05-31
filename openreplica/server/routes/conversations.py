"""Conversation management routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from openreplica.database.connection import get_db
from openreplica.database.conversation import ConversationService
from openreplica.models.conversation import (
    ConversationSchema, ConversationCreateSchema, 
    MessageSchema, MessageCreateSchema
)

router = APIRouter()


@router.post("/{session_id}", response_model=ConversationSchema, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    session_id: str,
    conversation_data: ConversationCreateSchema,
    db: AsyncSession = Depends(get_db)
):
    """Create a new conversation in a session."""
    service = ConversationService(db)
    return await service.create_conversation(session_id, conversation_data)


@router.get("/{session_id}", response_model=List[ConversationSchema])
async def list_conversations(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """List conversations for a session."""
    service = ConversationService(db)
    return await service.list_conversations(session_id)


@router.get("/detail/{conversation_id}", response_model=ConversationSchema)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a conversation by ID."""
    service = ConversationService(db)
    conversation = await service.get_conversation(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
        
    return conversation


@router.post("/{conversation_id}/messages", response_model=MessageSchema, status_code=status.HTTP_201_CREATED)
async def add_message(
    conversation_id: str,
    message_data: MessageCreateSchema,
    db: AsyncSession = Depends(get_db)
):
    """Add a message to a conversation."""
    service = ConversationService(db)
    return await service.add_message(conversation_id, message_data)


@router.get("/{conversation_id}/messages", response_model=List[MessageSchema])
async def get_messages(
    conversation_id: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get messages for a conversation."""
    service = ConversationService(db)
    return await service.get_messages(conversation_id, limit)
