"""Audit trail: records every job execution event to an append-only JSONL file."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class AuditEvent:
    job_name: str
    event: str  # 'start' | 'success' | 'failure' | 'retry' | 'timeout'
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    exit_code: Optional[int] = None
    attempt: int = 1
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "event": self.event,
            "timestamp": self.timestamp.isoformat(),
            "exit_code": self.exit_code,
            "attempt": self.attempt,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuditEvent":
        data = dict(data)
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class AuditLog:
    """Appends :class:`AuditEvent` records to a JSONL file."""

    def __init__(self, log_dir: str | os.PathLike = "/var/log/cronwrap/audit") -> None:
        self._dir = Path(log_dir)

    def _log_path(self, job_name: str) -> Path:
        safe = job_name.replace(os.sep, "_").replace(" ", "_")
        return self._dir / f"{safe}.audit.jsonl"

    def record(self, event: AuditEvent) -> None:
        path = self._log_path(event.job_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event.to_dict()) + "\n")

    def get_events(self, job_name: str) -> list[AuditEvent]:
        path = self._log_path(job_name)
        if not path.exists():
            return []
        events: list[AuditEvent] = []
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    events.append(AuditEvent.from_dict(json.loads(line)))
        return events

    def clear(self, job_name: str) -> None:
        """Remove the audit log for *job_name* (useful in tests)."""
        path = self._log_path(job_name)
        if path.exists():
            path.unlink()
