"""Metrics collection for cron job execution tracking."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List


@dataclass
class JobMetrics:
    """Holds execution metrics for a single cron job run."""

    job_name: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    exit_code: Optional[int] = None
    attempt: int = 1
    retries: int = 0
    tags: dict = field(default_factory=dict)

    @property
    def duration(self) -> Optional[timedelta]:
        """Return elapsed time if both start and end times are set."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def duration_seconds(self) -> Optional[float]:
        """Return duration in seconds, or None if not available."""
        d = self.duration
        return d.total_seconds() if d is not None else None

    @property
    def succeeded(self) -> Optional[bool]:
        """Return True if exit_code is 0, False if non-zero, None if unknown."""
        if self.exit_code is None:
            return None
        return self.exit_code == 0

    def to_dict(self) -> dict:
        """Serialize metrics to a plain dictionary."""
        return {
            "job_name": self.job_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "exit_code": self.exit_code,
            "succeeded": self.succeeded,
            "attempt": self.attempt,
            "retries": self.retries,
            "tags": self.tags,
        }


class MetricsCollector:
    """Accumulates metrics across multiple job runs."""

    def __init__(self) -> None:
        self._records: List[JobMetrics] = []

    def record(self, metrics: JobMetrics) -> None:
        """Store a completed JobMetrics instance."""
        self._records.append(metrics)

    def all(self) -> List[JobMetrics]:
        """Return all recorded metrics."""
        return list(self._records)

    def for_job(self, job_name: str) -> List[JobMetrics]:
        """Return metrics filtered by job name."""
        return [m for m in self._records if m.job_name == job_name]

    def success_rate(self, job_name: str) -> Optional[float]:
        """Return fraction of successful runs for a given job, or None if no data."""
        records = [m for m in self.for_job(job_name) if m.exit_code is not None]
        if not records:
            return None
        successes = sum(1 for m in records if m.succeeded)
        return successes / len(records)

    def clear(self) -> None:
        """Remove all stored records."""
        self._records.clear()
