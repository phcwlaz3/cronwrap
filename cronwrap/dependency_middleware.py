"""Middleware that gates job execution on dependency checks."""
from __future__ import annotations

from typing import Callable, TypeVar

from cronwrap.dependency import DependencyChecker, DependencyConfig, DependencyNotMetError
from cronwrap.history import JobHistory

T = TypeVar("T")


class DependencyMiddleware:
    """Runs a dependency check before invoking the wrapped callable.

    If the config is disabled (no required_jobs), the function is called
    unconditionally.  If the check fails a *DependencyNotMetError* is raised
    and the function is **not** called.
    """

    def __init__(self, config: DependencyConfig, history: JobHistory | None = None) -> None:
        self._checker = DependencyChecker(config, history)
        self._enabled = config.enabled

    def run(self, fn: Callable[[], T]) -> T:
        """Check dependencies then execute *fn*, returning its result."""
        if self._enabled:
            self._checker.check()  # raises DependencyNotMetError if unmet
        return fn()
