"""
Secrets routes for OpenReplica matching OpenHands exactly
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, SecretStr
from typing import Dict, Optional, Any

from app.core.logging import get_logger
from app.server.dependencies import get_dependencies
from app.server.user_auth import get_user_id, get_secrets_store
from app.storage.secrets.secrets_store import SecretsStore
from app.integrations.provider import ProviderToken, CustomSecret

logger = get_logger(__name__)

app = APIRouter(prefix='/api/secrets', dependencies=get_dependencies())


class SetSecretRequest(BaseModel):
    """Request model for setting a secret"""
    key: str
    value: SecretStr


class SetProviderTokenRequest(BaseModel):
    """Request model for setting a provider token"""
    provider: str
    token: Optional[SecretStr] = None
    user_id: Optional[str] = None
    host: Optional[str] = None


class SetCustomSecretRequest(BaseModel):
    """Request model for setting a custom secret"""
    name: str
    secret: SecretStr
    description: Optional[str] = None


@app.post('/set')
async def set_secret(
    request: SetSecretRequest,
    secrets_store: SecretsStore = Depends(get_secrets_store)
) -> JSONResponse:
    """Set a secret"""
    try:
        await secrets_store.set_secret(
            key=request.key,
            value=request.value.get_secret_value()
        )
        
        return JSONResponse({
            "success": True,
            "message": f"Secret '{request.key}' set successfully"
        })
        
    except Exception as e:
        logger.error(f"Error setting secret: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to set secret: {e}"}
        )


@app.get('/list')
async def list_secrets(
    secrets_store: SecretsStore = Depends(get_secrets_store)
) -> JSONResponse:
    """List all secret keys (not values)"""
    try:
        keys = await secrets_store.list_secrets()
        
        return JSONResponse({
            "secrets": keys,
            "count": len(keys)
        })
        
    except Exception as e:
        logger.error(f"Error listing secrets: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to list secrets: {e}"}
        )


@app.delete('/{key}')
async def delete_secret(
    key: str,
    secrets_store: SecretsStore = Depends(get_secrets_store)
) -> JSONResponse:
    """Delete a secret"""
    try:
        await secrets_store.delete_secret(key)
        
        return JSONResponse({
            "success": True,
            "message": f"Secret '{key}' deleted successfully"
        })
        
    except Exception as e:
        logger.error(f"Error deleting secret: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to delete secret: {e}"}
        )


@app.post('/provider-tokens/set')
async def set_provider_token(
    request: SetProviderTokenRequest,
    secrets_store: SecretsStore = Depends(get_secrets_store)
) -> JSONResponse:
    """Set a provider token"""
    try:
        token = ProviderToken(
            token=request.token,
            user_id=request.user_id,
            host=request.host
        )
        
        await secrets_store.set_provider_token(request.provider, token)
        
        return JSONResponse({
            "success": True,
            "message": f"Provider token for '{request.provider}' set successfully"
        })
        
    except Exception as e:
        logger.error(f"Error setting provider token: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to set provider token: {e}"}
        )


@app.get('/provider-tokens')
async def get_provider_tokens(
    secrets_store: SecretsStore = Depends(get_secrets_store)
) -> JSONResponse:
    """Get all provider tokens (without secret values)"""
    try:
        tokens = await secrets_store.get_provider_tokens()
        
        # Return tokens without secret values
        token_info = {}
        for provider, token in tokens.items():
            token_info[provider] = {
                "has_token": token.token is not None,
                "user_id": token.user_id,
                "host": token.host
            }
        
        return JSONResponse({
            "provider_tokens": token_info
        })
        
    except Exception as e:
        logger.error(f"Error getting provider tokens: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to get provider tokens: {e}"}
        )


@app.post('/custom-secrets/set')
async def set_custom_secret(
    request: SetCustomSecretRequest,
    secrets_store: SecretsStore = Depends(get_secrets_store)
) -> JSONResponse:
    """Set a custom secret"""
    try:
        secret = CustomSecret(
            secret=request.secret,
            description=request.description
        )
        
        await secrets_store.set_custom_secret(request.name, secret)
        
        return JSONResponse({
            "success": True,
            "message": f"Custom secret '{request.name}' set successfully"
        })
        
    except Exception as e:
        logger.error(f"Error setting custom secret: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to set custom secret: {e}"}
        )


@app.get('/custom-secrets')
async def get_custom_secrets(
    secrets_store: SecretsStore = Depends(get_secrets_store)
) -> JSONResponse:
    """Get all custom secrets (without secret values)"""
    try:
        secrets = await secrets_store.get_custom_secrets()
        
        # Return secrets without secret values
        secret_info = {}
        for name, secret in secrets.items():
            secret_info[name] = {
                "description": secret.description,
                "has_secret": secret.secret is not None
            }
        
        return JSONResponse({
            "custom_secrets": secret_info
        })
        
    except Exception as e:
        logger.error(f"Error getting custom secrets: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to get custom secrets: {e}"}
        )


async def invalidate_legacy_secrets_store(
    settings: Any,
    settings_store: Any,
    secrets_store: SecretsStore
) -> Optional[Any]:
    """Invalidate legacy secrets store and migrate to new format"""
    try:
        # This function would handle migration from old secrets format
        # For now, just return None
        return None
        
    except Exception as e:
        logger.error(f"Error invalidating legacy secrets store: {e}")
        return None
