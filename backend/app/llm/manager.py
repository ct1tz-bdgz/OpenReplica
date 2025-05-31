"""
LLM Manager for OpenReplica with full provider customization
Supports any LLM provider through litellm, matching OpenHands exactly but with improvements
"""
import os
from typing import Dict, Any, Optional, List, Union
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.config import LLMConfig
from app.llm.llm import LLM
from app.llm.metrics import Metrics
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMManager:
    """
    Advanced LLM Manager supporting multiple providers and models
    with automatic failover, load balancing, and cost optimization
    """
    
    def __init__(self):
        self.llms: Dict[str, LLM] = {}
        self.configs: Dict[str, LLMConfig] = {}
        self.global_metrics = Metrics()
        self.default_model: Optional[str] = None
        self.fallback_models: List[str] = []
        self.load_balancing_enabled = False
        self.cost_optimization_enabled = False
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Provider-specific configurations
        self.provider_configs = {
            'openai': {
                'api_key_env': 'OPENAI_API_KEY',
                'base_url_env': 'OPENAI_API_BASE',
                'default_models': ['gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo'],
                'supports_vision': True,
                'supports_function_calling': True,
            },
            'anthropic': {
                'api_key_env': 'ANTHROPIC_API_KEY',
                'base_url_env': 'ANTHROPIC_API_BASE',
                'default_models': ['claude-3-5-sonnet-20241022', 'claude-3-haiku-20240307'],
                'supports_vision': True,
                'supports_function_calling': True,
            },
            'google': {
                'api_key_env': 'GOOGLE_API_KEY',
                'base_url_env': 'GOOGLE_API_BASE',
                'default_models': ['gemini-pro', 'gemini-pro-vision'],
                'supports_vision': True,
                'supports_function_calling': True,
            },
            'cohere': {
                'api_key_env': 'COHERE_API_KEY',
                'base_url_env': 'COHERE_API_BASE',
                'default_models': ['command-r-plus', 'command-r'],
                'supports_vision': False,
                'supports_function_calling': True,
            },
            'azure': {
                'api_key_env': 'AZURE_API_KEY',
                'base_url_env': 'AZURE_API_BASE',
                'default_models': ['azure/gpt-4o', 'azure/gpt-4-turbo'],
                'supports_vision': True,
                'supports_function_calling': True,
            },
            'ollama': {
                'api_key_env': None,
                'base_url_env': 'OLLAMA_API_BASE',
                'default_models': ['llama3', 'codellama', 'mistral'],
                'supports_vision': False,
                'supports_function_calling': False,
            },
            'huggingface': {
                'api_key_env': 'HUGGINGFACE_API_KEY',
                'base_url_env': 'HUGGINGFACE_API_BASE',
                'default_models': ['meta-llama/Llama-2-70b-chat-hf'],
                'supports_vision': False,
                'supports_function_calling': False,
            },
            'bedrock': {
                'api_key_env': 'AWS_ACCESS_KEY_ID',
                'base_url_env': None,
                'default_models': ['bedrock/anthropic.claude-3-sonnet-20240229-v1:0'],
                'supports_vision': True,
                'supports_function_calling': True,
            },
            'vertex': {
                'api_key_env': 'GOOGLE_APPLICATION_CREDENTIALS',
                'base_url_env': None,
                'default_models': ['vertex_ai/gemini-pro'],
                'supports_vision': True,
                'supports_function_calling': True,
            }
        }
    
    def register_llm(self, name: str, config: LLMConfig) -> LLM:
        """Register a new LLM with enhanced configuration"""
        # Enhance config with provider-specific settings
        enhanced_config = self._enhance_config(config)
        
        # Create LLM instance
        llm = LLM(enhanced_config, metrics=self.global_metrics)
        
        # Store in registry
        self.llms[name] = llm
        self.configs[name] = enhanced_config
        
        # Set as default if it's the first one
        if self.default_model is None:
            self.default_model = name
        
        logger.info(f"Registered LLM: {name} with model {enhanced_config.model}")
        return llm
    
    def get_llm(self, name: Optional[str] = None) -> Optional[LLM]:
        """Get LLM by name or default"""
        if name is None:
            name = self.default_model
        
        if name and name in self.llms:
            return self.llms[name]
        
        # Try fallback models
        for fallback in self.fallback_models:
            if fallback in self.llms:
                logger.warning(f"Using fallback model {fallback} instead of {name}")
                return self.llms[fallback]
        
        return None
    
    def get_best_llm_for_task(
        self, 
        task_type: str = 'general',
        requirements: Dict[str, Any] = None
    ) -> Optional[LLM]:
        """
        Get the best LLM for a specific task type with intelligent selection
        This is an improvement over OpenHands - automatic model selection
        """
        requirements = requirements or {}
        
        # Score models based on requirements
        scored_models = []
        
        for name, llm in self.llms.items():
            score = self._score_model_for_task(llm, task_type, requirements)
            if score > 0:
                scored_models.append((score, name, llm))
        
        # Sort by score (descending) and cost (ascending) if cost optimization enabled
        if self.cost_optimization_enabled:
            scored_models.sort(key=lambda x: (-x[0], self._get_model_cost_score(x[2])))
        else:
            scored_models.sort(key=lambda x: -x[0])
        
        if scored_models:
            selected = scored_models[0]
            logger.info(f"Selected model {selected[1]} for task {task_type} (score: {selected[0]})")
            return selected[2]
        
        return self.get_llm()  # Fallback to default
    
    def _score_model_for_task(
        self, 
        llm: LLM, 
        task_type: str, 
        requirements: Dict[str, Any]
    ) -> float:
        """Score a model for a specific task"""
        score = 1.0  # Base score
        
        # Task-specific scoring
        if task_type == 'code':
            if 'code' in llm.model_name.lower():
                score += 2.0
            if any(x in llm.model_name.lower() for x in ['gpt-4', 'claude-3', 'gemini-pro']):
                score += 1.5
        
        elif task_type == 'vision':
            if requirements.get('vision_required', False):
                if llm.supports_vision:
                    score += 3.0
                else:
                    return 0.0  # Can't handle vision tasks
        
        elif task_type == 'function_calling':
            if requirements.get('function_calling_required', False):
                if llm.supports_function_calling:
                    score += 2.0
                else:
                    return 0.0  # Can't handle function calling
        
        elif task_type == 'reasoning':
            if any(x in llm.model_name.lower() for x in ['o1', 'o3', 'claude-3']):
                score += 2.0
        
        # Performance bonuses
        model_info = llm.get_model_info()
        if model_info:
            # Prefer models with higher context windows for complex tasks
            max_tokens = model_info.get('max_tokens', 4096)
            if max_tokens > 32000:
                score += 1.0
            elif max_tokens > 16000:
                score += 0.5
        
        return score
    
    def _get_model_cost_score(self, llm: LLM) -> float:
        """Get cost score for model (lower is better for cost optimization)"""
        # This would integrate with actual pricing data
        # For now, use rough estimates based on model names
        model_name = llm.model_name.lower()
        
        if 'gpt-4o' in model_name:
            return 1.0
        elif 'gpt-4' in model_name:
            return 2.0
        elif 'claude-3-5-sonnet' in model_name:
            return 1.5
        elif 'claude-3-haiku' in model_name:
            return 0.5
        elif 'gpt-3.5' in model_name:
            return 0.3
        elif 'gemini' in model_name:
            return 0.8
        elif 'ollama' in model_name:
            return 0.1  # Local models are cheapest
        else:
            return 1.0  # Default
    
    def _enhance_config(self, config: LLMConfig) -> LLMConfig:
        """Enhance config with provider-specific settings"""
        enhanced = LLMConfig(**config.dict())
        
        # Auto-detect provider from model name
        provider = self._detect_provider(enhanced.model)
        if provider and provider in self.provider_configs:
            provider_config = self.provider_configs[provider]
            
            # Set API key from environment if not provided
            if not enhanced.api_key and provider_config['api_key_env']:
                enhanced.api_key = os.getenv(provider_config['api_key_env'])
            
            # Set base URL from environment if not provided
            if not enhanced.base_url and provider_config['base_url_env']:
                enhanced.base_url = os.getenv(provider_config['base_url_env'])
            
            # Set provider-specific defaults
            if provider == 'ollama' and not enhanced.base_url:
                enhanced.base_url = 'http://localhost:11434'
        
        return enhanced
    
    def _detect_provider(self, model_name: str) -> Optional[str]:
        """Auto-detect provider from model name"""
        model_lower = model_name.lower()
        
        if model_lower.startswith('gpt-') or model_lower.startswith('o1-') or model_lower.startswith('o3-'):
            return 'openai'
        elif model_lower.startswith('claude-'):
            return 'anthropic'
        elif model_lower.startswith('gemini-'):
            return 'google'
        elif model_lower.startswith('command-'):
            return 'cohere'
        elif model_lower.startswith('azure/'):
            return 'azure'
        elif model_lower.startswith('bedrock/'):
            return 'bedrock'
        elif model_lower.startswith('vertex_ai/'):
            return 'vertex'
        elif '/' in model_name and 'huggingface' in model_lower:
            return 'huggingface'
        elif any(x in model_lower for x in ['llama', 'mistral', 'codellama']):
            return 'ollama'
        
        return None
    
    async def get_available_models(self, provider: Optional[str] = None) -> Dict[str, List[str]]:
        """Get available models by provider"""
        available = {}
        
        for provider_name, config in self.provider_configs.items():
            if provider and provider != provider_name:
                continue
                
            try:
                # This would query the actual provider API for available models
                # For now, return the default models
                available[provider_name] = config['default_models']
            except Exception as e:
                logger.warning(f"Failed to get models for {provider_name}: {e}")
                available[provider_name] = []
        
        return available
    
    def setup_automatic_failover(self, fallback_models: List[str]):
        """Setup automatic failover to backup models"""
        self.fallback_models = fallback_models
        logger.info(f"Configured failover models: {fallback_models}")
    
    def enable_load_balancing(self, enabled: bool = True):
        """Enable/disable load balancing across multiple models"""
        self.load_balancing_enabled = enabled
        logger.info(f"Load balancing {'enabled' if enabled else 'disabled'}")
    
    def enable_cost_optimization(self, enabled: bool = True):
        """Enable/disable cost optimization in model selection"""
        self.cost_optimization_enabled = enabled
        logger.info(f"Cost optimization {'enabled' if enabled else 'disabled'}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics across all LLMs"""
        summary = self.global_metrics.get_summary()
        
        # Add per-model metrics
        summary['per_model_metrics'] = {}
        for name, llm in self.llms.items():
            if hasattr(llm, 'metrics') and llm.metrics:
                summary['per_model_metrics'][name] = llm.metrics.get_summary()
        
        return summary
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.global_metrics.reset()
        for llm in self.llms.values():
            if hasattr(llm, 'metrics') and llm.metrics:
                llm.metrics.reset()
    
    def list_llms(self) -> Dict[str, Dict[str, Any]]:
        """List all registered LLMs with their info"""
        result = {}
        for name, llm in self.llms.items():
            config = self.configs[name]
            model_info = llm.get_model_info()
            
            result[name] = {
                'model': config.model,
                'provider': self._detect_provider(config.model),
                'supports_vision': llm.supports_vision,
                'supports_function_calling': llm.supports_function_calling,
                'max_tokens': model_info.get('max_tokens') if model_info else None,
                'is_default': name == self.default_model,
            }
        
        return result
    
    async def test_llm_connection(self, name: str) -> Dict[str, Any]:
        """Test connection to an LLM"""
        llm = self.get_llm(name)
        if not llm:
            return {'success': False, 'error': f'LLM {name} not found'}
        
        try:
            # Try a simple completion
            from app.core.message import Message
            test_message = Message(role='user', content='Hello, can you respond with just "OK"?')
            
            response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                llm.completion,
                [test_message]
            )
            
            return {
                'success': True,
                'model': llm.model_name,
                'response_length': len(response.choices[0].message.content or ''),
                'tokens_used': response.usage.total_tokens if response.usage else 0
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def close(self):
        """Close the LLM manager and cleanup resources"""
        self.executor.shutdown(wait=True)
        self.llms.clear()
        self.configs.clear()


# Global LLM manager instance
_llm_manager: Optional[LLMManager] = None


def get_llm_manager() -> LLMManager:
    """Get the global LLM manager instance"""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager


def setup_default_llms() -> LLMManager:
    """Setup default LLM configurations from environment"""
    manager = get_llm_manager()
    
    # OpenAI models
    if os.getenv('OPENAI_API_KEY'):
        for model in ['gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo']:
            config = LLMConfig(
                model=model,
                api_key=os.getenv('OPENAI_API_KEY'),
                base_url=os.getenv('OPENAI_API_BASE'),
                temperature=0.7,
                max_output_tokens=4000,
                timeout=60
            )
            manager.register_llm(f"openai_{model.replace('-', '_')}", config)
    
    # Anthropic models
    if os.getenv('ANTHROPIC_API_KEY'):
        for model in ['claude-3-5-sonnet-20241022', 'claude-3-haiku-20240307']:
            config = LLMConfig(
                model=model,
                api_key=os.getenv('ANTHROPIC_API_KEY'),
                temperature=0.7,
                max_output_tokens=4000,
                timeout=60
            )
            manager.register_llm(f"anthropic_{model.replace('-', '_').replace('.', '_')}", config)
    
    # Local Ollama models
    if os.getenv('OLLAMA_API_BASE') or True:  # Assume Ollama might be available
        for model in ['llama3', 'codellama']:
            config = LLMConfig(
                model=model,
                base_url=os.getenv('OLLAMA_API_BASE', 'http://localhost:11434'),
                temperature=0.7,
                max_output_tokens=4000,
                timeout=60
            )
            try:
                manager.register_llm(f"ollama_{model}", config)
            except Exception as e:
                logger.warning(f"Failed to register Ollama model {model}: {e}")
    
    return manager
