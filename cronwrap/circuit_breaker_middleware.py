"""Middleware that wraps a callable with circuit-breaker protection."""
from __future__ import annotations

from typing import Callable

from cronwrap.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitOpenError


class CircuitBreakerMiddleware:
    """Wraps *fn* so that repeated failures trip the circuit and block future runs.

    When the circuit is open, *fn* is not called and ``CircuitOpenError`` is raised
    unless *raise_on_open* is ``False``, in which case a sentinel return value of
    ``-1`` is returned instead.
    """

    def __init__(
        self,
        job_name: str,
        config: CircuitBreakerConfig,
        *,
        raise_on_open: bool = True,
    ) -> None:
        self._breaker = CircuitBreaker(job_name, config)
        self._raise_on_open = raise_on_open

    def run(self, fn: Callable[[], int]) -> int:
        if not self._breaker._config.enabled:
            return fn()

        if self._breaker.is_open():
            if self._raise_on_open:
                raise CircuitOpenError(
                    f"Circuit is open for job '{self._breaker._job_name}'; "
                    "skipping execution until recovery timeout elapses."
                )
            return -1

        exit_code = fn()
        if exit_code == 0:
            self._breaker.record_success()
        else:
            self._breaker.record_failure()
        return exit_code
