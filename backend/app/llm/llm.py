"""
LLM implementation for OpenReplica matching OpenHands exactly
"""
import copy
import os
import time
import warnings
from functools import partial
from typing import Any, Callable

import httpx

from app.core.config import LLMConfig

with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    import litellm

from litellm import ChatCompletionMessageToolCall, ModelInfo, PromptTokensDetails
from litellm import Message as LiteLLMMessage
from litellm import completion as litellm_completion
from litellm import completion_cost as litellm_completion_cost
from litellm.exceptions import (
    RateLimitError,
)
from litellm.types.utils import CostPerToken, ModelResponse, Usage
from litellm.utils import create_pretrained_tokenizer

from app.core.exceptions import LLMNoResponseError
from app.core.logging import get_logger
from app.core.message import Message
from app.llm.debug_mixin import DebugMixin
from app.llm.fn_call_converter import (
    STOP_WORDS,
    convert_fncall_messages_to_non_fncall_messages,
    convert_non_fncall_messages_to_fncall_messages,
)
from app.llm.metrics import Metrics
from app.llm.retry_mixin import RetryMixin

logger = get_logger(__name__)

__all__ = ['LLM']

# tuple of exceptions to retry on
LLM_RETRY_EXCEPTIONS: tuple[type[Exception], ...] = (
    RateLimitError,
    litellm.Timeout,
    litellm.InternalServerError,
    LLMNoResponseError,
)

# cache prompt supporting models
# remove this when we gemini and deepseek are supported
CACHE_PROMPT_SUPPORTED_MODELS = [
    'claude-3-7-sonnet-20250219',
    'claude-sonnet-3-7-latest',
    'claude-3.7-sonnet',
    'claude-3-5-sonnet-20241022',
    'claude-3-5-sonnet-20240620',
    'claude-3-5-haiku-20241022',
    'claude-3-haiku-20240307',
    'claude-3-opus-20240229',
    'claude-sonnet-4-20250514',
    'claude-opus-4-20250514',
]

# function calling supporting models
FUNCTION_CALLING_SUPPORTED_MODELS = [
    'claude-3-7-sonnet-20250219',
    'claude-sonnet-3-7-latest',
    'claude-3-5-sonnet',
    'claude-3-5-sonnet-20240620',
    'claude-3-5-sonnet-20241022',
    'claude-3.5-haiku',
    'claude-3-5-haiku-20241022',
    'claude-sonnet-4-20250514',
    'claude-opus-4-20250514',
    'gpt-4o-mini',
    'gpt-4o',
    'o1-2024-12-17',
    'o3-mini-2025-01-31',
    'o3-mini',
    'o3',
    'o3-2025-04-16',
    'o4-mini',
    'o4-mini-2025-04-16',
    'gemini-2.5-pro',
    'gpt-4.1',
]

REASONING_EFFORT_SUPPORTED_MODELS = [
    'o1-2024-12-17',
    'o1',
    'o3',
    'o3-2025-04-16',
    'o3-mini-2025-01-31',
    'o3-mini',
    'o4-mini',
    'o4-mini-2025-04-16',
]

MODELS_WITHOUT_STOP_WORDS = [
    'o1-mini',
    'o1-preview',
    'o1-2024-12-17',
    'o1',
    'o3',
    'o3-2025-04-16',
    'o3-mini-2025-01-31',
    'o3-mini',
    'o4-mini',
    'o4-mini-2025-04-16',
]


