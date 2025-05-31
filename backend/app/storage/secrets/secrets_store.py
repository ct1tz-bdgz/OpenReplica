"""
Secrets storage implementation for OpenReplica matching OpenHands exactly
"""
import json
import os
from abc import ABC, abstractmethod
from typing import Dict, Optional
from cryptography.fernet import Fernet
from pydantic import SecretStr

from app.core.logging import get_logger
from app.integrations.provider import CustomSecret, ProviderToken

logger = get_logger(__name__)


class SecretsStore(ABC):
    """Abstract base class for secrets storage"""
    
    @abstractmethod
    async def get_secret(self, key: str) -> Optional[str]:
        """Get a secret by key"""
        pass
    
    @abstractmethod
    async def set_secret(self, key: str, value: str) -> None:
        """Set a secret"""
        pass
    
    @abstractmethod
    async def delete_secret(self, key: str) -> None:
        """Delete a secret"""
        pass
    
    @abstractmethod
    async def list_secrets(self) -> list[str]:
        """List all secret keys"""
        pass
    
    @abstractmethod
    async def get_provider_tokens(self) -> Dict[str, ProviderToken]:
        """Get all provider tokens"""
        pass
    
    @abstractmethod
    async def set_provider_token(self, provider: str, token: ProviderToken) -> None:
        """Set provider token"""
        pass
    
    @abstractmethod
    async def get_custom_secrets(self) -> Dict[str, CustomSecret]:
        """Get all custom secrets"""
        pass
    
    @abstractmethod
    async def set_custom_secret(self, name: str, secret: CustomSecret) -> None:
        """Set custom secret"""
        pass


