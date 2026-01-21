import time
import logging
import functools
from typing import Callable, Type, Tuple, Optional

logger = logging.getLogger(__name__)


class RetryError(Exception):
    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        super().__init__(message)
        self.last_exception = last_exception


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"[Retry] {func.__name__} failed after {max_attempts} attempts. "
                            f"Last error: {e}"
                        )
                        raise RetryError(
                            f"Max retries ({max_attempts}) exceeded for {func.__name__}",
                            last_exception=e
                        ) from e
                    
                    delay = min(max_delay, base_delay * (exponential_base ** (attempt - 1)))
                    
                    logger.warning(
                        f"[Retry] {func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    time.sleep(delay)
            
            return None
        
        return wrapper
    return decorator
