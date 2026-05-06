"""Persistent job run history tracking for cronwrap."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass
class RunRecord:
    job_name: str
    started_at: Optional[str]
    finished_at: Optional[str]
    exit_code: Optional[int]
    succeeded: Optional[bool]
    duration_seconds: Optional[float]
    attempt: int = 1

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RunRecord":
        return cls(**data)


@dataclass
class JobHistory:
    history_dir: str = field(default_factory=lambda: os.environ.get("CRONWRAP_HISTORY_DIR", "/var/log/cronwrap"))
    max_records: int = 100

    def _history_path(self, job_name: str) -> Path:
        safe_name = job_name.replace(" ", "_").replace("/", "_")
        return Path(self.history_dir) / f"{safe_name}.json"

    def _load_records(self, job_name: str) -> List[dict]:
        path = self._history_path(job_name)
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return []

    def record(self, run: RunRecord) -> None:
        """Append a run record to the job's history file."""
        Path(self.history_dir).mkdir(parents=True, exist_ok=True)
        records = self._load_records(run.job_name)
        records.append(run.to_dict())
        if len(records) > self.max_records:
            records = records[-self.max_records :]
        path = self._history_path(run.job_name)
        path.write_text(json.dumps(records, indent=2))

    def get_records(self, job_name: str) -> List[RunRecord]:
        """Return all stored run records for a given job."""
        return [RunRecord.from_dict(d) for d in self._load_records(job_name)]

    def last_run(self, job_name: str) -> Optional[RunRecord]:
        """Return the most recent run record for a job, or None."""
        records = self.get_records(job_name)
        return records[-1] if records else None

    def consecutive_failures(self, job_name: str) -> int:
        """Return the count of consecutive failures from the most recent runs."""
        records = self.get_records(job_name)
        count = 0
        for record in reversed(records):
            if record.succeeded is False:
                count += 1
            else:
                break
        return count
