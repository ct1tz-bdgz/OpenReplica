"""
Server module for OpenReplica matching OpenHands exactly
"""
from .app import app
from .routes import *
from .shared import conversation_manager

__all__ = [
    "app",
    "conversation_manager"
]
