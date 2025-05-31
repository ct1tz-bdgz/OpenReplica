"""Configuration management for OpenReplica."""

import os
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=3000, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    reload: bool = Field(default=False, description="Auto-reload on changes")
    
    # Security
    secret_key: str = Field(default="your-secret-key-change-in-production", description="Secret key for JWT")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration")
    
    # Database
    database_url: str = Field(default="sqlite:///./openreplica.db", description="Database URL")
    
    # Redis for session management
    redis_url: str = Field(default="redis://localhost:6379", description="Redis URL")
    
    # AI/LLM Configuration
    default_llm_provider: str = Field(default="openai", description="Default LLM provider")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    llm_model: str = Field(default="gpt-4", description="Default LLM model")
    max_tokens: int = Field(default=4000, description="Max tokens for LLM responses")
    temperature: float = Field(default=0.1, description="LLM temperature")
    
    # Docker Runtime
    docker_enabled: bool = Field(default=True, description="Enable Docker runtime")
    runtime_image: str = Field(default="python:3.11-slim", description="Default runtime image")
    sandbox_timeout: int = Field(default=300, description="Sandbox timeout in seconds")
    max_container_memory: str = Field(default="1g", description="Max container memory")
    
    # File system
    workspace_base: str = Field(default="./workspaces", description="Base directory for workspaces")
    max_file_size: int = Field(default=10 * 1024 * 1024, description="Max file size (10MB)")
    allowed_extensions: List[str] = Field(
        default=[".py", ".js", ".ts", ".html", ".css", ".json", ".md", ".txt", ".yml", ".yaml"],
        description="Allowed file extensions"
    )
    
    # Monitoring
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    log_level: str = Field(default="INFO", description="Log level")
    
    # Frontend
    frontend_url: str = Field(default="http://localhost:3000", description="Frontend URL")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="CORS allowed origins"
    )
    
    class Config:
        env_file = ".env"
        env_prefix = "OPENREPLICA_"


# Global settings instance
settings = Settings()
