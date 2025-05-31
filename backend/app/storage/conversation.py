"""
Conversation storage for OpenReplica
"""
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import sqlite3
import asyncio
from threading import Lock

from app.core.config import get_settings
from app.core.logging import get_logger
from app.events.base import Event
from app.events.serialization import serialize_for_storage, deserialize_from_storage

logger = get_logger(__name__)


class ConversationStorage:
    """Handles storage and retrieval of conversation data"""
    
    def __init__(self):
        self.settings = get_settings()
        self.db_path = "openreplica_conversations.db"
        self.lock = Lock()
    
    async def initialize(self):
        """Initialize the storage system"""
        # Create database and tables
        await self._create_tables()
        logger.info("Conversation storage initialized")
    
    async def _create_tables(self):
        """Create database tables"""
        def create_tables():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    workspace_name TEXT,
                    agent_type TEXT,
                    llm_provider TEXT,
                    llm_model TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            # Messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT,
                    metadata TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                )
            """)
            
            # Events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_data TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations (session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages (conversation_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_conversation_id ON events (conversation_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_session_id ON events (session_id)")
            
            conn.commit()
            conn.close()
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, create_tables)
    
    async def create_conversation(self, 
                                session_id: str,
                                workspace_name: str,
                                agent_type: str,
                                llm_provider: str,
                                llm_model: str,
                                metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new conversation"""
        def create():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            conversation_id = f"conv_{session_id}_{int(datetime.utcnow().timestamp())}"
            
            cursor.execute("""
                INSERT INTO conversations 
                (id, session_id, workspace_name, agent_type, llm_provider, llm_model, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                conversation_id,
                session_id,
                workspace_name,
                agent_type,
                llm_provider,
                llm_model,
                json.dumps(metadata) if metadata else None
            ))
            
            conn.commit()
            conn.close()
            return conversation_id
        
        loop = asyncio.get_event_loop()
        conversation_id = await loop.run_in_executor(None, create)
        
        logger.info("Conversation created", conversation_id=conversation_id, session_id=session_id)
        return conversation_id
    
    async def add_message(self,
                         conversation_id: str,
                         role: str,
                         content: str,
                         event_type: Optional[str] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a message to a conversation"""
        def add():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            message_id = f"msg_{int(datetime.utcnow().timestamp() * 1000000)}"
            
            cursor.execute("""
                INSERT INTO messages 
                (id, conversation_id, role, content, event_type, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                message_id,
                conversation_id,
                role,
                content,
                event_type,
                json.dumps(metadata) if metadata else None
            ))
            
            # Update conversation timestamp
            cursor.execute("""
                UPDATE conversations 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (conversation_id,))
            
            conn.commit()
            conn.close()
            return message_id
        
        loop = asyncio.get_event_loop()
        message_id = await loop.run_in_executor(None, add)
        
        logger.info("Message added", message_id=message_id, conversation_id=conversation_id)
        return message_id
    
    async def add_event(self,
                       conversation_id: str,
                       event: Event) -> str:
        """Add an event to a conversation"""
        def add():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            event_data = serialize_for_storage(event)
            
            cursor.execute("""
                INSERT INTO events 
                (id, conversation_id, event_type, event_data, session_id)
                VALUES (?, ?, ?, ?, ?)
            """, (
                event.id,
                conversation_id,
                event.event_type.value,
                json.dumps(event_data),
                event.session_id
            ))
            
            conn.commit()
            conn.close()
            return event.id
        
        loop = asyncio.get_event_loop()
        event_id = await loop.run_in_executor(None, add)
        
        logger.info("Event added", event_id=event_id, conversation_id=conversation_id)
        return event_id
    
    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID"""
        def get():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM conversations WHERE id = ?
            """, (conversation_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return dict(row)
            return None
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, get)
    
    async def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a conversation"""
        def get():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM messages 
                WHERE conversation_id = ? 
                ORDER BY timestamp ASC
            """, (conversation_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, get)
    
    async def get_conversation_events(self, conversation_id: str) -> List[Event]:
        """Get all events for a conversation"""
        def get():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM events 
                WHERE conversation_id = ? 
                ORDER BY timestamp ASC
            """, (conversation_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            events = []
            for row in rows:
                try:
                    event_data = json.loads(row["event_data"])
                    event = deserialize_from_storage(event_data)
                    events.append(event)
                except Exception as e:
                    logger.error("Failed to deserialize event", error=str(e), event_id=row["id"])
            
            return events
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, get)
    
    async def list_conversations(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List conversations, optionally filtered by session"""
        def list_convs():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if session_id:
                cursor.execute("""
                    SELECT * FROM conversations 
                    WHERE session_id = ? 
                    ORDER BY updated_at DESC
                """, (session_id,))
            else:
                cursor.execute("""
                    SELECT * FROM conversations 
                    ORDER BY updated_at DESC
                """)
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, list_convs)
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its data"""
        def delete():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Delete in reverse dependency order
            cursor.execute("DELETE FROM events WHERE conversation_id = ?", (conversation_id,))
            cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            return deleted_count > 0
        
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(None, delete)
        
        if success:
            logger.info("Conversation deleted", conversation_id=conversation_id)
        
        return success
    
    async def close(self):
        """Close storage connections"""
        logger.info("Conversation storage closed")
