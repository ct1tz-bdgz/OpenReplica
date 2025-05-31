"""LLM provider implementations for OpenReplica."""

import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from openreplica.core.config import settings
from openreplica.core.exceptions import LLMError
from openreplica.core.logger import logger


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, api_key: str, model: str, **kwargs):
        self.api_key = api_key
        self.model = model
        self.config = kwargs
        
    @abstractmethod
    async def complete(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a completion for the given messages."""
        pass
        
    @abstractmethod
    async def stream_complete(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """Generate a streaming completion for the given messages."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation."""
    
    def __init__(self, api_key: str, model: str = "gpt-4", **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.client = AsyncOpenAI(api_key=api_key)
        
    async def complete(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a completion using OpenAI."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=float(kwargs.get("temperature", settings.temperature)),
                max_tokens=kwargs.get("max_tokens", settings.max_tokens),
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("OpenAI completion failed", error=str(e))
            raise LLMError(f"OpenAI completion failed: {str(e)}")
            
    async def stream_complete(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """Generate a streaming completion using OpenAI."""
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=float(kwargs.get("temperature", settings.temperature)),
                max_tokens=kwargs.get("max_tokens", settings.max_tokens),
                stream=True,
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens", "stream"]}
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error("OpenAI streaming failed", error=str(e))
            raise LLMError(f"OpenAI streaming failed: {str(e)}")


class AnthropicProvider(LLMProvider):
    """Anthropic provider implementation."""
    
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229", **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.client = AsyncAnthropic(api_key=api_key)
        
    async def complete(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a completion using Anthropic."""
        try:
            # Convert OpenAI format to Anthropic format
            system_message = None
            conversation_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    conversation_messages.append(msg)
            
            response = await self.client.messages.create(
                model=self.model,
                messages=conversation_messages,
                system=system_message,
                max_tokens=kwargs.get("max_tokens", settings.max_tokens),
                temperature=float(kwargs.get("temperature", settings.temperature)),
            )
            return response.content[0].text
        except Exception as e:
            logger.error("Anthropic completion failed", error=str(e))
            raise LLMError(f"Anthropic completion failed: {str(e)}")
            
    async def stream_complete(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """Generate a streaming completion using Anthropic."""
        try:
            # Convert OpenAI format to Anthropic format
            system_message = None
            conversation_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    conversation_messages.append(msg)
            
            async with self.client.messages.stream(
                model=self.model,
                messages=conversation_messages,
                system=system_message,
                max_tokens=kwargs.get("max_tokens", settings.max_tokens),
                temperature=float(kwargs.get("temperature", settings.temperature)),
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error("Anthropic streaming failed", error=str(e))
            raise LLMError(f"Anthropic streaming failed: {str(e)}")


class LiteLLMProvider(LLMProvider):
    """LiteLLM provider for unified access to multiple LLMs."""
    
    def __init__(self, api_key: str, model: str, **kwargs):
        super().__init__(api_key, model, **kwargs)
        try:
            import litellm
            self.litellm = litellm
        except ImportError:
            raise LLMError("LiteLLM not installed. Install with: pip install litellm")
            
    async def complete(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a completion using LiteLLM."""
        try:
            response = await self.litellm.acompletion(
                model=self.model,
                messages=messages,
                api_key=self.api_key,
                temperature=float(kwargs.get("temperature", settings.temperature)),
                max_tokens=kwargs.get("max_tokens", settings.max_tokens),
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("LiteLLM completion failed", error=str(e))
            raise LLMError(f"LiteLLM completion failed: {str(e)}")
            
    async def stream_complete(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """Generate a streaming completion using LiteLLM."""
        try:
            response = await self.litellm.acompletion(
                model=self.model,
                messages=messages,
                api_key=self.api_key,
                temperature=float(kwargs.get("temperature", settings.temperature)),
                max_tokens=kwargs.get("max_tokens", settings.max_tokens),
                stream=True,
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens", "stream"]}
            )
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error("LiteLLM streaming failed", error=str(e))
            raise LLMError(f"LiteLLM streaming failed: {str(e)}")
