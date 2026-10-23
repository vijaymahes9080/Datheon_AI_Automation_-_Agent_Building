"""Abstract Base Integration Adapter with circuit breaker, retry logic,
and health monitoring.
"""

from abc import ABC, abstractmethod
import logging
import time
from typing import Any, Callable, Dict, Optional
from core.config import IntegrationStatus, settings

logger = logging.getLogger("orbit.integrations")


class BaseIntegrationAdapter(ABC):
    """Abstract base class for all external service adapters."""

    def __init__(self, name: str, error_threshold: int = 3, reset_timeout_seconds: int = 60):
        self.name = name
        self.error_threshold = error_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        self.consecutive_failures = 0
        self.last_failure_timestamp: Optional[float] = None
        self.circuit_open = False

    @property
    def is_demo_mode(self) -> bool:
        """Indicate whether adapter is operating under synthetic mock mode."""
        return settings.DEMO_MODE or not self.is_configured()

    @abstractmethod
    def is_configured(self) -> bool:
        """Check whether required credentials and endpoints are present."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Perform non-destructive connectivity and authorization verification."""
        pass

    def check_circuit_breaker(self) -> None:
        """Enforce circuit breaker to protect external rate limits and downstream APIs."""
        if self.circuit_open:
            if self.last_failure_timestamp and (time.time() - self.last_failure_timestamp > self.reset_timeout_seconds):
                logger.info(f"Circuit breaker for {self.name} resetting to HALF-OPEN.")
                self.circuit_open = False
                self.consecutive_failures = 0
            else:
                raise ConnectionError(
                    f"Circuit breaker for {self.name} is OPEN due to repeated errors. "
                    f"Retry in {int(self.reset_timeout_seconds - (time.time() - (self.last_failure_timestamp or 0)))}s."
                )

    def record_success(self) -> None:
        """Record successful invocation and reset failure counter."""
        self.consecutive_failures = 0
        self.circuit_open = False

    def record_failure(self, error: Exception) -> None:
        """Record failure and trip circuit breaker if threshold is exceeded."""
        self.consecutive_failures += 1
        self.last_failure_timestamp = time.time()
        logger.warning(
            f"Adapter '{self.name}' failure count: {self.consecutive_failures}/{self.error_threshold} - Error: {error}"
        )
        if self.consecutive_failures >= self.error_threshold:
            self.circuit_open = True
            logger.error(f"Circuit breaker for {self.name} is now TRIPPED (OPEN).")

    def execute_with_retry(
        self,
        operation: Callable[..., Any],
        *args: Any,
        max_retries: int = 3,
        base_delay: float = 0.5,
        **kwargs: Any,
    ) -> Any:
        """Execute a callable with exponential backoff and circuit breaker protection."""
        self.check_circuit_breaker()
        last_error: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            try:
                start_time = time.perf_counter()
                result = operation(*args, **kwargs)
                latency = round((time.perf_counter() - start_time) * 1000, 2)
                self.record_success()
                return result
            except Exception as exc:
                last_error = exc
                self.record_failure(exc)
                if attempt == max_retries:
                    break
                sleep_time = base_delay * (2 ** (attempt - 1))
                logger.info(f"Retry attempt {attempt} for {self.name} failed ({exc}). Retrying in {sleep_time:.2f}s...")
                time.sleep(sleep_time)

        raise ConnectionError(f"Operation failed after {max_retries} attempts on {self.name}: {last_error}")
