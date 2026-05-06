"""Timeout enforcement for cron job execution."""
from __future__ import annotations

import signal
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional


class TimeoutExpired(Exception):
    """Raised when a job exceeds its allowed run time."""

    def __init__(self, timeout_seconds: int) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Job timed out after {timeout_seconds}s")


@dataclass
class TimeoutConfig:
    seconds: int = 0  # 0 means no timeout
    kill_on_expire: bool = True

    def __post_init__(self) -> None:
        if self.seconds < 0:
            raise ValueError("timeout seconds must be >= 0")

    @property
    def enabled(self) -> bool:
        return self.seconds > 0


class TimeoutHandler:
    """Enforces a wall-clock timeout around a callable."""

    def __init__(self, config: TimeoutConfig) -> None:
        self._config = config

    def run(self, func: Callable[[], int]) -> int:
        """Run *func* and return its exit code, raising TimeoutExpired if needed."""
        if not self._config.enabled:
            return func()

        result: dict = {"code": None, "exc": None}

        def _target() -> None:
            try:
                result["code"] = func()
            except Exception as exc:  # noqa: BLE001
                result["exc"] = exc

        thread = threading.Thread(target=_target, daemon=True)
        thread.start()
        thread.join(timeout=self._config.seconds)

        if thread.is_alive():
            raise TimeoutExpired(self._config.seconds)

        if result["exc"] is not None:
            raise result["exc"]

        return result["code"]  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # SIGALRM-based alternative (Unix only)
    # ------------------------------------------------------------------
    def run_with_sigalrm(self, func: Callable[[], int]) -> int:
        """Unix-only SIGALRM variant; falls back to thread-based on Windows."""
        if not self._config.enabled:
            return func()

        if not hasattr(signal, "SIGALRM"):
            return self.run(func)

        def _handler(signum: int, frame: object) -> None:  # noqa: ARG001
            raise TimeoutExpired(self._config.seconds)

        old = signal.signal(signal.SIGALRM, _handler)
        signal.alarm(self._config.seconds)
        try:
            return func()
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
