"""Tests for cronwrap.history module."""

import json
import pytest
from pathlib import Path

from cronwrap.history import JobHistory, RunRecord


@pytest.fixture
def history(tmp_path):
    return JobHistory(history_dir=str(tmp_path), max_records=10)


def _record(job_name="backup", exit_code=0, succeeded=True, attempt=1):
    return RunRecord(
        job_name=job_name,
        started_at="2024-01-01T00:00:00+00:00",
        finished_at="2024-01-01T00:00:05+00:00",
        exit_code=exit_code,
        succeeded=succeeded,
        duration_seconds=5.0,
        attempt=attempt,
    )


def test_record_creates_file(history, tmp_path):
    history.record(_record())
    files = list(tmp_path.iterdir())
    assert len(files) == 1
    assert files[0].name == "backup.json"


def test_record_persists_data(history):
    run = _record(exit_code=1, succeeded=False)
    history.record(run)
    records = history.get_records("backup")
    assert len(records) == 1
    assert records[0].exit_code == 1
    assert records[0].succeeded is False


def test_get_records_returns_empty_for_unknown_job(history):
    assert history.get_records("nonexistent") == []


def test_last_run_returns_none_when_no_history(history):
    assert history.last_run("backup") is None


def test_last_run_returns_most_recent(history):
    history.record(_record(exit_code=0, succeeded=True))
    history.record(_record(exit_code=1, succeeded=False))
    last = history.last_run("backup")
    assert last is not None
    assert last.succeeded is False


def test_max_records_trims_oldest(history):
    for _ in range(15):
        history.record(_record())
    assert len(history.get_records("backup")) == 10


def test_consecutive_failures_all_success(history):
    for _ in range(3):
        history.record(_record(exit_code=0, succeeded=True))
    assert history.consecutive_failures("backup") == 0


def test_consecutive_failures_counts_tail(history):
    history.record(_record(exit_code=0, succeeded=True))
    history.record(_record(exit_code=1, succeeded=False))
    history.record(_record(exit_code=1, succeeded=False))
    assert history.consecutive_failures("backup") == 2


def test_consecutive_failures_resets_after_success(history):
    history.record(_record(exit_code=1, succeeded=False))
    history.record(_record(exit_code=0, succeeded=True))
    history.record(_record(exit_code=1, succeeded=False))
    assert history.consecutive_failures("backup") == 1


def test_job_name_with_spaces_safe_filename(history, tmp_path):
    run = _record(job_name="my backup job")
    history.record(run)
    expected = tmp_path / "my_backup_job.json"
    assert expected.exists()


def test_run_record_round_trip():
    run = _record()
    restored = RunRecord.from_dict(run.to_dict())
    assert restored == run
