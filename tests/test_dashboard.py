"""Tests for cronwrap.dashboard."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cronwrap.dashboard import Dashboard, JobSummary
from cronwrap.history import RunRecord


def _record(exit_code: int, duration: float = 1.0) -> RunRecord:
    return RunRecord(
        job_name="myjob",
        started_at="2024-01-01T00:00:00",
        finished_at="2024-01-01T00:00:01",
        exit_code=exit_code,
        duration_seconds=duration,
    )


@pytest.fixture()
def mock_history():
    return MagicMock()


@pytest.fixture()
def dashboard(mock_history):
    return Dashboard(history=mock_history)


def test_summarise_empty_history(dashboard, mock_history):
    mock_history.get_records.return_value = []
    summary = dashboard.summarise("myjob")
    assert summary.total_runs == 0
    assert summary.successful_runs == 0
    assert summary.failed_runs == 0
    assert summary.last_exit_code is None
    assert summary.success_rate is None


def test_summarise_all_successful(dashboard, mock_history):
    mock_history.get_records.return_value = [_record(0), _record(0), _record(0)]
    summary = dashboard.summarise("myjob")
    assert summary.total_runs == 3
    assert summary.successful_runs == 3
    assert summary.failed_runs == 0
    assert summary.success_rate == pytest.approx(1.0)


def test_summarise_mixed_results(dashboard, mock_history):
    mock_history.get_records.return_value = [_record(0), _record(1), _record(0)]
    summary = dashboard.summarise("myjob")
    assert summary.successful_runs == 2
    assert summary.failed_runs == 1
    assert summary.success_rate == pytest.approx(2 / 3)


def test_summarise_last_record_used(dashboard, mock_history):
    records = [_record(0, 2.5), _record(1, 9.9)]
    mock_history.get_records.return_value = records
    summary = dashboard.summarise("myjob")
    assert summary.last_exit_code == 1
    assert summary.last_duration_seconds == pytest.approx(9.9)


def test_to_dict_contains_expected_keys(dashboard, mock_history):
    mock_history.get_records.return_value = [_record(0)]
    d = dashboard.summarise("myjob").to_dict()
    assert set(d.keys()) == {
        "job_name", "total_runs", "successful_runs",
        "failed_runs", "last_exit_code", "last_duration_seconds", "success_rate",
    }


def test_render_returns_string(dashboard, mock_history):
    mock_history.get_records.return_value = [_record(0, 3.14)]
    output = dashboard.render("myjob")
    assert "myjob" in output
    assert "100.0%" in output
    assert "3.14" in output


def test_render_shows_na_for_empty(dashboard, mock_history):
    mock_history.get_records.return_value = []
    output = dashboard.render("myjob")
    assert "N/A" in output


def test_default_history_created_when_none_passed():
    d = Dashboard()
    assert d._history is not None
