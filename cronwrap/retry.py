"""Retry logic for cron job execution."""

import time
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behaviour."""

    max_attempts: int = 3
    delay_seconds: float = 5.0
    backoff_factor: float = 2.0
    exceptions: tuple = field(default_factory=lambda: (Exception,))

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.delay_seconds < 0:
            raise ValueError("delay_seconds must be non-negative")
        if self.backoff_factor < 1.0:
            raise ValueError("backoff_factor must be >= 1.0")


class RetryHandler:
    """Executes a callable with configurable retry logic."""

    def __init__(self, config: Optional[RetryConfig] = None) -> None:
        self.config = config or RetryConfig()

    def run(self, func: Callable, *args, **kwargs):
        """Run *func* with retries.  Returns the function's return value.

        Raises the last exception if all attempts are exhausted.
        """
        config = self.config
        delay = config.delay_seconds
        last_exc: Optional[Exception] = None

        for attempt in range(1, config.max_attempts + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 1:
                    logger.info(
                        "Attempt %d/%d succeeded.", attempt, config.max_attempts
                    )
                return result
            except config.exceptions as exc:  # type: ignore[misc]
                last_exc = exc
                logger.warning(
                    "Attempt %d/%d failed: %s",
                    attempt,
                    config.max_attempts,
                    exc,
                )
                if attempt < config.max_attempts:
                    logger.debug("Retrying in %.1f seconds…", delay)
                    time.sleep(delay)
                    delay *= config.backoff_factor

        raise last_exc  # type: ignore[misc]
