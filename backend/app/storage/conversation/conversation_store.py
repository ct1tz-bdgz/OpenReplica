"""
Conversation storage implementation for OpenReplica matching OpenHands exactly
"""
import json
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.core.logging import get_logger
from app.storage.data_models.settings import ConversationMetadata
from app.events.event import Event

logger = get_logger(__name__)


class ConversationStore(ABC):
    """Abstract base class for conversation storage"""
    
    @abstractmethod
    async def create_conversation(
        self,
        title: Optional[str] = None,
        agent_class: Optional[str] = None,
        llm_model: Optional[str] = None,
        selected_repository: Optional[str] = None,
        initial_message: Optional[str] = None,
    ) -> str:
        """Create a new conversation and return its ID"""
        pass
    
    @abstractmethod
    async def get_metadata(self, conversation_id: str) -> Optional[ConversationMetadata]:
        """Get conversation metadata"""
        pass
    
    @abstractmethod
    async def update_metadata(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        status: Optional[str] = None,
        selected_repository: Optional[str] = None,
        last_message: Optional[str] = None,
        **kwargs
    ) -> None:
        """Update conversation metadata"""
        pass
    
    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation"""
        pass
    
    @abstractmethod
    async def list_conversations(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[ConversationMetadata]:
        """List conversations for the user"""
        pass
    
    @abstractmethod
    async def add_event(self, conversation_id: str, event: Event) -> None:
        """Add an event to the conversation"""
        pass
    
    @abstractmethod
    async def get_events(
        self,
        conversation_id: str,
        start_id: Optional[int] = None,
        limit: Optional[int] = None,
        event_type: Optional[str] = None
    ) -> List[Event]:
        """Get events for a conversation"""
        pass
    
    @abstractmethod
    async def get_event_count(self, conversation_id: str) -> int:
        """Get total number of events in conversation"""
        pass
    
    @abstractmethod
    async def clear_events(self, conversation_id: str) -> None:
        """Clear all events from a conversation"""
        pass


class FileConversationStore(ConversationStore):
    """File-based conversation storage"""
    
    def __init__(self, user_id: str, base_path: str = "/tmp/openreplica/conversations"):
        self.user_id = user_id
        self.base_path = base_path
        self.user_path = os.path.join(base_path, user_id)
        
        # Ensure directory exists
        os.makedirs(self.user_path, exist_ok=True)
    
    def _get_conversation_path(self, conversation_id: str) -> str:
        """Get path for conversation directory"""
        return os.path.join(self.user_path, conversation_id)
    
    def _get_metadata_path(self, conversation_id: str) -> str:
        """Get path for conversation metadata file"""
        return os.path.join(self._get_conversation_path(conversation_id), "metadata.json")
    
    def _get_events_path(self, conversation_id: str) -> str:
        """Get path for conversation events file"""
        return os.path.join(self._get_conversation_path(conversation_id), "events.jsonl")
    
    async def create_conversation(
        self,
        title: Optional[str] = None,
        agent_class: Optional[str] = None,
        llm_model: Optional[str] = None,
        selected_repository: Optional[str] = None,
        initial_message: Optional[str] = None,
    ) -> str:
        """Create a new conversation and return its ID"""
        conversation_id = str(uuid.uuid4())
        conversation_path = self._get_conversation_path(conversation_id)
        
        # Create conversation directory
        os.makedirs(conversation_path, exist_ok=True)
        
        # Create metadata
        metadata = ConversationMetadata(
            conversation_id=conversation_id,
            title=title or "New Conversation",
            agent_class=agent_class or "CodeActAgent",
            llm_model=llm_model or "claude-3-5-sonnet-20241022",
            selected_repository=selected_repository,
            last_message=initial_message,
            message_count=1 if initial_message else 0,
        )
        
        # Save metadata
        await self._save_metadata(metadata)
        
        logger.info(f"Created conversation {conversation_id} for user {self.user_id}")
        return conversation_id
    
    async def get_metadata(self, conversation_id: str) -> Optional[ConversationMetadata]:
        """Get conversation metadata"""
        try:
            metadata_path = self._get_metadata_path(conversation_id)
            
            if not os.path.exists(metadata_path):
                return None
            
            with open(metadata_path, 'r') as f:
                data = json.load(f)
            
            return ConversationMetadata(**data)
            
        except Exception as e:
            logger.error(f"Error loading metadata for conversation {conversation_id}: {e}")
            return None
    
    async def _save_metadata(self, metadata: ConversationMetadata) -> None:
        """Save conversation metadata"""
        try:
            metadata_path = self._get_metadata_path(metadata.conversation_id)
            
            # Update timestamp
            metadata.updated_at = datetime.utcnow()
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata.model_dump(), f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Error saving metadata for conversation {metadata.conversation_id}: {e}")
            raise
    
    async def update_metadata(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        status: Optional[str] = None,
        selected_repository: Optional[str] = None,
        last_message: Optional[str] = None,
        **kwargs
    ) -> None:
        """Update conversation metadata"""
        metadata = await self.get_metadata(conversation_id)
        if not metadata:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Update fields
        if title is not None:
            metadata.title = title
        if status is not None:
            metadata.status = status
        if selected_repository is not None:
            metadata.selected_repository = selected_repository
        if last_message is not None:
            metadata.last_message = last_message
            metadata.message_count = (metadata.message_count or 0) + 1
        
        # Update any additional fields
        for key, value in kwargs.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)
        
        await self._save_metadata(metadata)
    
    async def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation"""
        try:
            conversation_path = self._get_conversation_path(conversation_id)
            
            if os.path.exists(conversation_path):
                import shutil
                shutil.rmtree(conversation_path)
                logger.info(f"Deleted conversation {conversation_id} for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Error deleting conversation {conversation_id}: {e}")
            raise
    
    async def list_conversations(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[ConversationMetadata]:
        """List conversations for the user"""
        try:
            conversations = []
            
            if not os.path.exists(self.user_path):
                return conversations
            
            # Get all conversation directories
            for item in os.listdir(self.user_path):
                item_path = os.path.join(self.user_path, item)
                if os.path.isdir(item_path):
                    metadata = await self.get_metadata(item)
                    if metadata:
                        # Filter by status if specified
                        if status is None or metadata.status == status:
                            conversations.append(metadata)
            
            # Sort by updated_at (most recent first)
            conversations.sort(key=lambda x: x.updated_at or datetime.min, reverse=True)
            
            # Apply pagination
            if offset:
                conversations = conversations[offset:]
            if limit:
                conversations = conversations[:limit]
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error listing conversations for user {self.user_id}: {e}")
            return []
    
    async def add_event(self, conversation_id: str, event: Event) -> None:
        """Add an event to the conversation"""
        try:
            events_path = self._get_events_path(conversation_id)
            
            # Serialize event to JSON
            event_data = {
                'id': getattr(event, 'id', str(uuid.uuid4())),
                'timestamp': getattr(event, 'timestamp', datetime.utcnow()).isoformat(),
                'type': type(event).__name__,
                'data': event.model_dump() if hasattr(event, 'model_dump') else str(event)
            }
            
            # Append to events file
            with open(events_path, 'a') as f:
                f.write(json.dumps(event_data) + '\n')
            
            # Update message count in metadata
            if hasattr(event, 'content'):
                await self.update_metadata(
                    conversation_id,
                    last_message=getattr(event, 'content', '')[:100]
                )
                
        except Exception as e:
            logger.error(f"Error adding event to conversation {conversation_id}: {e}")
            raise
    
    async def get_events(
        self,
        conversation_id: str,
        start_id: Optional[int] = None,
        limit: Optional[int] = None,
        event_type: Optional[str] = None
    ) -> List[Event]:
        """Get events for a conversation"""
        try:
            events_path = self._get_events_path(conversation_id)
            events = []
            
            if not os.path.exists(events_path):
                return events
            
            with open(events_path, 'r') as f:
                for line_num, line in enumerate(f):
                    if start_id and line_num < start_id:
                        continue
                    
                    try:
                        event_data = json.loads(line.strip())
                        
                        # Filter by event type if specified
                        if event_type and event_data.get('type') != event_type:
                            continue
                        
                        # Create mock event object
                        mock_event = MockEvent(event_data)
                        events.append(mock_event)
                        
                        if limit and len(events) >= limit:
                            break
                            
                    except json.JSONDecodeError:
                        continue
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting events for conversation {conversation_id}: {e}")
            return []
    
    async def get_event_count(self, conversation_id: str) -> int:
        """Get total number of events in conversation"""
        try:
            events_path = self._get_events_path(conversation_id)
            
            if not os.path.exists(events_path):
                return 0
            
            with open(events_path, 'r') as f:
                return sum(1 for _ in f)
                
        except Exception as e:
            logger.error(f"Error counting events for conversation {conversation_id}: {e}")
            return 0
    
    async def clear_events(self, conversation_id: str) -> None:
        """Clear all events from a conversation"""
        try:
            events_path = self._get_events_path(conversation_id)
            
            if os.path.exists(events_path):
                open(events_path, 'w').close()  # Truncate file
                
        except Exception as e:
            logger.error(f"Error clearing events for conversation {conversation_id}: {e}")
            raise


class MockConversationStore(ConversationStore):
    """Mock conversation store for development"""
    
    _conversations: Dict[str, Dict[str, ConversationMetadata]] = {}
    _events: Dict[str, Dict[str, List[Event]]] = {}
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        if user_id not in self._conversations:
            self._conversations[user_id] = {}
            self._events[user_id] = {}
    
    async def create_conversation(
        self,
        title: Optional[str] = None,
        agent_class: Optional[str] = None,
        llm_model: Optional[str] = None,
        selected_repository: Optional[str] = None,
        initial_message: Optional[str] = None,
    ) -> str:
        """Create a new conversation and return its ID"""
        conversation_id = str(uuid.uuid4())
        
        metadata = ConversationMetadata(
            conversation_id=conversation_id,
            title=title or "New Conversation",
            agent_class=agent_class or "CodeActAgent",
            llm_model=llm_model or "claude-3-5-sonnet-20241022",
            selected_repository=selected_repository,
            last_message=initial_message,
            message_count=1 if initial_message else 0,
        )
        
        self._conversations[self.user_id][conversation_id] = metadata
        self._events[self.user_id][conversation_id] = []
        
        logger.info(f"Mock created conversation {conversation_id} for user {self.user_id}")
        return conversation_id
    
    async def get_metadata(self, conversation_id: str) -> Optional[ConversationMetadata]:
        """Get conversation metadata"""
        return self._conversations[self.user_id].get(conversation_id)
    
    async def update_metadata(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        status: Optional[str] = None,
        selected_repository: Optional[str] = None,
        last_message: Optional[str] = None,
        **kwargs
    ) -> None:
        """Update conversation metadata"""
        metadata = self._conversations[self.user_id].get(conversation_id)
        if not metadata:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        if title is not None:
            metadata.title = title
        if status is not None:
            metadata.status = status
        if selected_repository is not None:
            metadata.selected_repository = selected_repository
        if last_message is not None:
            metadata.last_message = last_message
            metadata.message_count = (metadata.message_count or 0) + 1
        
        metadata.updated_at = datetime.utcnow()
    
    async def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation"""
        if conversation_id in self._conversations[self.user_id]:
            del self._conversations[self.user_id][conversation_id]
        if conversation_id in self._events[self.user_id]:
            del self._events[self.user_id][conversation_id]
    
    async def list_conversations(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[ConversationMetadata]:
        """List conversations for the user"""
        conversations = list(self._conversations[self.user_id].values())
        
        # Filter by status
        if status:
            conversations = [c for c in conversations if c.status == status]
        
        # Sort by updated_at
        conversations.sort(key=lambda x: x.updated_at or datetime.min, reverse=True)
        
        # Apply pagination
        if offset:
            conversations = conversations[offset:]
        if limit:
            conversations = conversations[:limit]
        
        return conversations
    
    async def add_event(self, conversation_id: str, event: Event) -> None:
        """Add an event to the conversation"""
        if conversation_id not in self._events[self.user_id]:
            self._events[self.user_id][conversation_id] = []
        
        self._events[self.user_id][conversation_id].append(event)
        
        # Update message count in metadata
        if hasattr(event, 'content'):
            await self.update_metadata(
                conversation_id,
                last_message=getattr(event, 'content', '')[:100]
            )
    
    async def get_events(
        self,
        conversation_id: str,
        start_id: Optional[int] = None,
        limit: Optional[int] = None,
        event_type: Optional[str] = None
    ) -> List[Event]:
        """Get events for a conversation"""
        events = self._events[self.user_id].get(conversation_id, [])
        
        # Apply start_id filter
        if start_id:
            events = events[start_id:]
        
        # Apply event type filter
        if event_type:
            events = [e for e in events if type(e).__name__ == event_type]
        
        # Apply limit
        if limit:
            events = events[:limit]
        
        return events
    
    async def get_event_count(self, conversation_id: str) -> int:
        """Get total number of events in conversation"""
        return len(self._events[self.user_id].get(conversation_id, []))
    
    async def clear_events(self, conversation_id: str) -> None:
        """Clear all events from a conversation"""
        if conversation_id in self._events[self.user_id]:
            self._events[self.user_id][conversation_id] = []


class MockEvent:
    """Mock event for file storage"""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.timestamp = datetime.fromisoformat(data.get('timestamp', datetime.utcnow().isoformat()))
        self.type = data.get('type')
        self.data = data.get('data', {})
        self.source = data.get('source', 'user')
        self.message = data.get('message', '')
        self.extras = data.get('extras', {})
        self.action = data.get('action')
        self.observation = data.get('observation')
        self.content = data.get('content', '')
    
    def dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'type': self.type,
            'data': self.data,
            'source': self.source,
            'message': self.message,
            'extras': self.extras,
            'action': self.action,
            'observation': self.observation,
            'content': self.content
        }


def get_conversation_store(user_id: str, store_type: str = "file") -> ConversationStore:
    """Factory function to get conversation store"""
    if store_type == "file":
        return FileConversationStore(user_id)
    elif store_type == "mock":
        return MockConversationStore(user_id)
    else:
        raise ValueError(f"Unknown store type: {store_type}")
