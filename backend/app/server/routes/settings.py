"""
Settings routes for OpenReplica matching OpenHands exactly
"""
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.integrations.provider import (
    PROVIDER_TOKEN_TYPE,
    ProviderType,
)
from app.server.dependencies import get_dependencies
from app.server.routes.secrets import invalidate_legacy_secrets_store
from app.server.settings import GETSettingsModel
from app.server.shared import config
from app.server.user_auth import (
    get_provider_tokens,
    get_secrets_store,
    get_user_settings_store,
)
from app.storage.data_models.settings import Settings
from app.storage.secrets.secrets_store import SecretsStore
from app.storage.settings.settings_store import SettingsStore

logger = get_logger(__name__)

app = APIRouter(prefix='/api', dependencies=get_dependencies())


@app.get(
    '/settings',
    response_model=GETSettingsModel,
    responses={
        404: {'description': 'Settings not found', 'model': dict},
        401: {'description': 'Invalid token', 'model': dict},
    },
)
async def load_settings(
    provider_tokens: PROVIDER_TOKEN_TYPE | None = Depends(get_provider_tokens),
    settings_store: SettingsStore = Depends(get_user_settings_store),
    secrets_store: SecretsStore = Depends(get_secrets_store),
) -> GETSettingsModel | JSONResponse:
    """Load user settings including LLM configuration"""
    settings = await settings_store.load()

    try:
        if not settings:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={'error': 'Settings not found'},
            )

        # On initial load, user secrets may not be populated with values migrated from settings store
        user_secrets = await invalidate_legacy_secrets_store(
            settings, settings_store, secrets_store
        )

        # If invalidation is successful, then the returned user secrets holds the most recent values
        git_providers = (
            user_secrets.provider_tokens if user_secrets else provider_tokens
        )

        provider_tokens_set: dict[ProviderType, str | None] = {}
        if git_providers:
            for provider_type, provider_token in git_providers.items():
                if provider_token.token or provider_token.user_id:
                    provider_tokens_set[provider_type] = provider_token.host

        settings_with_token_data = GETSettingsModel(
            **settings.model_dump(exclude='secrets_store'),
            llm_api_key_set=settings.llm_api_key is not None
            and bool(settings.llm_api_key),
            search_api_key_set=settings.search_api_key is not None
            and bool(settings.search_api_key),
            provider_tokens_set=provider_tokens_set,
        )
        settings_with_token_data.llm_api_key = None
        settings_with_token_data.search_api_key = None
        return settings_with_token_data
    except Exception as e:
        logger.warning(f'Invalid token: {e}')
        # Get user_id from settings if available
        user_id = getattr(settings, 'user_id', 'unknown') if settings else 'unknown'
        logger.info(
            f'Returning 401 Unauthorized - Invalid token for user_id: {user_id}'
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={'error': 'Invalid token'},
        )


@app.post(
    '/reset-settings',
    responses={
        410: {
            'description': 'Reset settings functionality has been removed',
            'model': dict,
        }
    },
)
async def reset_settings() -> JSONResponse:
    """
    Resets user settings. (Deprecated)
    """
    logger.warning('Deprecated endpoint /api/reset-settings called by user')
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={'error': 'Reset settings functionality has been removed.'},
    )


async def store_llm_settings(
    settings: Settings, settings_store: SettingsStore
) -> Settings:
    """Store LLM settings with merging existing settings"""
    existing_settings = await settings_store.load()

    # Convert to Settings model and merge with existing settings
    if existing_settings:
        # Keep existing LLM settings if not provided
        if settings.llm_api_key is None:
            settings.llm_api_key = existing_settings.llm_api_key
        if settings.llm_model is None:
            settings.llm_model = existing_settings.llm_model
        if settings.llm_base_url is None:
            settings.llm_base_url = existing_settings.llm_base_url
        if settings.llm_api_version is None:
            settings.llm_api_version = existing_settings.llm_api_version
        if settings.llm_custom_provider is None:
            settings.llm_custom_provider = existing_settings.llm_custom_provider
        if settings.openrouter_api_key is None:
            settings.openrouter_api_key = existing_settings.openrouter_api_key
        if settings.taviily_api_key is None:
            settings.taviily_api_key = existing_settings.taviily_api_key
        # Keep existing search API key if not provided
        if settings.search_api_key is None:
            settings.search_api_key = existing_settings.search_api_key

    return settings


# NOTE: We use response_model=None for endpoints that return JSONResponse directly.
# This is because FastAPI's response_model expects a Pydantic model, but we're returning
# a response object directly. We document the possible responses using the 'responses'
# parameter and maintain proper type annotations for mypy.
@app.post(
    '/settings',
    response_model=None,
    responses={
        200: {'description': 'Settings stored successfully', 'model': dict},
        500: {'description': 'Error storing settings', 'model': dict},
    },
)
async def store_settings(
    settings: Settings,
    settings_store: SettingsStore = Depends(get_user_settings_store),
) -> JSONResponse:
    """Store user settings including LLM configuration"""
    # Check provider tokens are valid
    try:
        existing_settings = await settings_store.load()

        # Convert to Settings model and merge with existing settings
        if existing_settings:
            settings = await store_llm_settings(settings, settings_store)

            # Keep existing analytics consent if not provided
            if settings.user_consents_to_analytics is None:
                settings.user_consents_to_analytics = (
                    existing_settings.user_consents_to_analytics
                )

        # Update sandbox config with new settings
        if settings.remote_runtime_resource_factor is not None:
            config.sandbox.remote_runtime_resource_factor = (
                settings.remote_runtime_resource_factor
            )

        settings = convert_to_settings(settings)
        await settings_store.store(settings)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'message': 'Settings stored'},
        )
    except Exception as e:
        logger.warning(f'Something went wrong storing settings: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': 'Something went wrong storing settings'},
        )


