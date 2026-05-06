"""Integration-style tests for Dashboard using a real JobHistory on disk."""
from __future__ import annotations

import tempfile
import os
from pathlib import Path

import pytest

from cronwrap.dashboard import Dashboard
from cronwrap.history import JobHistory, RunRecord


@pytest.fixture()
def tmp_history(tmp_path):
    return JobHistory(base_dir=str(tmp_path))


@pytest.fixture()
def dashboard(tmp_history):
    return Dashboard(history=tmp_history)


def _push(history: JobHistory, job: str, exit_code: int, duration: float = 1.0):
    rec = RunRecord(
        job_name=job,
        started_at="2024-01-01T00:00:00",
        finished_at="2024-01-01T00:00:01",
        exit_code=exit_code,
        duration_seconds=duration,
    )
    history.record(rec)


def test_empty_job_summary(dashboard):
    summary = dashboard.summarise("unknown-job")
    assert summary.total_runs == 0
    assert summary.success_rate is None


def test_summary_after_recording_runs(tmp_history, dashboard):
    for _ in range(3):
        _push(tmp_history, "batch", exit_code=0)
    _push(tmp_history, "batch", exit_code=1)
    summary = dashboard.summarise("batch")
    assert summary.total_runs == 4
    assert summary.successful_runs == 3
    assert summary.failed_runs == 1


def test_render_output_contains_job_name(tmp_history, dashboard):
    _push(tmp_history, "render-job", exit_code=0, duration=2.5)
    output = dashboard.render("render-job")
    assert "render-job" in output
    assert "2.5" in output


def test_limit_respected(tmp_history, dashboard):
    for i in range(20):
        _push(tmp_history, "limitjob", exit_code=0)
    summary = dashboard.summarise("limitjob", limit=5)
    assert summary.total_runs <= 5


def test_success_rate_one_hundred_percent(tmp_history, dashboard):
    for _ in range(4):
        _push(tmp_history, "perfect", exit_code=0)
    summary = dashboard.summarise("perfect")
    assert summary.success_rate == pytest.approx(1.0)
