"""Job dependency checking — ensure prerequisite jobs succeeded before running."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronwrap.history import JobHistory


class DependencyNotMetError(Exception):
    """Raised when one or more job dependencies have not been satisfied."""


@dataclass
class DependencyConfig:
    """Configuration for job dependency checks."""

    required_jobs: List[str] = field(default_factory=list)
    # Maximum age (seconds) of a successful run that counts as "met".  0 = any age.
    max_age_seconds: int = 0

    def __post_init__(self) -> None:
        if self.max_age_seconds < 0:
            raise ValueError("max_age_seconds must be >= 0")

    @property
    def enabled(self) -> bool:
        return bool(self.required_jobs)


class DependencyChecker:
    """Verifies that all required jobs have a recent successful run."""

    def __init__(self, config: DependencyConfig, history: Optional[JobHistory] = None) -> None:
        self._config = config
        self._history = history or JobHistory()

    def check(self) -> None:
        """Raise DependencyNotMetError if any required job dependency is unmet."""
        if not self._config.enabled:
            return

        import time

        now = time.time()
        unmet: List[str] = []

        for job_name in self._config.required_jobs:
            records = self._history.get_records(job_name)
            successful = [r for r in records if r.exit_code == 0]
            if not successful:
                unmet.append(job_name)
                continue

            if self._config.max_age_seconds > 0:
                latest = max(successful, key=lambda r: r.end_time or r.start_time)
                ts = latest.end_time or latest.start_time
                if (now - ts) > self._config.max_age_seconds:
                    unmet.append(job_name)

        if unmet:
            raise DependencyNotMetError(
                f"Unmet job dependencies: {', '.join(unmet)}"
            )
