"""Jitter support for cron jobs — adds randomised delay before execution.

Useful for preventing thundering-herd problems when many cron jobs
start simultaneously (e.g. on the hour).
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class JitterConfig:
    """Configuration for pre-execution jitter delay."""

    max_seconds: float = 0.0
    """Maximum number of seconds to sleep before running the job.
    A value of 0 disables jitter entirely."""

    seed: Optional[int] = field(default=None, repr=False)
    """Optional RNG seed for deterministic testing."""

    def __post_init__(self) -> None:
        if self.max_seconds < 0:
            raise ValueError(
                f"max_seconds must be >= 0, got {self.max_seconds}"
            )

    @property
    def enabled(self) -> bool:
        """Return True when jitter is active."""
        return self.max_seconds > 0


class JitterMiddleware:
    """Sleeps for a random duration before invoking *fn*.

    Parameters
    ----------
    config:
        A :class:`JitterConfig` that controls the delay window.
    sleep_fn:
        Callable used to sleep; defaults to :func:`time.sleep`.  Inject a
        no-op or mock in tests to avoid real delays.
    rng:
        Optional :class:`random.Random` instance.  A fresh instance seeded
        from ``config.seed`` is created when not provided.
    """

    def __init__(
        self,
        config: JitterConfig,
        *,
        sleep_fn: Callable[[float], None] = time.sleep,
        rng: Optional[random.Random] = None,
    ) -> None:
        self._config = config
        self._sleep = sleep_fn
        self._rng = rng if rng is not None else random.Random(config.seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, fn: Callable[[], int]) -> int:
        """Apply jitter delay then call *fn*, returning its exit code."""
        if self._config.enabled:
            delay = self._rng.uniform(0, self._config.max_seconds)
            self._sleep(delay)
        return fn()

    @property
    def config(self) -> JitterConfig:
        """Expose the active configuration (read-only)."""
        return self._config
