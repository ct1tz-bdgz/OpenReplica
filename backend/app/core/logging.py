"""
Logging configuration for OpenReplica
"""
import logging
import sys
from typing import Dict, Any

import structlog
from python_json_logger import jsonlogger

from app.core.config import get_settings


def setup_logging() -> None:
    """Setup structured logging for the application"""
    settings = get_settings()
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Setup standard logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=settings.log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce noise from external libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("socketio").setLevel(logging.WARNING)
    logging.getLogger("engineio").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin to add structured logging to classes"""
    
    @property
    def logger(self) -> structlog.BoundLogger:
        """Get logger bound to the class name"""
        return get_logger(self.__class__.__name__)


def log_function_call(func_name: str, args: Dict[str, Any] = None) -> None:
    """Log function call with arguments"""
    logger = get_logger("function_call")
    logger.info(
        "Function called",
        function=func_name,
        arguments=args or {}
    )


def log_error(error: Exception, context: Dict[str, Any] = None) -> None:
    """Log error with context"""
    logger = get_logger("error")
    logger.error(
        "Error occurred",
        error=str(error),
        error_type=type(error).__name__,
        context=context or {}
    )


def log_agent_action(agent_type: str, action: str, details: Dict[str, Any] = None) -> None:
    """Log agent action"""
    logger = get_logger("agent")
    logger.info(
        "Agent action",
        agent_type=agent_type,
        action=action,
        details=details or {}
    )


def log_llm_call(provider: str, model: str, tokens_used: int = None, cost: float = None) -> None:
    """Log LLM API call"""
    logger = get_logger("llm")
    logger.info(
        "LLM API call",
        provider=provider,
        model=model,
        tokens_used=tokens_used,
        cost=cost
    )
