"""
Retry mixin for LLM operations matching OpenHands
"""
import asyncio
import random
import time
from functools import wraps
from typing import Any, Callable

from app.core.logging import get_logger

logger = get_logger(__name__)


class RetryMixin:
    """Mixin class for retrying LLM operations with exponential backoff"""
    
    def __init__(self):
        self.max_retries = getattr(self, 'max_retries', 3)
        self.base_delay = getattr(self, 'base_delay', 1.0)
        self.max_delay = getattr(self, 'max_delay', 60.0)
        self.exponential_base = getattr(self, 'exponential_base', 2.0)
        self.jitter = getattr(self, 'jitter', True)
    
    def retry_on_exception(self, exceptions: tuple, max_retries: int = None):
        """Decorator for retrying functions on specific exceptions"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                return self._retry_with_backoff(
                    func, args, kwargs, exceptions, max_retries or self.max_retries
                )
            return wrapper
        return decorator
    
    def _retry_with_backoff(
        self, 
        func: Callable, 
        args: tuple, 
        kwargs: dict, 
        exceptions: tuple,
        max_retries: int
    ) -> Any:
        """Execute function with exponential backoff retry logic"""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                
                if attempt == max_retries:
                    logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}")
                    raise e
                
                delay = self._calculate_delay(attempt)
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                    f"Retrying in {delay:.2f} seconds..."
                )
                time.sleep(delay)
            except Exception as e:
                # Don't retry on non-specified exceptions
                logger.error(f"Non-retryable error in {func.__name__}: {e}")
                raise e
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception
    
    async def async_retry_with_backoff(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        exceptions: tuple,
        max_retries: int
    ) -> Any:
        """Async version of retry with backoff"""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                
                if attempt == max_retries:
                    logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}")
                    raise e
                
                delay = self._calculate_delay(attempt)
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                    f"Retrying in {delay:.2f} seconds..."
                )
                await asyncio.sleep(delay)
            except Exception as e:
                # Don't retry on non-specified exceptions
                logger.error(f"Non-retryable error in {func.__name__}: {e}")
                raise e
        
        if last_exception:
            raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for exponential backoff with jitter"""
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        
        if self.jitter:
            # Add random jitter of ±25%
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay)  # Ensure delay is never negative
        
        return delay
    
    def configure_retry(
        self,
        max_retries: int = None,
        base_delay: float = None,
        max_delay: float = None,
        exponential_base: float = None,
        jitter: bool = None
    ):
        """Configure retry parameters"""
        if max_retries is not None:
            self.max_retries = max_retries
        if base_delay is not None:
            self.base_delay = base_delay
        if max_delay is not None:
            self.max_delay = max_delay
        if exponential_base is not None:
            self.exponential_base = exponential_base
        if jitter is not None:
            self.jitter = jitter
