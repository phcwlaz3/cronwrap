"""File-based locking to prevent concurrent execution of the same cron job."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class LockAcquisitionError(Exception):
    """Raised when a lock cannot be acquired."""


@dataclass
class LockConfig:
    enabled: bool = False
    lock_dir: str = "/tmp/cronwrap/locks"
    stale_after_seconds: int = 3600

    def __post_init__(self) -> None:
        if self.stale_after_seconds < 0:
            raise ValueError("stale_after_seconds must be >= 0")


class JobLock:
    """Manages a PID-based lock file for a named job."""

    def __init__(self, job_name: str, config: LockConfig) -> None:
        self._config = config
        self._path = Path(config.lock_dir) / f"{job_name}.lock"
        self._acquired = False

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def acquire(self) -> None:
        """Acquire the lock or raise LockAcquisitionError."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

        if self._path.exists():
            if self._is_stale():
                self._path.unlink(missing_ok=True)
            else:
                pid = self._read_pid()
                raise LockAcquisitionError(
                    f"Job already running (pid={pid}, lock={self._path})"
                )

        self._path.write_text(str(os.getpid()))
        self._acquired = True

    def release(self) -> None:
        """Release the lock if we own it."""
        if self._acquired and self._path.exists():
            self._path.unlink(missing_ok=True)
        self._acquired = False

    @property
    def is_held(self) -> bool:
        return self._acquired

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_stale(self) -> bool:
        try:
            age = time.time() - self._path.stat().st_mtime
            return age > self._config.stale_after_seconds
        except OSError:
            return True

    def _read_pid(self) -> Optional[int]:
        try:
            return int(self._path.read_text().strip())
        except (OSError, ValueError):
            return None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "JobLock":
        self.acquire()
        return self

    def __exit__(self, *_) -> None:
        self.release()