class LLM(RetryMixin, DebugMixin):
    """
    LLM class for OpenReplica that interfaces with litellm.
    """

    def __init__(
        self,
        config: LLMConfig,
        metrics: Metrics | None = None,
    ):
        """
        Initializes the LLM class.
        """
        self.config = config
        self.metrics = metrics if metrics is not None else Metrics()

        # llm config should specify the model
        if self.config.model is None or self.config.model == '':
            raise ValueError('Model is required')
        self.model_name = self.config.model

        # Set litellm settings
        litellm.set_verbose = False
        litellm.drop_params = True
        litellm.modify_params = True

        # Set API key and base URL if provided
        if self.config.api_key:
            os.environ['OPENAI_API_KEY'] = self.config.api_key
        if self.config.base_url:
            os.environ['OPENAI_API_BASE'] = self.config.base_url

        # Initialize tokenizer
        self._tokenizer = None
        self._initialize_tokenizer()

    def _initialize_tokenizer(self):
        """Initialize tokenizer for token counting"""
        try:
            self._tokenizer = create_pretrained_tokenizer(self.model_name)
        except Exception as e:
            logger.warning(f"Failed to initialize tokenizer for {self.model_name}: {e}")
            self._tokenizer = None

    def completion(
        self,
        messages: list[Message],
        convert_system_messages: bool = True,
        **kwargs
    ) -> ModelResponse:
        """
        Creates a completion using the LLM.
        """
        # Convert messages to litellm format
        litellm_messages = []
        for message in messages:
            if isinstance(message, dict):
                litellm_messages.append(message)
            else:
                litellm_messages.append(message.to_dict())

        # Handle system messages for models that don't support them
        if convert_system_messages:
            litellm_messages = self._convert_system_messages(litellm_messages)

        # Add model-specific parameters
        completion_kwargs = self._prepare_completion_kwargs(kwargs)

        # Add stop words for supported models
        if self.model_name not in MODELS_WITHOUT_STOP_WORDS:
            completion_kwargs.setdefault('stop', STOP_WORDS)

        # Handle function calling
        if 'tools' in completion_kwargs:
            if self.model_name not in FUNCTION_CALLING_SUPPORTED_MODELS:
                logger.warning(f"Model {self.model_name} does not support function calling")
                # Convert to non-function calling format
                litellm_messages = convert_fncall_messages_to_non_fncall_messages(
                    litellm_messages, completion_kwargs.get('tools', [])
                )
                completion_kwargs.pop('tools', None)
                completion_kwargs.pop('tool_choice', None)

        # Add caching for supported models
        if self.model_name in CACHE_PROMPT_SUPPORTED_MODELS:
            completion_kwargs['extra_headers'] = {
                'anthropic-beta': 'prompt-caching-2024-07-31'
            }

        # Add reasoning effort for supported models
        if (self.model_name in REASONING_EFFORT_SUPPORTED_MODELS and 
            'reasoning_effort' not in completion_kwargs):
            completion_kwargs['reasoning_effort'] = 'medium'

        try:
            response = litellm_completion(
                model=self.model_name,
                messages=litellm_messages,
                **completion_kwargs
            )
            
            # Record metrics
            if response.usage:
                self.metrics.add_completion(
                    model=self.model_name,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    cost=litellm_completion_cost(response)
                )

            return response

        except Exception as e:
            logger.error(f"LLM completion failed: {e}")
            raise

    def _convert_system_messages(self, messages: list[dict]) -> list[dict]:
        """Convert system messages for models that don't support them"""
        converted = []
        system_content = []
        
        for message in messages:
            if message.get('role') == 'system':
                system_content.append(message['content'])
            else:
                if system_content and not converted:
                    # Add system content to first user message
                    if message.get('role') == 'user':
                        combined_content = '\n\n'.join(system_content + [message['content']])
                        converted.append({
                            'role': 'user',
                            'content': combined_content
                        })
                        system_content = []
                    else:
                        # Add as user message if no user message yet
                        converted.append({
                            'role': 'user',
                            'content': '\n\n'.join(system_content)
                        })
                        converted.append(message)
                        system_content = []
                else:
                    converted.append(message)
        
        return converted

    def _prepare_completion_kwargs(self, kwargs: dict) -> dict:
        """Prepare completion kwargs with model-specific settings"""
        completion_kwargs = {
            'temperature': self.config.temperature,
            'max_tokens': self.config.max_output_tokens,
            'timeout': self.config.timeout,
        }
        
        # Add custom parameters
        if self.config.custom_llm_provider:
            completion_kwargs['custom_llm_provider'] = self.config.custom_llm_provider
        
        if self.config.max_input_tokens:
            completion_kwargs['max_input_tokens'] = self.config.max_input_tokens

        # Override with provided kwargs
        completion_kwargs.update(kwargs)
        
        return completion_kwargs

    def count_tokens(self, messages: list[Message]) -> int:
        """Count tokens in messages"""
        if self._tokenizer is None:
            # Fallback estimation
            total_chars = sum(len(str(msg)) for msg in messages)
            return total_chars // 4  # Rough estimation
        
        try:
            total_tokens = 0
            for message in messages:
                if isinstance(message, dict):
                    content = message.get('content', '')
                else:
                    content = str(message)
                total_tokens += len(self._tokenizer.encode(content))
            return total_tokens
        except Exception:
            # Fallback estimation
            total_chars = sum(len(str(msg)) for msg in messages)
            return total_chars // 4

    def get_model_info(self) -> ModelInfo | None:
        """Get model information"""
        try:
            return litellm.get_model_info(self.model_name)
        except Exception as e:
            logger.warning(f"Failed to get model info for {self.model_name}: {e}")
            return None

    @property
    def supports_function_calling(self) -> bool:
        """Check if model supports function calling"""
        return self.model_name in FUNCTION_CALLING_SUPPORTED_MODELS

    @property
    def supports_vision(self) -> bool:
        """Check if model supports vision"""
        model_info = self.get_model_info()
        if model_info:
            return model_info.get('supports_vision', False)
        
        # Fallback check for known vision models
        vision_models = [
            'gpt-4-vision',
            'gpt-4o',
            'claude-3',
            'gemini-pro-vision'
        ]
        return any(vm in self.model_name for vm in vision_models)

    def reset(self):
        """Reset the LLM state"""
        pass

    def __repr__(self):
        return f"LLM(model={self.model_name})"
