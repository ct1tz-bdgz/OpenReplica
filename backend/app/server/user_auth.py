"""
User authentication for OpenReplica matching OpenHands exactly
"""
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.logging import get_logger
from app.server.shared import config

logger = get_logger(__name__)

security = HTTPBearer(auto_error=False)


async def get_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Get user ID from request"""
    # For development, return a default user ID
    # In production, this would validate the JWT token and extract user ID
    
    # Check if authentication is required
    if not getattr(config, 'require_auth', False):
        return "default_user"
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate token and extract user ID
    try:
        user_id = validate_token(credentials.credentials)
        return user_id
    except Exception as e:
        logger.error(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def validate_token(token: str) -> str:
    """Validate JWT token and return user ID"""
    # For development, accept any token and return default user
    # In production, this would use JWT validation
    
    if token == "development_token":
        return "default_user"
    
    # Mock JWT validation - in real implementation use PyJWT
    try:
        # Decode JWT token
        # payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        # return payload.get("user_id")
        
        # For now, return extracted user from token
        return "user_" + token[:8]  # Simple mock
        
    except Exception:
        raise ValueError("Invalid token format")


async def get_provider_tokens(
    user_id: str = Depends(get_user_id)
) -> Optional[dict]:
    """Get provider tokens for user"""
    # This would fetch provider tokens from storage
    # For now, return None
    return None


async def get_secrets_store(
    user_id: str = Depends(get_user_id)
):
    """Get secrets store for user"""
    from app.storage.secrets.secrets_store import MockSecretsStore
    return MockSecretsStore(user_id)


async def get_user_settings_store(
    user_id: str = Depends(get_user_id)
):
    """Get user settings store"""
    from app.storage.settings.settings_store import MockSettingsStore
    return MockSettingsStore(user_id)


class AuthManager:
    """Authentication and authorization manager"""
    
    def __init__(self):
        self.secret_key = getattr(config, 'secret_key', 'development_secret')
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
    
    def create_access_token(self, user_id: str, expires_delta: Optional[int] = None) -> str:
        """Create JWT access token"""
        import jwt
        from datetime import datetime, timedelta
        
        if expires_delta:
            expire = datetime.utcnow() + timedelta(minutes=expires_delta)
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode = {
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> dict:
        """Verify JWT token"""
        import jwt
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )


# Global auth manager
auth_manager = AuthManager()
