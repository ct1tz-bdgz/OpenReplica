"""
LLM metrics tracking for OpenReplica matching OpenHands
"""
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TokenUsage:
    """Token usage information"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0


@dataclass
class CompletionMetrics:
    """Metrics for a single completion"""
    model: str
    timestamp: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    duration: float = 0.0
    success: bool = True
    error: Optional[str] = None


class Metrics:
    """LLM metrics collector and tracker"""
    
    def __init__(self):
        self.completions: List[CompletionMetrics] = []
        self.total_cost = 0.0
        self.total_tokens = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.model_usage: Dict[str, TokenUsage] = {}
        self.start_time = time.time()
    
    def add_completion(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
        duration: float = 0.0,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Add a completion to metrics"""
        total_tokens = prompt_tokens + completion_tokens
        
        completion = CompletionMetrics(
            model=model,
            timestamp=time.time(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            duration=duration,
            success=success,
            error=error
        )
        
        self.completions.append(completion)
        
        # Update totals
        self.total_cost += cost
        self.total_tokens += total_tokens
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        
        # Update model-specific usage
        if model not in self.model_usage:
            self.model_usage[model] = TokenUsage()
        
        model_usage = self.model_usage[model]
        model_usage.prompt_tokens += prompt_tokens
        model_usage.completion_tokens += completion_tokens
        model_usage.total_tokens += total_tokens
        model_usage.cost += cost
        
        logger.debug(f"LLM Metrics - Model: {model}, Tokens: {total_tokens}, Cost: ${cost:.4f}")
    
    def get_total_cost(self) -> float:
        """Get total cost across all completions"""
        return self.total_cost
    
    def get_total_tokens(self) -> int:
        """Get total tokens across all completions"""
        return self.total_tokens
    
    def get_model_usage(self, model: str) -> TokenUsage:
        """Get usage for a specific model"""
        return self.model_usage.get(model, TokenUsage())
    
    def get_completion_count(self) -> int:
        """Get total number of completions"""
        return len(self.completions)
    
    def get_success_rate(self) -> float:
        """Get success rate of completions"""
        if not self.completions:
            return 0.0
        
        successful = sum(1 for c in self.completions if c.success)
        return successful / len(self.completions)
    
    def get_average_tokens_per_completion(self) -> float:
        """Get average tokens per completion"""
        if not self.completions:
            return 0.0
        
        return self.total_tokens / len(self.completions)
    
    def get_average_cost_per_completion(self) -> float:
        """Get average cost per completion"""
        if not self.completions:
            return 0.0
        
        return self.total_cost / len(self.completions)
    
    def get_average_duration(self) -> float:
        """Get average completion duration"""
        if not self.completions:
            return 0.0
        
        total_duration = sum(c.duration for c in self.completions if c.duration > 0)
        count_with_duration = sum(1 for c in self.completions if c.duration > 0)
        
        if count_with_duration == 0:
            return 0.0
        
        return total_duration / count_with_duration
    
    def get_summary(self) -> Dict[str, any]:
        """Get comprehensive metrics summary"""
        return {
            'total_completions': self.get_completion_count(),
            'total_cost': self.total_cost,
            'total_tokens': self.total_tokens,
            'total_prompt_tokens': self.total_prompt_tokens,
            'total_completion_tokens': self.total_completion_tokens,
            'success_rate': self.get_success_rate(),
            'average_tokens_per_completion': self.get_average_tokens_per_completion(),
            'average_cost_per_completion': self.get_average_cost_per_completion(),
            'average_duration': self.get_average_duration(),
            'session_duration': time.time() - self.start_time,
            'models_used': list(self.model_usage.keys()),
            'model_usage': {
                model: {
                    'prompt_tokens': usage.prompt_tokens,
                    'completion_tokens': usage.completion_tokens,
                    'total_tokens': usage.total_tokens,
                    'cost': usage.cost
                }
                for model, usage in self.model_usage.items()
            }
        }
    
    def get_recent_completions(self, limit: int = 10) -> List[CompletionMetrics]:
        """Get recent completions"""
        return self.completions[-limit:] if self.completions else []
    
    def get_completions_by_model(self, model: str) -> List[CompletionMetrics]:
        """Get completions for a specific model"""
        return [c for c in self.completions if c.model == model]
    
    def get_failed_completions(self) -> List[CompletionMetrics]:
        """Get failed completions"""
        return [c for c in self.completions if not c.success]
    
    def reset(self):
        """Reset all metrics"""
        self.completions.clear()
        self.total_cost = 0.0
        self.total_tokens = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.model_usage.clear()
        self.start_time = time.time()
    
    def export_to_dict(self) -> Dict[str, any]:
        """Export metrics to dictionary for serialization"""
        return {
            'completions': [
                {
                    'model': c.model,
                    'timestamp': c.timestamp,
                    'prompt_tokens': c.prompt_tokens,
                    'completion_tokens': c.completion_tokens,
                    'total_tokens': c.total_tokens,
                    'cost': c.cost,
                    'duration': c.duration,
                    'success': c.success,
                    'error': c.error
                }
                for c in self.completions
            ],
            'summary': self.get_summary()
        }
    
    def __repr__(self):
        return (
            f"Metrics(completions={len(self.completions)}, "
            f"total_cost=${self.total_cost:.4f}, "
            f"total_tokens={self.total_tokens})"
        )
