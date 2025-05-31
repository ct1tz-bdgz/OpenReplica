"""
Settings storage implementation for OpenReplica matching OpenHands exactly
"""
import json
import os
from abc import ABC, abstractmethod
from typing import Optional

from app.core.logging import get_logger
from app.storage.data_models.settings import Settings

logger = get_logger(__name__)


class SettingsStore(ABC):
    """Abstract base class for settings storage"""
    
    @abstractmethod
    async def load(self) -> Optional[Settings]:
        """Load user settings"""
        pass
    
    @abstractmethod
    async def store(self, settings: Settings) -> None:
        """Store user settings"""
        pass
    
    @abstractmethod
    async def delete(self) -> None:
        """Delete user settings"""
        pass


class FileSettingsStore(SettingsStore):
    """File-based settings storage"""
    
    def __init__(self, user_id: str, base_path: str = "/tmp/openreplica/settings"):
        self.user_id = user_id
        self.base_path = base_path
        self.file_path = os.path.join(base_path, f"{user_id}.json")
        
        # Ensure directory exists
        os.makedirs(base_path, exist_ok=True)
    
    async def load(self) -> Optional[Settings]:
        """Load settings from file"""
        try:
            if not os.path.exists(self.file_path):
                return None
            
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            
            return Settings(**data)
            
        except Exception as e:
            logger.error(f"Error loading settings for user {self.user_id}: {e}")
            return None
    
    async def store(self, settings: Settings) -> None:
        """Store settings to file"""
        try:
            # Update timestamp
            settings.update_timestamp()
            
            # Convert to dict and handle SecretStr
            data = {}
            for field, value in settings.model_dump().items():
                if hasattr(value, 'get_secret_value'):
                    data[field] = value.get_secret_value()
                else:
                    data[field] = value
            
            # Write to file
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Settings stored for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Error storing settings for user {self.user_id}: {e}")
            raise
    
    async def delete(self) -> None:
        """Delete settings file"""
        try:
            if os.path.exists(self.file_path):
                os.remove(self.file_path)
                logger.info(f"Settings deleted for user {self.user_id}")
        except Exception as e:
            logger.error(f"Error deleting settings for user {self.user_id}: {e}")
            raise


class MockSettingsStore(SettingsStore):
    """Mock settings store for development"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self._settings = None
    
    async def load(self) -> Optional[Settings]:
        """Load mock settings"""
        if self._settings is None:
            # Return default settings
            return Settings(
                user_id=self.user_id,
                llm_model="claude-3-5-sonnet-20241022",
                agent_class="CodeActAgent",
                max_iterations=100,
                theme="dark",
                language="en"
            )
        return self._settings
    
    async def store(self, settings: Settings) -> None:
        """Store mock settings"""
        settings.user_id = self.user_id
        settings.update_timestamp()
        self._settings = settings
        logger.info(f"Mock settings stored for user {self.user_id}")
    
    async def delete(self) -> None:
        """Delete mock settings"""
        self._settings = None
        logger.info(f"Mock settings deleted for user {self.user_id}")


class DatabaseSettingsStore(SettingsStore):
    """Database-based settings storage"""
    
    def __init__(self, user_id: str, db_connection=None):
        self.user_id = user_id
        self.db = db_connection
    
    async def load(self) -> Optional[Settings]:
        """Load settings from database"""
        # Implementation would depend on database type
        # For now, return None
        return None
    
    async def store(self, settings: Settings) -> None:
        """Store settings to database"""
        # Implementation would depend on database type
        pass
    
    async def delete(self) -> None:
        """Delete settings from database"""
        # Implementation would depend on database type
        pass


def get_settings_store(user_id: str, store_type: str = "file") -> SettingsStore:
    """Factory function to get settings store"""
    if store_type == "file":
        return FileSettingsStore(user_id)
    elif store_type == "mock":
        return MockSettingsStore(user_id)
    elif store_type == "database":
        return DatabaseSettingsStore(user_id)
    else:
        raise ValueError(f"Unknown store type: {store_type}")
