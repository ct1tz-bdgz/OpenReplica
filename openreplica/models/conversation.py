"""Conversation models for OpenReplica."""

from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, String, Text, JSON, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from pydantic import Field
from openreplica.models.base import Base, TimestampMixin, UUIDMixin, BaseSchema, TimestampSchema, UUIDSchema


class Conversation(Base, UUIDMixin, TimestampMixin):
    """Database model for conversations within sessions."""
    
    __tablename__ = "conversations"
    
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(String(50), default="active")  # active, completed, error
    
    # Agent information
    agent_type = Column(String(100), default="coder")
    agent_config = Column(JSON, default=dict)
    
    # Conversation metadata
    metadata = Column(JSON, default=dict)
    
    # Relationships
    session = relationship("Session", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base, UUIDMixin, TimestampMixin):
    """Database model for messages in conversations."""
    
    __tablename__ = "messages"
    
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    message_type = Column(String(50), default="text")  # text, code, image, file
    
    # Message metadata
    tokens_used = Column(Integer, default=0)
    execution_time = Column(String(20))
    metadata = Column(JSON, default=dict)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class ConversationSchema(UUIDSchema, TimestampSchema):
    """Pydantic schema for conversations."""
    
    session_id: str
    title: str
    status: str = "active"
    agent_type: str = "coder"
    agent_config: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    messages: List["MessageSchema"] = Field(default_factory=list)


class MessageSchema(UUIDSchema, TimestampSchema):
    """Pydantic schema for messages."""
    
    conversation_id: str
    role: str
    content: str
    message_type: str = "text"
    tokens_used: int = 0
    execution_time: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MessageCreateSchema(BaseSchema):
    """Schema for creating messages."""
    
    role: str
    content: str
    message_type: str = "text"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationCreateSchema(BaseSchema):
    """Schema for creating conversations."""
    
    title: str
    agent_type: str = "coder"
    agent_config: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Update forward references
ConversationSchema.model_rebuild()
