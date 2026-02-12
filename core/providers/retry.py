import time
import logging
import functools
import threading
from typing import Callable, Type, Tuple, Optional, Dict

logger = logging.getLogger(__name__)


class RetryError(Exception):
    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        super().__init__(message)
        self.last_exception = last_exception


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_success_threshold: int = 1
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_success_threshold = half_open_success_threshold
        self.state = "closed"
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self._lock = threading.Lock()

    def allow_request(self) -> bool:
        with self._lock:
            if self.state == "open":
                if time.monotonic() - self.last_failure_time >= self.recovery_timeout:
                    self.state = "half_open"
                    self.success_count = 0
                    return True
                return False
            return True

    def record_success(self) -> None:
        with self._lock:
            self.failure_count = 0
            if self.state == "half_open":
                self.success_count += 1
                if self.success_count >= self.half_open_success_threshold:
                    self.state = "closed"
                    self.success_count = 0
            else:
                self.state = "closed"

    def record_failure(self) -> None:
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.monotonic()
            if self.failure_count >= self.failure_threshold:
                self.state = "open"

    def snapshot(self) -> Dict[str, float]:
        with self._lock:
            return {
                "state": self.state,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "last_failure_time": self.last_failure_time,
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout
            }


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
