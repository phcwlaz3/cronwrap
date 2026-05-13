"""Throttle middleware: skip execution if a job is already running too frequently."""
from __future__ import annotations

import time
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Any, Optional


@dataclass
class ThrottleConfig:
    """Configuration for job throttling."""
    min_interval_seconds: float = 0.0
    state_dir: str = "/tmp/cronwrap/throttle"

    def __post_init__(self) -> None:
        if self.min_interval_seconds < 0:
            raise ValueError("min_interval_seconds must be >= 0")

    @property
    def enabled(self) -> bool:
        return self.min_interval_seconds > 0


class ThrottleViolation(Exception):
    """Raised when a job is throttled."""


@dataclass
class ThrottleState:
    last_run: Optional[float] = None

    def to_dict(self) -> dict:
        return {"last_run": self.last_run}

    @classmethod
    def from_dict(cls, data: dict) -> "ThrottleState":
        return cls(last_run=data.get("last_run"))


class Throttler:
    """Checks and enforces minimum interval between job runs."""

    def __init__(self, config: ThrottleConfig, job_name: str) -> None:
        self.config = config
        self.job_name = job_name
        self._path = Path(config.state_dir) / f"{job_name}.json"

    def _load_state(self) -> ThrottleState:
        if not self._path.exists():
            return ThrottleState()
        try:
            with open(self._path) as fh:
                return ThrottleState.from_dict(json.load(fh))
        except (json.JSONDecodeError, OSError):
            return ThrottleState()

    def _save_state(self, state: ThrottleState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as fh:
            json.dump(state.to_dict(), fh)

    def check(self) -> None:
        """Raise ThrottleViolation if the job ran too recently."""
        if not self.config.enabled:
            return
        state = self._load_state()
        if state.last_run is not None:
            elapsed = time.time() - state.last_run
            if elapsed < self.config.min_interval_seconds:
                remaining = self.config.min_interval_seconds - elapsed
                raise ThrottleViolation(
                    f"Job '{self.job_name}' throttled; {remaining:.1f}s remaining "
                    f"before next allowed run."
                )

    def record(self) -> None:
        """Record that the job ran right now."""
        state = ThrottleState(last_run=time.time())
        self._save_state(state)

    def run(self, fn: Callable[[], Any]) -> Any:
        """Check throttle, run fn, then record the run time."""
        self.check()
        result = fn()
        self.record()
        return result