@app.get(
    '/models',
    response_model=dict,
    responses={
        200: {'description': 'Available models', 'model': dict},
        500: {'description': 'Error fetching models', 'model': dict},
    },
)
async def get_available_models() -> JSONResponse:
    """Get available LLM models from all providers"""
    try:
        from app.integrations.provider import PROVIDER_MODEL_REGISTRY, OpenRouterIntegration
        from app.core.config.llm_config import POPULAR_MODELS
        
        models = {}
        
        # Add models from provider registry
        for provider, info in PROVIDER_MODEL_REGISTRY.items():
            models[provider] = {
                'models': info.get('models', []),
                'base_url': info.get('base_url'),
                'supports_vision': info.get('supports_vision', False),
                'supports_function_calling': info.get('supports_function_calling', False)
            }
        
        # Add OpenRouter models dynamically
        try:
            openrouter = OpenRouterIntegration()
            if openrouter.is_configured():
                openrouter_models = await openrouter.get_available_models()
                models['openrouter']['models'] = [model.get('id', '') for model in openrouter_models]
        except Exception as e:
            logger.warning(f'Failed to fetch OpenRouter models: {e}')
        
        # Add popular models for quick selection
        models['popular'] = {
            'models': list(POPULAR_MODELS.keys()),
            'configs': {name: config.dict() for name, config in POPULAR_MODELS.items()}
        }
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=models
        )
        
    except Exception as e:
        logger.error(f'Error fetching available models: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Error fetching models: {e}'}
        )


@app.post(
    '/test-llm-connection',
    response_model=dict,
    responses={
        200: {'description': 'Connection test result', 'model': dict},
        500: {'description': 'Error testing connection', 'model': dict},
    },
)
async def test_llm_connection(
    llm_config: dict
) -> JSONResponse:
    """Test LLM connection with provided configuration"""
    try:
        from app.core.config.llm_config import LLMConfig
        from app.llm.manager import get_llm_manager
        
        # Create LLM config from request
        config = LLMConfig.from_dict(llm_config)
        
        # Register temporary LLM for testing
        manager = get_llm_manager()
        test_name = f"test_{int(time.time())}"
        manager.register_llm(test_name, config)
        
        # Test the connection
        result = await manager.test_llm_connection(test_name)
        
        # Clean up test LLM
        if test_name in manager.llms:
            del manager.llms[test_name]
            del manager.configs[test_name]
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=result
        )
        
    except Exception as e:
        logger.error(f'Error testing LLM connection: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                'success': False,
                'error': f'Connection test failed: {e}'
            }
        )


@app.get(
    '/providers',
    response_model=dict,
    responses={
        200: {'description': 'Available providers', 'model': dict},
    },
)
async def get_providers() -> JSONResponse:
    """Get list of all supported LLM providers"""
    try:
        from app.integrations.provider import get_all_providers, get_provider_info
        
        providers = {}
        for provider in get_all_providers():
            info = get_provider_info(provider)
            providers[provider] = {
                'name': provider.title(),
                'base_url': info.get('base_url'),
                'supports_vision': info.get('supports_vision', False),
                'supports_function_calling': info.get('supports_function_calling', False),
                'models_count': len(info.get('models', [])),
                'description': _get_provider_description(provider)
            }
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=providers
        )
        
    except Exception as e:
        logger.error(f'Error fetching providers: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Error fetching providers: {e}'}
        )


def convert_to_settings(settings_with_token_data: Settings) -> Settings:
    """Convert settings with token data to Settings model"""
    settings_data = settings_with_token_data.model_dump()

    # Filter out additional fields from `SettingsWithTokenData`
    filtered_settings_data = {
        key: value
        for key, value in settings_data.items()
        if key in Settings.model_fields  # Ensures only `Settings` fields are included
    }

    # Convert the API keys to `SecretStr` instances
    filtered_settings_data['llm_api_key'] = settings_with_token_data.llm_api_key
    filtered_settings_data['search_api_key'] = settings_with_token_data.search_api_key

    # Create a new Settings instance
    settings = Settings(**filtered_settings_data)
    return settings


def _get_provider_description(provider: str) -> str:
    """Get description for provider"""
    descriptions = {
        'openai': 'OpenAI models including GPT-4, GPT-3.5, and O1 series',
        'anthropic': 'Anthropic Claude models including Claude 3.5 Sonnet and Haiku',
        'google': 'Google Gemini and PaLM models',
        'cohere': 'Cohere Command models for text generation',
        'openrouter': 'Access to 100+ models from multiple providers',
        'ollama': 'Local models running on Ollama',
        'together': 'Together AI hosting for open source models',
        'replicate': 'Replicate cloud platform for ML models'
    }
    return descriptions.get(provider, f'{provider.title()} language models')
