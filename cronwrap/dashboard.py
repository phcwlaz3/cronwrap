"""Simple text-based dashboard for summarising recent cron job runs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from cronwrap.history import JobHistory, RunRecord


@dataclass
class JobSummary:
    job_name: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    last_exit_code: Optional[int]
    last_duration_seconds: Optional[float]

    @property
    def success_rate(self) -> Optional[float]:
        if self.total_runs == 0:
            return None
        return self.successful_runs / self.total_runs

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "last_exit_code": self.last_exit_code,
            "last_duration_seconds": self.last_duration_seconds,
            "success_rate": self.success_rate,
        }


class Dashboard:
    """Aggregates run history into per-job summaries."""

    def __init__(self, history: Optional[JobHistory] = None) -> None:
        self._history = history or JobHistory()

    def summarise(self, job_name: str, limit: int = 50) -> JobSummary:
        records: List[RunRecord] = self._history.get_records(job_name, limit=limit)
        total = len(records)
        successful = sum(1 for r in records if r.exit_code == 0)
        failed = total - successful
        last = records[-1] if records else None
        return JobSummary(
            job_name=job_name,
            total_runs=total,
            successful_runs=successful,
            failed_runs=failed,
            last_exit_code=last.exit_code if last else None,
            last_duration_seconds=last.duration_seconds if last else None,
        )

    def render(self, job_name: str, limit: int = 50) -> str:
        summary = self.summarise(job_name, limit=limit)
        rate = summary.success_rate
        rate_str = f"{rate * 100:.1f}%" if rate is not None else "N/A"
        lines = [
            f"Job: {summary.job_name}",
            f"  Runs (last {limit}): {summary.total_runs}",
            f"  Successful:          {summary.successful_runs}",
            f"  Failed:              {summary.failed_runs}",
            f"  Success rate:        {rate_str}",
            f"  Last exit code:      {summary.last_exit_code}",
            f"  Last duration (s):   {summary.last_duration_seconds}",
        ]
        return "\n".join(lines)
