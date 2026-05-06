"""Cron expression validation and next-run scheduling utilities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

try:
    from croniter import croniter  # type: ignore
except ImportError:  # pragma: no cover
    croniter = None  # type: ignore


@dataclass
class ScheduleInfo:
    """Holds metadata about a job's cron schedule."""

    expression: str
    last_run: Optional[datetime] = None

    def is_valid(self) -> bool:
        """Return True if the cron expression is syntactically valid."""
        if croniter is None:
            raise RuntimeError(
                "croniter is required for schedule validation. "
                "Install it with: pip install croniter"
            )
        return croniter.is_valid(self.expression)

    def next_run(self, base: Optional[datetime] = None) -> datetime:
        """Return the next scheduled run time after *base* (defaults to now)."""
        if croniter is None:
            raise RuntimeError(
                "croniter is required for next_run. "
                "Install it with: pip install croniter"
            )
        if not self.is_valid():
            raise ValueError(f"Invalid cron expression: {self.expression!r}")
        base = base or datetime.now(tz=timezone.utc)
        itr = croniter(self.expression, base)
        return itr.get_next(datetime)

    def is_overdue(self, tolerance_seconds: float = 0.0) -> bool:
        """Return True if the job is overdue relative to *last_run*."""
        if self.last_run is None:
            return False
        now = datetime.now(tz=timezone.utc)
        last = self.last_run
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        expected_next = self.next_run(base=last)
        return (now - expected_next).total_seconds() > tolerance_seconds

    def to_dict(self) -> dict:
        return {
            "expression": self.expression,
            "last_run": self.last_run.isoformat() if self.last_run else None,
        }
