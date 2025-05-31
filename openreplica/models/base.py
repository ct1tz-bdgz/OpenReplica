"""Base models for OpenReplica."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, DateTime, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from pydantic import BaseModel, Field
import uuid


Base = declarative_base()


class TimestampMixin:
    """Mixin for timestamp fields."""
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class UUIDMixin:
    """Mixin for UUID primary key."""
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))


class BaseSchema(BaseModel):
    """Base Pydantic schema."""
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UUIDSchema(BaseSchema):
    """Schema with UUID field."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
