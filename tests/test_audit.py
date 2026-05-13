"""Tests for cronwrap.audit."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronwrap.audit import AuditEvent, AuditLog


@pytest.fixture()
def audit(tmp_path: Path) -> AuditLog:
    return AuditLog(log_dir=tmp_path)


@pytest.fixture()
def event() -> AuditEvent:
    return AuditEvent(
        job_name="nightly-backup",
        event="success",
        exit_code=0,
        attempt=1,
        detail="finished in 3s",
    )


# ---------------------------------------------------------------------------
# AuditEvent
# ---------------------------------------------------------------------------

def test_to_dict_contains_required_keys(event: AuditEvent) -> None:
    d = event.to_dict()
    for key in ("job_name", "event", "timestamp", "exit_code", "attempt", "detail"):
        assert key in d


def test_from_dict_round_trips(event: AuditEvent) -> None:
    restored = AuditEvent.from_dict(event.to_dict())
    assert restored.job_name == event.job_name
    assert restored.event == event.event
    assert restored.exit_code == event.exit_code
    assert restored.detail == event.detail


def test_timestamp_defaults_to_utc_now() -> None:
    ev = AuditEvent(job_name="j", event="start")
    assert ev.timestamp.tzinfo is not None


# ---------------------------------------------------------------------------
# AuditLog.record
# ---------------------------------------------------------------------------

def test_record_creates_file(audit: AuditLog, event: AuditEvent, tmp_path: Path) -> None:
    audit.record(event)
    log_file = tmp_path / "nightly-backup.audit.jsonl"
    assert log_file.exists()


def test_record_appends_valid_json(audit: AuditLog, event: AuditEvent, tmp_path: Path) -> None:
    audit.record(event)
    audit.record(event)
    lines = (tmp_path / "nightly-backup.audit.jsonl").read_text().splitlines()
    assert len(lines) == 2
    for line in lines:
        parsed = json.loads(line)
        assert parsed["job_name"] == "nightly-backup"


def test_record_different_events_stored_in_order(audit: AuditLog, tmp_path: Path) -> None:
    for ev in ("start", "retry", "success"):
        audit.record(AuditEvent(job_name="myjob", event=ev))
    events = audit.get_events("myjob")
    assert [e.event for e in events] == ["start", "retry", "success"]


# ---------------------------------------------------------------------------
# AuditLog.get_events
# ---------------------------------------------------------------------------

def test_get_events_returns_empty_for_unknown_job(audit: AuditLog) -> None:
    assert audit.get_events("does-not-exist") == []


def test_get_events_deserialises_correctly(audit: AuditLog, event: AuditEvent) -> None:
    audit.record(event)
    events = audit.get_events("nightly-backup")
    assert len(events) == 1
    assert events[0].exit_code == 0
    assert events[0].detail == "finished in 3s"


# ---------------------------------------------------------------------------
# AuditLog.clear
# ---------------------------------------------------------------------------

def test_clear_removes_log_file(audit: AuditLog, event: AuditEvent, tmp_path: Path) -> None:
    audit.record(event)
    audit.clear("nightly-backup")
    assert not (tmp_path / "nightly-backup.audit.jsonl").exists()


def test_clear_nonexistent_job_does_not_raise(audit: AuditLog) -> None:
    audit.clear("ghost-job")  # must not raise
