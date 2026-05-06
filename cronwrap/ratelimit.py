"""Rate limiting for cron jobs — prevents a job from running too frequently."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import json


@dataclass
class RateLimitConfig:
    """Configuration for job rate limiting."""
    min_interval_seconds: int = 0  # 0 means disabled

    def __post_init__(self) -> None:
        if self.min_interval_seconds < 0:
            raise ValueError(
                f"min_interval_seconds must be >= 0, got {self.min_interval_seconds}"
            )

    @property
    def enabled(self) -> bool:
        return self.min_interval_seconds > 0


@dataclass
class RateLimiter:
    """Tracks last-run timestamps and enforces minimum intervals between runs."""
    config: RateLimitConfig
    state_dir: Path = field(default_factory=lambda: Path.home() / ".cronwrap" / "ratelimit")

    def _state_path(self, job_name: str) -> Path:
        return self.state_dir / f"{job_name}.json"

    def _read_last_run(self, job_name: str) -> Optional[float]:
        path = self._state_path(job_name)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return float(data["last_run"])
        except (KeyError, ValueError, json.JSONDecodeError):
            return None

    def _write_last_run(self, job_name: str, timestamp: float) -> None:
        path = self._state_path(job_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"last_run": timestamp}))

    def is_allowed(self, job_name: str) -> bool:
        """Return True if the job is allowed to run now."""
        if not self.config.enabled:
            return True
        last_run = self._read_last_run(job_name)
        if last_run is None:
            return True
        elapsed = time.time() - last_run
        return elapsed >= self.config.min_interval_seconds

    def record_run(self, job_name: str) -> None:
        """Record that the job ran right now."""
        self._write_last_run(job_name, time.time())

    def seconds_until_allowed(self, job_name: str) -> float:
        """Return how many seconds remain before the job may run again (0 if allowed)."""
        if not self.config.enabled:
            return 0.0
        last_run = self._read_last_run(job_name)
        if last_run is None:
            return 0.0
        elapsed = time.time() - last_run
        remaining = self.config.min_interval_seconds - elapsed
        return max(0.0, remaining)
