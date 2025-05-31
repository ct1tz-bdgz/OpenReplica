"""
Settings data model for OpenReplica matching OpenHands exactly
"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, SecretStr


class Settings(BaseModel):
    """User settings model"""
    
    # LLM Configuration
    llm_model: Optional[str] = Field(default="claude-3-5-sonnet-20241022")
    llm_api_key: Optional[SecretStr] = Field(default=None)
    llm_base_url: Optional[str] = Field(default=None)
    llm_api_version: Optional[str] = Field(default=None)
    llm_custom_provider: Optional[str] = Field(default=None)
    
    # Search API Configuration
    search_api_key: Optional[SecretStr] = Field(default=None)
    taviily_api_key: Optional[SecretStr] = Field(default=None)
    
    # Provider API Keys
    openai_api_key: Optional[SecretStr] = Field(default=None)
    anthropic_api_key: Optional[SecretStr] = Field(default=None)
    google_api_key: Optional[SecretStr] = Field(default=None)
    cohere_api_key: Optional[SecretStr] = Field(default=None)
    openrouter_api_key: Optional[SecretStr] = Field(default=None)
    ollama_base_url: Optional[str] = Field(default="http://localhost:11434")
    
    # Agent Configuration
    agent_class: Optional[str] = Field(default="CodeActAgent")
    max_iterations: Optional[int] = Field(default=100)
    
    # Runtime Configuration
    remote_runtime_resource_factor: Optional[int] = Field(default=1)
    workspace_base: Optional[str] = Field(default="/tmp/openreplica")
    
    # UI Preferences
    theme: Optional[str] = Field(default="dark")
    language: Optional[str] = Field(default="en")
    
    # Privacy and Analytics
    user_consents_to_analytics: Optional[bool] = Field(default=False)
    
    # Git Integration
    github_token: Optional[SecretStr] = Field(default=None)
    gitlab_token: Optional[SecretStr] = Field(default=None)
    
    # Advanced Settings
    security_scan_enabled: Optional[bool] = Field(default=True)
    auto_save_enabled: Optional[bool] = Field(default=True)
    
    # User Information
    user_id: Optional[str] = Field(default=None)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    # Custom Settings
    custom_settings: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    model_config = {
        'use_enum_values': True,
        'validate_assignment': True
    }
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration as dictionary"""
        config = {
            'model': self.llm_model,
            'api_key': self.llm_api_key.get_secret_value() if self.llm_api_key else None,
            'base_url': self.llm_base_url,
            'api_version': self.llm_api_version,
            'custom_llm_provider': self.llm_custom_provider,
        }
        
        # Add provider-specific configurations
        if self.openai_api_key:
            config['openai_api_key'] = self.openai_api_key.get_secret_value()
        if self.anthropic_api_key:
            config['anthropic_api_key'] = self.anthropic_api_key.get_secret_value()
        if self.google_api_key:
            config['google_api_key'] = self.google_api_key.get_secret_value()
        if self.cohere_api_key:
            config['cohere_api_key'] = self.cohere_api_key.get_secret_value()
        if self.openrouter_api_key:
            config['openrouter_api_key'] = self.openrouter_api_key.get_secret_value()
        if self.ollama_base_url:
            config['ollama_base_url'] = self.ollama_base_url
        
        return {k: v for k, v in config.items() if v is not None}
    
    def get_search_config(self) -> Dict[str, Any]:
        """Get search configuration"""
        config = {}
        
        if self.search_api_key:
            config['search_api_key'] = self.search_api_key.get_secret_value()
        if self.taviily_api_key:
            config['taviily_api_key'] = self.taviily_api_key.get_secret_value()
        
        return config
    
    def get_git_config(self) -> Dict[str, Any]:
        """Get git integration configuration"""
        config = {}
        
        if self.github_token:
            config['github_token'] = self.github_token.get_secret_value()
        if self.gitlab_token:
            config['gitlab_token'] = self.gitlab_token.get_secret_value()
        
        return config
    
    def update_timestamp(self):
        """Update the updated_at timestamp"""
        self.updated_at = datetime.utcnow()
    
    def to_safe_dict(self) -> Dict[str, Any]:
        """Convert to dictionary without exposing secrets"""
        data = self.model_dump()
        
        # Remove or mask secret fields
        secret_fields = [
            'llm_api_key', 'search_api_key', 'taviily_api_key',
            'openai_api_key', 'anthropic_api_key', 'google_api_key',
            'cohere_api_key', 'openrouter_api_key', 'github_token', 'gitlab_token'
        ]
        
        for field in secret_fields:
            if field in data and data[field] is not None:
                data[f'{field}_set'] = True
                data[field] = None
            else:
                data[f'{field}_set'] = False
        
        return data


class ConversationMetadata(BaseModel):
    """Conversation metadata model"""
    
    conversation_id: str
    title: Optional[str] = Field(default="Untitled Conversation")
    agent_class: Optional[str] = Field(default="CodeActAgent")
    llm_model: Optional[str] = Field(default="claude-3-5-sonnet-20241022")
    status: Optional[str] = Field(default="active")
    selected_repository: Optional[str] = Field(default=None)
    last_message: Optional[str] = Field(default=None)
    message_count: Optional[int] = Field(default=0)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    # Additional metadata
    tags: Optional[list[str]] = Field(default_factory=list)
    workspace_path: Optional[str] = Field(default=None)
    runtime_id: Optional[str] = Field(default=None)
    total_iterations: Optional[int] = Field(default=0)
    total_cost: Optional[float] = Field(default=0.0)
    
    model_config = {
        'use_enum_values': True,
        'validate_assignment': True
    }


class UserProfile(BaseModel):
    """User profile model"""
    
    user_id: str
    username: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    full_name: Optional[str] = Field(default=None)
    avatar_url: Optional[str] = Field(default=None)
    
    # Preferences
    preferred_language: Optional[str] = Field(default="en")
    preferred_theme: Optional[str] = Field(default="dark")
    timezone: Optional[str] = Field(default="UTC")
    
    # Usage statistics
    total_conversations: Optional[int] = Field(default=0)
    total_messages: Optional[int] = Field(default=0)
    total_tokens_used: Optional[int] = Field(default=0)
    total_cost: Optional[float] = Field(default=0.0)
    
    # Account info
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(default=None)
    is_active: Optional[bool] = Field(default=True)
    
    model_config = {
        'use_enum_values': True,
        'validate_assignment': True
    }
