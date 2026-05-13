"""Middleware that wraps a callable with throttle enforcement."""
from __future__ import annotations

from typing import Callable, Any

from cronwrap.throttle import ThrottleConfig, Throttler, ThrottleViolation


class ThrottleMiddleware:
    """Applies throttle logic around a job function.

    If the job is throttled, *skip_fn* is called (if provided) and the
    middleware returns ``None`` without raising, unless *raise_on_throttle*
    is ``True``.
    """

    def __init__(
        self,
        config: ThrottleConfig,
        job_name: str,
        raise_on_throttle: bool = False,
        skip_fn: Callable[[ThrottleViolation], None] | None = None,
    ) -> None:
        self._throttler = Throttler(config, job_name)
        self._raise = raise_on_throttle
        self._skip_fn = skip_fn

    def run(self, fn: Callable[[], Any]) -> Any:
        """Execute *fn* subject to throttle constraints."""
        try:
            return self._throttler.run(fn)
        except ThrottleViolation as exc:
            if self._skip_fn is not None:
                self._skip_fn(exc)
            if self._raise:
                raise
            return None
