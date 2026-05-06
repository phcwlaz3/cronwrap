"""Middleware that wraps JobRunner execution with optional locking."""

from __future__ import annotations

from typing import Callable

from cronwrap.lock import JobLock, LockAcquisitionError, LockConfig


class LockMiddleware:
    """Wraps a callable with a JobLock guard.

    If locking is disabled the callable is invoked directly.
    If the lock cannot be acquired the middleware returns the
    ``skip_exit_code`` (default 0) without running the job.
    """

    def __init__(
        self,
        job_name: str,
        config: LockConfig,
        *,
        skip_exit_code: int = 0,
    ) -> None:
        self._job_name = job_name
        self._config = config
        self._skip_exit_code = skip_exit_code

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, fn: Callable[[], int]) -> int:
        """Run *fn* protected by the lock; return its exit code.

        Returns ``skip_exit_code`` if the lock is already held.
        """
        if not self._config.enabled:
            return fn()

        lock = JobLock(self._job_name, self._config)
        try:
            lock.acquire()
        except LockAcquisitionError:
            return self._skip_exit_code

        try:
            return fn()
        finally:
            lock.release()
