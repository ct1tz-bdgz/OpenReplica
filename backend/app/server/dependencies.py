"""
Dependencies for OpenReplica server matching OpenHands exactly
"""
from typing import Any, List
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.logging import get_logger
from app.server.shared import config

logger = get_logger(__name__)

security = HTTPBearer(auto_error=False)


async def verify_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str | None:
    """Verify API key if authentication is enabled"""
    # For now, we'll implement basic API key verification
    # This can be extended for more sophisticated auth
    if not config.security.require_auth:
        return None
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify the token against configured API keys
    if config.security.api_keys and credentials.credentials not in config.security.api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return credentials.credentials


async def get_conversation_from_request(request: Request) -> Any:
    """Get conversation from request state"""
    if not hasattr(request.state, 'conversation'):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return request.state.conversation


def get_dependencies() -> List[Any]:
    """Get list of dependencies for routes"""
    dependencies = []
    
    # Add auth dependency if required
    if config.security.require_auth:
        dependencies.append(Depends(verify_api_key))
    
    return dependencies


async def validate_conversation_access(
    request: Request,
    conversation_id: str,
    user_id: str | None = None
) -> bool:
    """Validate user has access to conversation"""
    # For now, return True - can be extended for user-specific access control
    return True


async def rate_limit_check(request: Request) -> None:
    """Check rate limits for requests"""
    # Placeholder for rate limiting implementation
    # Can be extended with Redis-based rate limiting
    pass


async def log_request(request: Request) -> None:
    """Log incoming requests"""
    logger.info(
        f"Request: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": request.client.host if request.client else None
        }
    )


# Middleware dependencies
async def add_request_logging(request: Request, call_next):
    """Middleware to log requests"""
    await log_request(request)
    response = await call_next(request)
    return response


async def add_cors_headers(request: Request, call_next):
    """Middleware to add CORS headers"""
    response = await call_next(request)
    
    # Add CORS headers
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Session-API-Key"
    response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
    
    return response
