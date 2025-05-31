"""
Shared components for OpenReplica server matching OpenHands exactly
"""
from typing import Any, Dict, Optional
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Global configuration
config = get_settings()


class ConversationManager:
    """Manager for conversation state and events"""
    
    def __init__(self):
        self.conversations: Dict[str, Any] = {}
        self.event_callbacks = []
        self.status_callbacks = []
    
    def register_event_callback(self, callback):
        """Register callback for new events"""
        self.event_callbacks.append(callback)
    
    def register_status_callback(self, callback):
        """Register callback for status changes"""
        self.status_callbacks.append(callback)
    
    async def send_to_event_stream(self, conversation_id: str, event: Dict[str, Any]):
        """Send event to event stream"""
        # Notify all registered callbacks
        for callback in self.event_callbacks:
            try:
                await callback(conversation_id, event)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")
    
    async def update_status(self, conversation_id: str, status: str, data: Dict[str, Any] = None):
        """Update conversation status"""
        # Notify all registered callbacks
        for callback in self.status_callbacks:
            try:
                await callback(conversation_id, status, data or {})
            except Exception as e:
                logger.error(f"Error in status callback: {e}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        logger.info("Conversation manager starting...")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        logger.info("Conversation manager shutting down...")


class ConversationStoreImpl:
    """Implementation of conversation store"""
    
    @classmethod
    async def get_instance(cls, config: Any, user_id: str):
        """Get conversation store instance for user"""
        # This would return the actual conversation store implementation
        # For now, return a mock implementation
        return MockConversationStore(user_id)


class MockConversationStore:
    """Mock conversation store for development"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.conversations = {}
    
    async def list_conversations(self):
        """List conversations for user"""
        return []
    
    async def get_metadata(self, conversation_id: str):
        """Get conversation metadata"""
        return None
    
    async def create_conversation(self, **kwargs):
        """Create new conversation"""
        import uuid
        conversation_id = str(uuid.uuid4())
        return conversation_id
    
    async def update_metadata(self, conversation_id: str, **kwargs):
        """Update conversation metadata"""
        pass
    
    async def delete_conversation(self, conversation_id: str):
        """Delete conversation"""
        pass
    
    async def get_events(self, conversation_id: str, **kwargs):
        """Get conversation events"""
        return []
    
    async def add_event(self, conversation_id: str, event: Any):
        """Add event to conversation"""
        pass


# Global conversation manager instance
conversation_manager = ConversationManager()
