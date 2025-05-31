"""
Provider integrations for OpenReplica matching OpenHands exactly
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Annotated, Any, Coroutine, Literal, overload

from pydantic import (
    BaseModel,
    Field,
    SecretStr,
    WithJsonSchema,
)

from app.core.logging import get_logger
from app.events.action.action import Action
from app.events.action.commands import CmdRunAction
from app.events.stream import EventStream
from app.integrations.github.github_service import GithubServiceImpl
from app.integrations.gitlab.gitlab_service import GitLabServiceImpl
from app.integrations.service_types import (
    AuthenticationError,
    Branch,
    GitService,
    ProviderType,
    Repository,
    SuggestedTask,
    User,
)
from app.server.types import AppMode

logger = get_logger(__name__)


class ProviderToken(BaseModel):
    token: SecretStr | None = Field(default=None)
    user_id: str | None = Field(default=None)
    host: str | None = Field(default=None)

    model_config = {
        'frozen': True,  # Makes the entire model immutable
        'validate_assignment': True,
    }

    @classmethod
    def from_value(cls, token_value: ProviderToken | dict[str, str]) -> ProviderToken:
        """Factory method to create a ProviderToken from various input types"""
        if isinstance(token_value, cls):
            return token_value
        elif isinstance(token_value, dict):
            token_str = token_value.get('token', '')
            # Override with empty string if it was set to None
            # Cannot pass None to SecretStr
            if token_str is None:
                token_str = ''
            user_id = token_value.get('user_id')
            host = token_value.get('host')
            return cls(token=SecretStr(token_str), user_id=user_id, host=host)

        else:
            raise ValueError('Unsupported Provider token type')


class CustomSecret(BaseModel):
    secret: SecretStr = Field(default_factory=lambda: SecretStr(''))
    description: str = Field(default='')

    model_config = {
        'frozen': True,  # Makes the entire model immutable
        'validate_assignment': True,
    }

    @classmethod
    def from_value(cls, secret_value: CustomSecret | dict[str, str]) -> CustomSecret:
        """Factory method to create a CustomSecret from various input types"""
        if isinstance(secret_value, CustomSecret):
            return secret_value
        elif isinstance(secret_value, dict):
            secret = secret_value.get('secret')
            description = secret_value.get('description')
            return cls(secret=SecretStr(secret), description=description)

        else:
            raise ValueError('Unsupported Provider token type')


PROVIDER_TOKEN_TYPE = MappingProxyType[ProviderType, ProviderToken]
CUSTOM_SECRETS_TYPE = MappingProxyType[str, CustomSecret]
PROVIDER_TOKEN_TYPE_WITH_JSON_SCHEMA = Annotated[
    PROVIDER_TOKEN_TYPE,
    WithJsonSchema({'type': 'object', 'additionalProperties': {'type': 'string'}}),
]
CUSTOM_SECRETS_TYPE_WITH_JSON_SCHEMA = Annotated[
    CUSTOM_SECRETS_TYPE,
    WithJsonSchema({'type': 'object', 'additionalProperties': {'type': 'string'}}),
]


class ProviderHandler:
    def __init__(
        self,
        provider_tokens: PROVIDER_TOKEN_TYPE,
        external_auth_id: str | None = None,
        external_auth_token: SecretStr | None = None,
    ):
        self.provider_tokens = provider_tokens
        self.external_auth_id = external_auth_id
        self.external_auth_token = external_auth_token

    @overload
    def get_service(
        self, provider_type: Literal[ProviderType.GITHUB]
    ) -> GithubServiceImpl: ...

    @overload
    def get_service(
        self, provider_type: Literal[ProviderType.GITLAB]
    ) -> GitLabServiceImpl: ...

    @overload
    def get_service(self, provider_type: ProviderType) -> GitService: ...

    def get_service(self, provider_type: ProviderType) -> GitService:
        """Get service instance for the given provider type"""
        if provider_type == ProviderType.GITHUB:
            token = self._get_token_for_provider(provider_type)
            return GithubServiceImpl(token)
        elif provider_type == ProviderType.GITLAB:
            token = self._get_token_for_provider(provider_type)
            return GitLabServiceImpl(token)
        else:
            raise ValueError(f'Unsupported provider type: {provider_type}')

    def _get_token_for_provider(self, provider_type: ProviderType) -> ProviderToken:
        """Get token for the specified provider"""
        if provider_type not in self.provider_tokens:
            raise AuthenticationError(f'No token found for provider: {provider_type}')
        
        return self.provider_tokens[provider_type]

    async def list_repositories(
        self, provider_type: ProviderType
    ) -> list[Repository]:
        """List repositories for the given provider"""
        service = self.get_service(provider_type)
        return await service.list_repositories()

    async def get_repository(
        self, provider_type: ProviderType, repo_name: str
    ) -> Repository:
        """Get repository details"""
        service = self.get_service(provider_type)
        return await service.get_repository(repo_name)

    async def list_branches(
        self, provider_type: ProviderType, repo_name: str
    ) -> list[Branch]:
        """List branches for the repository"""
        service = self.get_service(provider_type)
        return await service.list_branches(repo_name)

    async def get_user(self, provider_type: ProviderType) -> User:
        """Get user information"""
        service = self.get_service(provider_type)
        return await service.get_user()

    async def get_suggested_tasks(
        self, provider_type: ProviderType, repo_name: str
    ) -> list[SuggestedTask]:
        """Get suggested tasks for the repository"""
        service = self.get_service(provider_type)
        return await service.get_suggested_tasks(repo_name)

    async def create_repository(
        self, provider_type: ProviderType, repo_name: str, private: bool = True
    ) -> Repository:
        """Create a new repository"""
        service = self.get_service(provider_type)
        return await service.create_repository(repo_name, private)

    async def fork_repository(
        self, provider_type: ProviderType, repo_name: str
    ) -> Repository:
        """Fork a repository"""
        service = self.get_service(provider_type)
        return await service.fork_repository(repo_name)

    async def create_pull_request(
        self,
        provider_type: ProviderType,
        repo_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = 'main'
    ) -> dict[str, Any]:
        """Create a pull request"""
        service = self.get_service(provider_type)
        return await service.create_pull_request(
            repo_name, title, body, head_branch, base_branch
        )

    def supports_provider(self, provider_type: ProviderType) -> bool:
        """Check if provider is supported and has valid token"""
        try:
            self._get_token_for_provider(provider_type)
            return True
        except AuthenticationError:
            return False

    def get_supported_providers(self) -> list[ProviderType]:
        """Get list of supported providers with valid tokens"""
        return [
            provider_type
            for provider_type in ProviderType
            if self.supports_provider(provider_type)
        ]


# Taviily integration for web search and browsing
class TavilyIntegration:
    """Integration with Taviily for web search and AI browsing"""
    
    def __init__(self, api_key: SecretStr | None = None):
        self.api_key = api_key
        self._client = None
    
    def is_configured(self) -> bool:
        """Check if Taviily is properly configured"""
        return self.api_key is not None
    
    async def search(
        self,
        query: str,
        search_depth: str = "basic",
        include_images: bool = False,
        include_answer: bool = True,
        max_results: int = 5
    ) -> dict[str, Any]:
        """
        Search the web using Taviily
        
        Args:
            query: Search query
            search_depth: "basic" or "advanced" 
            include_images: Whether to include images
            include_answer: Whether to include AI-generated answer
            max_results: Maximum number of results
            
        Returns:
            Search results with URLs, content, and answer
        """
        if not self.is_configured():
            raise ValueError("Taviily API key not configured")
        
        try:
            # Import here to avoid dependency issues if not installed
            from tavily import TavilyClient
            
            if self._client is None:
                self._client = TavilyClient(api_key=self.api_key.get_secret_value())
            
            response = await self._client.search(
                query=query,
                search_depth=search_depth,
                include_images=include_images,
                include_answer=include_answer,
                max_results=max_results
            )
            
            return response
            
        except ImportError:
            logger.error("Taviily client not installed. Install with: pip install tavily-python")
            raise ValueError("Taviily client not available")
        except Exception as e:
            logger.error(f"Taviily search failed: {e}")
            raise

    async def extract_content(self, urls: list[str]) -> dict[str, str]:
        """
        Extract content from URLs using Taviily
        
        Args:
            urls: List of URLs to extract content from
            
        Returns:
            Dictionary mapping URLs to extracted content
        """
        if not self.is_configured():
            raise ValueError("Taviily API key not configured")
        
        try:
            from tavily import TavilyClient
            
            if self._client is None:
                self._client = TavilyClient(api_key=self.api_key.get_secret_value())
            
            results = {}
            for url in urls:
                try:
                    content = await self._client.extract(url)
                    results[url] = content
                except Exception as e:
                    logger.warning(f"Failed to extract content from {url}: {e}")
                    results[url] = f"Error: {str(e)}"
            
            return results
            
        except ImportError:
            logger.error("Taviily client not installed. Install with: pip install tavily-python")
            raise ValueError("Taviily client not available")
        except Exception as e:
            logger.error(f"Taviily content extraction failed: {e}")
            raise


# OpenRouter integration for accessing hundreds of models
class OpenRouterIntegration:
    """Integration with OpenRouter for accessing multiple LLM providers"""
    
    def __init__(self, api_key: SecretStr | None = None):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
    
    def is_configured(self) -> bool:
        """Check if OpenRouter is properly configured"""
        return self.api_key is not None
    
    async def get_available_models(self) -> list[dict[str, Any]]:
        """
        Get list of available models from OpenRouter
        
        Returns:
            List of model information dictionaries
        """
        if not self.is_configured():
            return []
        
        try:
            import httpx
            
            headers = {
                "Authorization": f"Bearer {self.api_key.get_secret_value()}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=headers
                )
                response.raise_for_status()
                
                models_data = response.json()
                return models_data.get("data", [])
                
        except Exception as e:
            logger.error(f"Failed to fetch OpenRouter models: {e}")
            return []
    
    def get_model_config(self, model_id: str) -> dict[str, Any]:
        """
        Get OpenRouter configuration for a specific model
        
        Args:
            model_id: The OpenRouter model ID
            
        Returns:
            Configuration dictionary for LLMConfig
        """
        return {
            "model": model_id,
            "base_url": self.base_url,
            "api_key": self.api_key,
            "openrouter_site_url": "https://github.com/ct1tz-bdgz/OpenReplica",
            "openrouter_app_name": "OpenReplica"
        }
    
    async def get_model_info(self, model_id: str) -> dict[str, Any] | None:
        """
        Get detailed information about a specific model
        
        Args:
            model_id: The OpenRouter model ID
            
        Returns:
            Model information or None if not found
        """
        models = await self.get_available_models()
        for model in models:
            if model.get("id") == model_id:
                return model
        return None


# Provider model registry
PROVIDER_MODEL_REGISTRY = {
    "openai": {
        "models": [
            "gpt-4o",
            "gpt-4o-mini", 
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
            "o1-preview",
            "o1-mini",
            "o1-2024-12-17",
            "o3-mini-2025-01-31",
            "o3-mini",
            "o3-2025-04-16",
            "o4-mini-2025-04-16"
        ],
        "base_url": "https://api.openai.com/v1",
        "supports_vision": True,
        "supports_function_calling": True
    },
    "anthropic": {
        "models": [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-sonnet-20240620", 
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
            "claude-instant-1.2"
        ],
        "base_url": "https://api.anthropic.com",
        "supports_vision": True,
        "supports_function_calling": True
    },
    "google": {
        "models": [
            "gemini-pro",
            "gemini-pro-vision",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "palm-2-chat-bison",
            "palm-2-codechat-bison"
        ],
        "base_url": "https://generativelanguage.googleapis.com/v1",
        "supports_vision": True,
        "supports_function_calling": True
    },
    "cohere": {
        "models": [
            "command-r-plus",
            "command-r",
            "command-nightly",
            "command-light-nightly"
        ],
        "base_url": "https://api.cohere.ai/v1",
        "supports_vision": False,
        "supports_function_calling": True
    },
    "openrouter": {
        "models": [],  # Populated dynamically
        "base_url": "https://openrouter.ai/api/v1",
        "supports_vision": True,  # Depends on specific model
        "supports_function_calling": True  # Depends on specific model
    },
    "ollama": {
        "models": [
            "llama3.2",
            "llama3.1",
            "codellama",
            "mistral",
            "mixtral",
            "qwen2.5",
            "deepseek-coder",
            "phi3"
        ],
        "base_url": "http://localhost:11434",
        "supports_vision": False,
        "supports_function_calling": False
    },
    "together": {
        "models": [
            "meta-llama/Llama-3.1-405B-Instruct-Turbo",
            "meta-llama/Llama-3.1-70B-Instruct-Turbo",
            "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "Qwen/Qwen2.5-72B-Instruct-Turbo"
        ],
        "base_url": "https://api.together.xyz/v1",
        "supports_vision": False,
        "supports_function_calling": True
    },
    "replicate": {
        "models": [
            "meta/llama-2-70b-chat",
            "mistralai/mistral-7b-instruct-v0.1",
            "google-deepmind/gemma-7b-it"
        ],
        "base_url": "https://api.replicate.com/v1",
        "supports_vision": False,
        "supports_function_calling": False
    }
}


def get_provider_models(provider: str) -> list[str]:
    """Get available models for a provider"""
    return PROVIDER_MODEL_REGISTRY.get(provider, {}).get("models", [])


def get_provider_info(provider: str) -> dict[str, Any]:
    """Get provider information"""
    return PROVIDER_MODEL_REGISTRY.get(provider, {})


def get_all_providers() -> list[str]:
    """Get list of all supported providers"""
    return list(PROVIDER_MODEL_REGISTRY.keys())


def is_model_supported(provider: str, model: str) -> bool:
    """Check if a model is supported by a provider"""
    models = get_provider_models(provider)
    return model in models or provider == "openrouter"  # OpenRouter supports many models