class EncryptedFileSecretsStore(SecretsStore):
    """Encrypted file-based secrets storage"""
    
    def __init__(self, user_id: str, base_path: str = "/tmp/openreplica/secrets"):
        self.user_id = user_id
        self.base_path = base_path
        self.secrets_file = os.path.join(base_path, f"{user_id}_secrets.enc")
        self.key_file = os.path.join(base_path, f"{user_id}_key.key")
        
        # Ensure directory exists
        os.makedirs(base_path, exist_ok=True)
        
        # Initialize encryption
        self.fernet = self._get_or_create_encryption_key()
    
    def _get_or_create_encryption_key(self) -> Fernet:
        """Get or create encryption key"""
        try:
            if os.path.exists(self.key_file):
                with open(self.key_file, 'rb') as f:
                    key = f.read()
            else:
                # Generate new key
                key = Fernet.generate_key()
                with open(self.key_file, 'wb') as f:
                    f.write(key)
                # Secure the key file
                os.chmod(self.key_file, 0o600)
            
            return Fernet(key)
            
        except Exception as e:
            logger.error(f"Error with encryption key: {e}")
            raise
    
    async def _load_secrets(self) -> Dict[str, str]:
        """Load and decrypt secrets from file"""
        try:
            if not os.path.exists(self.secrets_file):
                return {}
            
            with open(self.secrets_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.fernet.decrypt(encrypted_data)
            secrets = json.loads(decrypted_data.decode('utf-8'))
            
            return secrets
            
        except Exception as e:
            logger.error(f"Error loading secrets: {e}")
            return {}
    
    async def _save_secrets(self, secrets: Dict[str, str]) -> None:
        """Encrypt and save secrets to file"""
        try:
            data = json.dumps(secrets).encode('utf-8')
            encrypted_data = self.fernet.encrypt(data)
            
            with open(self.secrets_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Secure the secrets file
            os.chmod(self.secrets_file, 0o600)
            
        except Exception as e:
            logger.error(f"Error saving secrets: {e}")
            raise
    
    async def get_secret(self, key: str) -> Optional[str]:
        """Get a secret by key"""
        secrets = await self._load_secrets()
        return secrets.get(key)
    
    async def set_secret(self, key: str, value: str) -> None:
        """Set a secret"""
        secrets = await self._load_secrets()
        secrets[key] = value
        await self._save_secrets(secrets)
        logger.info(f"Secret '{key}' set for user {self.user_id}")
    
    async def delete_secret(self, key: str) -> None:
        """Delete a secret"""
        secrets = await self._load_secrets()
        if key in secrets:
            del secrets[key]
            await self._save_secrets(secrets)
            logger.info(f"Secret '{key}' deleted for user {self.user_id}")
    
    async def list_secrets(self) -> list[str]:
        """List all secret keys"""
        secrets = await self._load_secrets()
        return list(secrets.keys())
    
    async def get_provider_tokens(self) -> Dict[str, ProviderToken]:
        """Get all provider tokens"""
        secrets = await self._load_secrets()
        tokens = {}
        
        for key, value in secrets.items():
            if key.startswith('provider_'):
                provider = key.replace('provider_', '')
                try:
                    token_data = json.loads(value)
                    tokens[provider] = ProviderToken.from_value(token_data)
                except Exception as e:
                    logger.warning(f"Error parsing provider token {provider}: {e}")
        
        return tokens
    
    async def set_provider_token(self, provider: str, token: ProviderToken) -> None:
        """Set provider token"""
        key = f"provider_{provider}"
        value = json.dumps({
            'token': token.token.get_secret_value() if token.token else None,
            'user_id': token.user_id,
            'host': token.host
        })
        await self.set_secret(key, value)
    
    async def get_custom_secrets(self) -> Dict[str, CustomSecret]:
        """Get all custom secrets"""
        secrets = await self._load_secrets()
        custom_secrets = {}
        
        for key, value in secrets.items():
            if key.startswith('custom_'):
                name = key.replace('custom_', '')
                try:
                    secret_data = json.loads(value)
                    custom_secrets[name] = CustomSecret.from_value(secret_data)
                except Exception as e:
                    logger.warning(f"Error parsing custom secret {name}: {e}")
        
        return custom_secrets
    
    async def set_custom_secret(self, name: str, secret: CustomSecret) -> None:
        """Set custom secret"""
        key = f"custom_{name}"
        value = json.dumps({
            'secret': secret.secret.get_secret_value(),
            'description': secret.description
        })
        await self.set_secret(key, value)


class MockSecretsStore(SecretsStore):
    """Mock secrets store for development"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self._secrets: Dict[str, str] = {}
    
    async def get_secret(self, key: str) -> Optional[str]:
        """Get a secret by key"""
        return self._secrets.get(key)
    
    async def set_secret(self, key: str, value: str) -> None:
        """Set a secret"""
        self._secrets[key] = value
        logger.info(f"Mock secret '{key}' set for user {self.user_id}")
    
    async def delete_secret(self, key: str) -> None:
        """Delete a secret"""
        if key in self._secrets:
            del self._secrets[key]
            logger.info(f"Mock secret '{key}' deleted for user {self.user_id}")
    
    async def list_secrets(self) -> list[str]:
        """List all secret keys"""
        return list(self._secrets.keys())
    
    async def get_provider_tokens(self) -> Dict[str, ProviderToken]:
        """Get all provider tokens"""
        tokens = {}
        for key, value in self._secrets.items():
            if key.startswith('provider_'):
                provider = key.replace('provider_', '')
                try:
                    token_data = json.loads(value)
                    tokens[provider] = ProviderToken.from_value(token_data)
                except Exception:
                    pass
        return tokens
    
    async def set_provider_token(self, provider: str, token: ProviderToken) -> None:
        """Set provider token"""
        key = f"provider_{provider}"
        value = json.dumps({
            'token': token.token.get_secret_value() if token.token else None,
            'user_id': token.user_id,
            'host': token.host
        })
        self._secrets[key] = value
    
    async def get_custom_secrets(self) -> Dict[str, CustomSecret]:
        """Get all custom secrets"""
        custom_secrets = {}
        for key, value in self._secrets.items():
            if key.startswith('custom_'):
                name = key.replace('custom_', '')
                try:
                    secret_data = json.loads(value)
                    custom_secrets[name] = CustomSecret.from_value(secret_data)
                except Exception:
                    pass
        return custom_secrets
    
    async def set_custom_secret(self, name: str, secret: CustomSecret) -> None:
        """Set custom secret"""
        key = f"custom_{name}"
        value = json.dumps({
            'secret': secret.secret.get_secret_value(),
            'description': secret.description
        })
        self._secrets[key] = value


class InMemorySecretsStore(SecretsStore):
    """In-memory secrets store (not persistent)"""
    
    _stores: Dict[str, Dict[str, str]] = {}
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        if user_id not in self._stores:
            self._stores[user_id] = {}
    
    async def get_secret(self, key: str) -> Optional[str]:
        """Get a secret by key"""
        return self._stores[self.user_id].get(key)
    
    async def set_secret(self, key: str, value: str) -> None:
        """Set a secret"""
        self._stores[self.user_id][key] = value
    
    async def delete_secret(self, key: str) -> None:
        """Delete a secret"""
        if key in self._stores[self.user_id]:
            del self._stores[self.user_id][key]
    
    async def list_secrets(self) -> list[str]:
        """List all secret keys"""
        return list(self._stores[self.user_id].keys())
    
    async def get_provider_tokens(self) -> Dict[str, ProviderToken]:
        """Get all provider tokens"""
        tokens = {}
        for key, value in self._stores[self.user_id].items():
            if key.startswith('provider_'):
                provider = key.replace('provider_', '')
                try:
                    token_data = json.loads(value)
                    tokens[provider] = ProviderToken.from_value(token_data)
                except Exception:
                    pass
        return tokens
    
    async def set_provider_token(self, provider: str, token: ProviderToken) -> None:
        """Set provider token"""
        key = f"provider_{provider}"
        value = json.dumps({
            'token': token.token.get_secret_value() if token.token else None,
            'user_id': token.user_id,
            'host': token.host
        })
        self._stores[self.user_id][key] = value
    
    async def get_custom_secrets(self) -> Dict[str, CustomSecret]:
        """Get all custom secrets"""
        custom_secrets = {}
        for key, value in self._stores[self.user_id].items():
            if key.startswith('custom_'):
                name = key.replace('custom_', '')
                try:
                    secret_data = json.loads(value)
                    custom_secrets[name] = CustomSecret.from_value(secret_data)
                except Exception:
                    pass
        return custom_secrets
    
    async def set_custom_secret(self, name: str, secret: CustomSecret) -> None:
        """Set custom secret"""
        key = f"custom_{name}"
        value = json.dumps({
            'secret': secret.secret.get_secret_value(),
            'description': secret.description
        })
        self._stores[self.user_id][key] = value


def get_secrets_store(user_id: str, store_type: str = "encrypted_file") -> SecretsStore:
    """Factory function to get secrets store"""
    if store_type == "encrypted_file":
        return EncryptedFileSecretsStore(user_id)
    elif store_type == "mock":
        return MockSecretsStore(user_id)
    elif store_type == "memory":
        return InMemorySecretsStore(user_id)
    else:
        raise ValueError(f"Unknown store type: {store_type}")
