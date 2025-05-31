"""
Configuration settings for OpenReplica
"""
import os
from functools import lru_cache
from typing import Optional, List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Application settings
    app_name: str = "OpenReplica"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Security settings
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Database settings
    database_url: str = "sqlite:///./openreplica.db"
    redis_url: str = "redis://localhost:6379"
    
    # LLM settings
    default_llm_provider: str = "openai"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    
    # Runtime settings
    docker_enabled: bool = True
    max_concurrent_sessions: int = 10
    session_timeout_minutes: int = 60
    
    # Agent settings
    default_agent: str = "codeact"
    max_iterations: int = 100
    max_budget_per_task: float = 4.0
    
    # File system settings
    workspace_base: str = "/tmp/openreplica/workspaces"
    max_file_size_mb: int = 10
    allowed_file_extensions: List[str] = [
        ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss",
        ".json", ".yaml", ".yml", ".md", ".txt", ".sh", ".dockerfile",
        ".sql", ".env", ".toml", ".ini", ".cfg", ".xml", ".csv"
    ]
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # WebSocket settings
    ws_heartbeat_interval: int = 30
    ws_max_connections: int = 1000
    
    # Security settings
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    trusted_hosts: List[str] = ["localhost", "127.0.0.1"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


def get_llm_config(provider: str) -> dict:
    """Get LLM configuration for a specific provider"""
    settings = get_settings()
    
    configs = {
        "openai": {
            "api_key": settings.openai_api_key,
            "model": "gpt-4",
            "base_url": "https://api.openai.com/v1",
        },
        "anthropic": {
            "api_key": settings.anthropic_api_key,
            "model": "claude-3-sonnet-20240229",
        },
        "google": {
            "api_key": settings.google_api_key,
            "model": "gemini-pro",
        }
    }
    
    return configs.get(provider, configs["openai"])


def validate_environment():
    """Validate required environment variables"""
    settings = get_settings()
    
    if not settings.openai_api_key and not settings.anthropic_api_key:
        raise ValueError(
            "At least one LLM API key must be provided "
            "(OPENAI_API_KEY or ANTHROPIC_API_KEY)"
        )
    
    # Create workspace directory if it doesn't exist
    os.makedirs(settings.workspace_base, exist_ok=True)
    
    return True
