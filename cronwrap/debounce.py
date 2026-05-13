"""Debounce middleware — skips a job run if it was executed too recently.

Unlike the throttle module (which enforces a minimum interval between runs),
debounce is intended to suppress rapid re-triggering: if the job ran within
the debounce window the current invocation is silently skipped and the
caller receives a sentinel return value of ``None``.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


@dataclass
class DebounceConfig:
    """Configuration for the debounce middleware."""

    #: Minimum seconds that must elapse since the last run before a new run
    #: is allowed.  Set to 0 (default) to disable debouncing entirely.
    window_seconds: float = 0.0
    #: Directory used to persist last-run timestamps between processes.
    state_dir: str = "/tmp/cronwrap/debounce"

    def __post_init__(self) -> None:
        if self.window_seconds < 0:
            raise ValueError("window_seconds must be >= 0")

    @property
    def enabled(self) -> bool:
        return self.window_seconds > 0


class DebounceMiddleware:
    """Wraps a callable and skips execution when inside the debounce window."""

    def __init__(self, config: DebounceConfig, job_name: str) -> None:
        self._config = config
        self._job_name = job_name
        self._state_path = (
            Path(config.state_dir) / f"{job_name}.debounce.json"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _last_run(self) -> Optional[float]:
        """Return the timestamp of the last run, or *None* if unknown."""
        try:
            data = json.loads(self._state_path.read_text())
            return float(data["last_run"])
        except (FileNotFoundError, KeyError, ValueError):
            return None

    def _record_run(self) -> None:
        """Persist the current timestamp as the last-run time."""
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps({"last_run": time.time()}))

    def _is_debounced(self) -> bool:
        """Return *True* if the job is still within the debounce window."""
        last = self._last_run()
        if last is None:
            return False
        return (time.time() - last) < self._config.window_seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, fn: Callable, *args, **kwargs):
        """Execute *fn* unless the debounce window is active.

        Returns the callable's return value on execution, or ``None`` when
        the invocation is suppressed.
        """
        if not self._config.enabled:
            return fn(*args, **kwargs)

        if self._is_debounced():
            return None

        result = fn(*args, **kwargs)
        self._record_run()
        return result
