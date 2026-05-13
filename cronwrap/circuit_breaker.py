"""Circuit breaker for cron jobs — stops repeated execution when a job is consistently failing."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 3
    recovery_timeout: float = 300.0  # seconds
    state_dir: str = "/tmp/cronwrap/circuit"

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.recovery_timeout < 0:
            raise ValueError("recovery_timeout must be >= 0")

    @property
    def enabled(self) -> bool:
        return self.failure_threshold > 0


class CircuitOpenError(Exception):
    """Raised when the circuit is open and execution is blocked."""


@dataclass
class _State:
    failures: int = 0
    opened_at: Optional[float] = None

    def to_dict(self) -> dict:
        return {"failures": self.failures, "opened_at": self.opened_at}

    @classmethod
    def from_dict(cls, data: dict) -> "_State":
        return cls(failures=data.get("failures", 0), opened_at=data.get("opened_at"))


class CircuitBreaker:
    def __init__(self, job_name: str, config: CircuitBreakerConfig) -> None:
        self._job_name = job_name
        self._config = config
        Path(config.state_dir).mkdir(parents=True, exist_ok=True)

    def _state_path(self) -> Path:
        safe = self._job_name.replace("/", "_").replace(" ", "_")
        return Path(self._config.state_dir) / f"{safe}.json"

    def _load(self) -> _State:
        p = self._state_path()
        if p.exists():
            return _State.from_dict(json.loads(p.read_text()))
        return _State()

    def _save(self, state: _State) -> None:
        self._state_path().write_text(json.dumps(state.to_dict()))

    def is_open(self) -> bool:
        state = self._load()
        if state.opened_at is None:
            return False
        elapsed = time.time() - state.opened_at
        return elapsed < self._config.recovery_timeout

    def record_success(self) -> None:
        self._save(_State())

    def record_failure(self) -> None:
        state = self._load()
        state.failures += 1
        if state.failures >= self._config.failure_threshold:
            state.opened_at = time.time()
        self._save(state)

    def failure_count(self) -> int:
        return self._load().failures

    def reset(self) -> None:
        p = self._state_path()
        if p.exists():
            p.unlink()
