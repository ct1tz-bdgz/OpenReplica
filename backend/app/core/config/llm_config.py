"""
LLM Configuration for OpenReplica matching OpenHands exactly with improvements
"""
from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field, SecretStr, ValidationError

from app.core.logging import LOG_DIR, get_logger

logger = get_logger(__name__)


class LLMConfig(BaseModel):
    """Configuration for the LLM model.

    Attributes:
        model: The model to use.
        api_key: The API key to use.
        base_url: The base URL for the API. This is necessary for local LLMs.
        api_version: The version of the API.
        aws_access_key_id: The AWS access key ID.
        aws_secret_access_key: The AWS secret access key.
        aws_region_name: The AWS region name.
        num_retries: The number of retries to attempt.
        retry_multiplier: The multiplier for the exponential backoff.
        retry_min_wait: The minimum time to wait between retries, in seconds. This is exponential backoff minimum. For models with very low limits, this can be set to 15-20.
        retry_max_wait: The maximum time to wait between retries, in seconds. This is exponential backoff maximum.
        timeout: The timeout for the API.
        max_message_chars: The approximate max number of characters in the content of an event included in the prompt to the LLM. Larger observations are truncated.
        temperature: The temperature for the API.
        top_p: The top p for the API.
        top_k: The top k for the API.
        custom_llm_provider: The custom LLM provider to use. This is undocumented in openhands, and normally not used. It is documented on the litellm side.
        max_input_tokens: The maximum number of input tokens. Note that this is currently unused, and the value at runtime is actually the total tokens in OpenAI (e.g. 128,000 tokens for GPT-4).
        max_output_tokens: The maximum number of output tokens. This is sent to the LLM.
        input_cost_per_token: The cost per input token. This will available in logs for the user to check.
        output_cost_per_token: The cost per output token. This will available in logs for the user to check.
        ollama_base_url: The base URL for the OLLAMA API.
        drop_params: Drop any unmapped (unsupported) params without causing an exception.
        modify_params: Modify params allows litellm to do transformations like adding a default message, when a message is empty.
        disable_vision: If model is vision capable, this option allows to disable image processing (useful for cost reduction).
        caching_prompt: Use the prompt caching feature if provided by the LLM and supported by the provider.
        log_completions: Whether to log LLM completions to the state.
        log_completions_folder: The folder to log LLM completions to. Required if log_completions is True.
        custom_tokenizer: A custom tokenizer to use for token counting.
        native_tool_calling: Whether to use native tool calling if supported by the model. Can be True, False, or not set.
        reasoning_effort: The effort to put into reasoning. This is a string that can be one of 'low', 'medium', 'high', or 'none'. Exclusive for o1 models.
        seed: The seed to use for the LLM.
        openrouter_site_url: Site URL for OpenRouter attribution.
        openrouter_app_name: App name for OpenRouter attribution.
    """

    model: str = Field(default='claude-3-5-sonnet-20241022')
    api_key: SecretStr | None = Field(default=None)
    base_url: str | None = Field(default=None)
    api_version: str | None = Field(default=None)
    aws_access_key_id: SecretStr | None = Field(default=None)
    aws_secret_access_key: SecretStr | None = Field(default=None)
    aws_region_name: str | None = Field(default=None)
    openrouter_site_url: str = Field(default='https://github.com/ct1tz-bdgz/OpenReplica')
    openrouter_app_name: str = Field(default='OpenReplica')
    # total wait time: 5 + 10 + 20 + 30 = 65 seconds
    num_retries: int = Field(default=4)
    retry_multiplier: float = Field(default=2)
    retry_min_wait: int = Field(default=5)
    retry_max_wait: int = Field(default=30)
    timeout: int | None = Field(default=None)
    max_message_chars: int = Field(
        default=30_000
    )  # maximum number of characters in an observation's content when sent to the llm
    temperature: float = Field(default=0.0)
    top_p: float = Field(default=1.0)
    top_k: float | None = Field(default=None)
    custom_llm_provider: str | None = Field(default=None)
    max_input_tokens: int | None = Field(default=None)
    max_output_tokens: int | None = Field(default=None)
    input_cost_per_token: float | None = Field(default=None)
    output_cost_per_token: float | None = Field(default=None)
    ollama_base_url: str | None = Field(default=None)
    # This setting can be sent in each call to litellm
    drop_params: bool = Field(default=True)
    # Note: this setting is actually global, unlike drop_params
    modify_params: bool = Field(default=True)
    disable_vision: bool | None = Field(default=None)
    caching_prompt: bool = Field(default=True)
    log_completions: bool = Field(default=False)
    log_completions_folder: str = Field(default=os.path.join(LOG_DIR, 'completions'))
    custom_tokenizer: str | None = Field(default=None)
    native_tool_calling: bool | None = Field(default=None)
    reasoning_effort: str | None = Field(default='high')
    seed: int | None = Field(default=None)

    model_config = {'extra': 'forbid'}

    @classmethod
    def from_toml_section(cls, data: dict) -> dict[str, 'LLMConfig']:
        """
        Create a mapping of LLMConfig instances from a toml dictionary representing the [llm] section.

        The default configuration is built from all non-dict keys in data.
        Then, each key with a dict value (e.g. [llm.random_name]) is treated as a custom LLM configuration,
        and its values override the default configuration.

        Args:
            data: The dictionary representing the [llm] section of the toml config file.

        Returns:
            A mapping of LLMConfig instances, where the key 'default' corresponds to the default configuration.
        """
        llm_configs = {}

        # Build the default configuration from all non-dict keys
        default_config_data = {k: v for k, v in data.items() if not isinstance(v, dict)}
        
        try:
            default_config = cls.model_validate(default_config_data)
            llm_configs['default'] = default_config
        except ValidationError as e:
            logger.error(f'Error creating default LLM config: {e}')
            llm_configs['default'] = cls()  # Use default constructor

        # Build custom configurations
        for name, custom_data in data.items():
            if isinstance(custom_data, dict):
                # Merge with default configuration
                merged_data = {**default_config_data, **custom_data}
                try:
                    custom_config = cls.model_validate(merged_data)
                    llm_configs[name] = custom_config
                except ValidationError as e:
                    logger.error(f'Error creating custom LLM config {name}: {e}')
                    # Fall back to default config
                    llm_configs[name] = llm_configs['default']

        return llm_configs

    def get_provider_type(self) -> str:
        """
        Determine the provider type based on the model name and configuration.
        
        Returns:
            The provider type string (e.g., 'openai', 'anthropic', 'openrouter', etc.)
        """
        model_lower = self.model.lower()
        
        # OpenRouter detection
        if 'openrouter' in model_lower or (self.base_url and 'openrouter.ai' in self.base_url):
            return 'openrouter'
        
        # Provider detection by model prefix
        if model_lower.startswith(('gpt-', 'o1-', 'o3-', 'davinci-', 'ada-', 'babbage-', 'curie-')):
            return 'openai'
        elif model_lower.startswith('claude-'):
            return 'anthropic'
        elif model_lower.startswith(('gemini-', 'palm-', 'bison-')):
            return 'google'
        elif model_lower.startswith('command-'):
            return 'cohere'
        elif model_lower.startswith('azure/'):
            return 'azure'
        elif model_lower.startswith('bedrock/'):
            return 'bedrock'
        elif model_lower.startswith('vertex_ai/'):
            return 'vertex'
        elif 'llama' in model_lower or 'mistral' in model_lower or 'codellama' in model_lower:
            if self.ollama_base_url or (self.base_url and 'ollama' in self.base_url):
                return 'ollama'
            else:
                return 'huggingface'
        
        # Base URL detection
        if self.base_url:
            base_url_lower = self.base_url.lower()
            if 'openai' in base_url_lower:
                return 'openai'
            elif 'anthropic' in base_url_lower:
                return 'anthropic'
            elif 'openrouter.ai' in base_url_lower:
                return 'openrouter'
            elif 'ollama' in base_url_lower:
                return 'ollama'
            elif 'cohere' in base_url_lower:
                return 'cohere'
            elif 'together' in base_url_lower:
                return 'together'
            elif 'replicate' in base_url_lower:
                return 'replicate'
            else:
                return 'custom'
        
        # Default to custom if we can't determine
        return 'custom'

    def get_available_models(self) -> list[str]:
        """
        Get available models for the provider type.
        
        Returns:
            List of available model names for this provider.
        """
        provider = self.get_provider_type()
        
        # This would be populated from actual provider APIs in a real implementation
        provider_models = {
            'openai': [
                'gpt-4o',
                'gpt-4o-mini', 
                'gpt-4-turbo',
                'gpt-4',
                'gpt-3.5-turbo',
                'o1-preview',
                'o1-mini',
                'o1-2024-12-17',
                'o3-mini-2025-01-31',
                'o3-mini',
                'o3-2025-04-16',
                'o4-mini-2025-04-16'
            ],
            'anthropic': [
                'claude-3-5-sonnet-20241022',
                'claude-3-5-sonnet-20240620', 
                'claude-3-5-haiku-20241022',
                'claude-3-opus-20240229',
                'claude-3-sonnet-20240229',
                'claude-3-haiku-20240307',
                'claude-2.1',
                'claude-2.0',
                'claude-instant-1.2'
            ],
            'google': [
                'gemini-pro',
                'gemini-pro-vision',
                'gemini-1.5-pro',
                'gemini-1.5-flash',
                'palm-2-chat-bison',
                'palm-2-codechat-bison'
            ],
            'cohere': [
                'command-r-plus',
                'command-r',
                'command-nightly',
                'command-light-nightly'
            ],
            'openrouter': [
                # OpenRouter has hundreds of models, this is a subset
                'openai/gpt-4o',
                'openai/gpt-4o-mini',
                'anthropic/claude-3-5-sonnet',
                'anthropic/claude-3-haiku',
                'google/gemini-pro',
                'meta-llama/llama-3.1-405b-instruct',
                'meta-llama/llama-3.1-70b-instruct',
                'mistralai/mistral-large',
                'qwen/qwen-2.5-72b-instruct',
                'deepseek/deepseek-chat'
            ],
            'ollama': [
                'llama3.2',
                'llama3.1',
                'codellama',
                'mistral',
                'mixtral',
                'qwen2.5',
                'deepseek-coder',
                'phi3'
            ]
        }
        
        return provider_models.get(provider, [self.model])

    def supports_function_calling(self) -> bool:
        """Check if the model supports function calling."""
        provider = self.get_provider_type()
        model_lower = self.model.lower()
        
        # Known function calling models
        function_calling_models = [
            'gpt-4', 'gpt-3.5-turbo', 'claude-3', 'gemini-pro', 'command-r'
        ]
        
        return any(model in model_lower for model in function_calling_models)

    def supports_vision(self) -> bool:
        """Check if the model supports vision capabilities."""
        model_lower = self.model.lower()
        
        vision_keywords = [
            'vision', 'gpt-4o', 'claude-3', 'gemini-pro-vision', 'gemini-1.5'
        ]
        
        return any(keyword in model_lower for keyword in vision_keywords)

    def get_cost_info(self) -> dict[str, float]:
        """Get cost information for the model."""
        return {
            'input_cost_per_token': self.input_cost_per_token or 0.0,
            'output_cost_per_token': self.output_cost_per_token or 0.0
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, handling SecretStr fields."""
        data = self.model_dump()
        
        # Convert SecretStr to string for serialization
        if self.api_key:
            data['api_key'] = self.api_key.get_secret_value()
        if self.aws_access_key_id:
            data['aws_access_key_id'] = self.aws_access_key_id.get_secret_value()
        if self.aws_secret_access_key:
            data['aws_secret_access_key'] = self.aws_secret_access_key.get_secret_value()
            
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'LLMConfig':
        """Create from dictionary, handling SecretStr fields."""
        # Convert string secrets to SecretStr
        if 'api_key' in data and data['api_key']:
            data['api_key'] = SecretStr(data['api_key'])
        if 'aws_access_key_id' in data and data['aws_access_key_id']:
            data['aws_access_key_id'] = SecretStr(data['aws_access_key_id'])
        if 'aws_secret_access_key' in data and data['aws_secret_access_key']:
            data['aws_secret_access_key'] = SecretStr(data['aws_secret_access_key'])
            
        return cls.model_validate(data)

    def __str__(self) -> str:
        """String representation without exposing secrets."""
        return f"LLMConfig(model={self.model}, provider={self.get_provider_type()})"

    def __repr__(self) -> str:
        """Detailed representation without exposing secrets."""
        return (
            f"LLMConfig(model={self.model}, provider={self.get_provider_type()}, "
            f"temperature={self.temperature}, max_output_tokens={self.max_output_tokens})"
        )


# Predefined configurations for popular models
POPULAR_MODELS = {
    'gpt-4o': LLMConfig(
        model='gpt-4o',
        temperature=0.1,
        max_output_tokens=4096
    ),
    'claude-3-5-sonnet': LLMConfig(
        model='claude-3-5-sonnet-20241022',
        temperature=0.1,
        max_output_tokens=4096
    ),
    'gemini-pro': LLMConfig(
        model='gemini-pro',
        temperature=0.1,
        max_output_tokens=4096
    ),
    'o1-preview': LLMConfig(
        model='o1-preview',
        temperature=1.0,  # o1 models don't support temperature control
        reasoning_effort='high',
        max_output_tokens=32768
    )
}


def get_default_llm_config() -> LLMConfig:
    """Get the default LLM configuration."""
    return LLMConfig()


def create_llm_config_from_env() -> LLMConfig:
    """Create LLM config from environment variables."""
    config_data = {}
    
    # Map environment variables to config fields
    env_mappings = {
        'OPENAI_API_KEY': 'api_key',
        'ANTHROPIC_API_KEY': 'api_key',
        'GOOGLE_API_KEY': 'api_key',
        'COHERE_API_KEY': 'api_key',
        'OPENROUTER_API_KEY': 'api_key',
        'LLM_MODEL': 'model',
        'LLM_BASE_URL': 'base_url',
        'LLM_API_VERSION': 'api_version',
        'LLM_TEMPERATURE': 'temperature',
        'LLM_MAX_TOKENS': 'max_output_tokens',
        'AWS_ACCESS_KEY_ID': 'aws_access_key_id',
        'AWS_SECRET_ACCESS_KEY': 'aws_secret_access_key',
        'AWS_REGION': 'aws_region_name',
        'OLLAMA_BASE_URL': 'ollama_base_url'
    }
    
    for env_var, config_field in env_mappings.items():
        value = os.getenv(env_var)
        if value:
            # Convert types as needed
            if config_field in ['temperature']:
                config_data[config_field] = float(value)
            elif config_field in ['max_output_tokens']:
                config_data[config_field] = int(value)
            elif config_field in ['api_key', 'aws_access_key_id', 'aws_secret_access_key']:
                config_data[config_field] = SecretStr(value)
            else:
                config_data[config_field] = value
    
    return LLMConfig.model_validate(config_data) if config_data else LLMConfig()
