"""LLM manager for OpenReplica."""

from typing import Dict, Optional, List, AsyncGenerator
from openreplica.core.config import settings
from openreplica.core.exceptions import LLMError, ConfigurationError
from openreplica.core.logger import logger
from openreplica.llm.providers import LLMProvider, OpenAIProvider, AnthropicProvider, LiteLLMProvider


class LLMManager:
    """Manages LLM providers and configurations."""
    
    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self._initialize_providers()
        
    def _initialize_providers(self):
        """Initialize available LLM providers."""
        # OpenAI provider
        if settings.openai_api_key:
            try:
                self.providers["openai"] = OpenAIProvider(
                    api_key=settings.openai_api_key,
                    model=settings.llm_model if settings.llm_model.startswith("gpt") else "gpt-4"
                )
                logger.info("OpenAI provider initialized")
            except Exception as e:
                logger.warning("Failed to initialize OpenAI provider", error=str(e))
                
        # Anthropic provider
        if settings.anthropic_api_key:
            try:
                self.providers["anthropic"] = AnthropicProvider(
                    api_key=settings.anthropic_api_key,
                    model=settings.llm_model if settings.llm_model.startswith("claude") else "claude-3-sonnet-20240229"
                )
                logger.info("Anthropic provider initialized")
            except Exception as e:
                logger.warning("Failed to initialize Anthropic provider", error=str(e))
                
        if not self.providers:
            logger.warning("No LLM providers configured. Please set API keys in configuration.")
            
    def get_provider(self, provider_name: Optional[str] = None) -> LLMProvider:
        """Get an LLM provider by name."""
        if provider_name is None:
            provider_name = settings.default_llm_provider
            
        if provider_name not in self.providers:
            available = list(self.providers.keys())
            raise ConfigurationError(
                f"LLM provider '{provider_name}' not found. Available providers: {available}"
            )
            
        return self.providers[provider_name]
        
    def add_provider(self, name: str, provider: LLMProvider):
        """Add a custom LLM provider."""
        self.providers[name] = provider
        logger.info("Added custom LLM provider", name=name)
        
    async def complete(
        self, 
        messages: List[Dict[str, str]], 
        provider_name: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a completion using the specified provider."""
        provider = self.get_provider(provider_name)
        return await provider.complete(messages, **kwargs)
        
    async def stream_complete(
        self, 
        messages: List[Dict[str, str]], 
        provider_name: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming completion using the specified provider."""
        provider = self.get_provider(provider_name)
        async for chunk in provider.stream_complete(messages, **kwargs):
            yield chunk
            
    def list_providers(self) -> List[str]:
        """List available providers."""
        return list(self.providers.keys())
        
    def is_provider_available(self, provider_name: str) -> bool:
        """Check if a provider is available."""
        return provider_name in self.providers


# Global LLM manager instance
llm_manager = LLMManager()
