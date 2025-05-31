"""
Debug mixin for LLM interactions
"""
import json
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class DebugMixin:
    """Mixin class for debugging LLM interactions"""
    
    def debug_log(self, message: str, data: Any = None):
        """Log debug information"""
        if data:
            logger.debug(f"{message}: {json.dumps(data, indent=2, default=str)}")
        else:
            logger.debug(message)
    
    def log_request(self, messages: list, **kwargs):
        """Log LLM request"""
        self.debug_log("LLM Request", {
            "model": getattr(self, 'model_name', 'unknown'),
            "messages": messages,
            "kwargs": kwargs
        })
    
    def log_response(self, response: Any):
        """Log LLM response"""
        self.debug_log("LLM Response", {
            "model": getattr(self, 'model_name', 'unknown'),
            "response": response
        })
    
    def log_error(self, error: Exception):
        """Log LLM error"""
        logger.error(f"LLM Error: {error}")
