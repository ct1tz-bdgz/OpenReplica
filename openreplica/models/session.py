"""Session models for OpenReplica."""

from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, String, Text, JSON, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship
from pydantic import Field
from openreplica.models.base import Base, TimestampMixin, UUIDMixin, BaseSchema, TimestampSchema, UUIDSchema


class Session(Base, UUIDMixin, TimestampMixin):
    """Database model for user sessions."""
    
    __tablename__ = "sessions"
    
    title = Column(String(255), nullable=False)
    description = Column(Text)
    user_id = Column(String(255), nullable=True)  # Optional user authentication
    status = Column(String(50), default="active")  # active, paused, completed, error
    
    # Configuration
    llm_provider = Column(String(50), nullable=False)
    llm_model = Column(String(100), nullable=False)
    temperature = Column(String(10), default="0.1")
    max_tokens = Column(Integer, default=4000)
    
    # Workspace info
    workspace_path = Column(String(500))
    git_repo = Column(String(500))
    branch = Column(String(100), default="main")
    
    # Session metadata
    metadata = Column(JSON, default=dict)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="session", cascade="all, delete-orphan")


class SessionSchema(UUIDSchema, TimestampSchema):
    """Pydantic schema for sessions."""
    
    title: str
    description: Optional[str] = None
    user_id: Optional[str] = None
    status: str = "active"
    
    llm_provider: str
    llm_model: str
    temperature: str = "0.1"
    max_tokens: int = 4000
    
    workspace_path: Optional[str] = None
    git_repo: Optional[str] = None
    branch: str = "main"
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionCreateSchema(BaseSchema):
    """Schema for creating sessions."""
    
    title: str
    description: Optional[str] = None
    llm_provider: str = "openai"
    llm_model: str = "gpt-4"
    temperature: str = "0.1"
    max_tokens: int = 4000
    git_repo: Optional[str] = None
    branch: str = "main"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionUpdateSchema(BaseSchema):
    """Schema for updating sessions."""
    
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
