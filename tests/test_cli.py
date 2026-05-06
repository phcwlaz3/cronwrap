"""Tests for cronwrap.cli."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cronwrap.cli import main, _build_parser
from cronwrap.history import RunRecord


def _make_record(exit_code: int = 0) -> RunRecord:
    return RunRecord(
        job_name="testjob",
        started_at="2024-06-01T12:00:00",
        finished_at="2024-06-01T12:00:05",
        exit_code=exit_code,
        duration_seconds=5.0,
    )


def test_no_command_returns_nonzero():
    result = main([])
    assert result == 1


def test_dashboard_command_returns_zero(capsys):
    with patch("cronwrap.cli.JobHistory") as MockHistory, \
         patch("cronwrap.cli.Dashboard") as MockDash:
        mock_dash_instance = MagicMock()
        mock_dash_instance.render.return_value = "Job: testjob\n  Runs: 1"
        MockDash.return_value = mock_dash_instance
        result = main(["dashboard", "testjob"])
    assert result == 0
    captured = capsys.readouterr()
    assert "testjob" in captured.out


def test_dashboard_passes_limit():
    with patch("cronwrap.cli.JobHistory"), \
         patch("cronwrap.cli.Dashboard") as MockDash:
        mock_inst = MagicMock()
        mock_inst.render.return_value = ""
        MockDash.return_value = mock_inst
        main(["dashboard", "myjob", "--limit", "5"])
        mock_inst.render.assert_called_once_with("myjob", limit=5)


def test_history_command_no_records(capsys):
    with patch("cronwrap.cli.JobHistory") as MockHistory:
        MockHistory.return_value.get_records.return_value = []
        result = main(["history", "myjob"])
    assert result == 0
    assert "No history" in capsys.readouterr().out


def test_history_command_with_records(capsys):
    with patch("cronwrap.cli.JobHistory") as MockHistory:
        MockHistory.return_value.get_records.return_value = [
            _make_record(0),
            _make_record(1),
        ]
        result = main(["history", "myjob"])
    assert result == 0
    out = capsys.readouterr().out
    assert "OK" in out
    assert "FAIL" in out


def test_dashboard_with_custom_history_dir():
    with patch("cronwrap.cli.JobHistory") as MockHistory, \
         patch("cronwrap.cli.Dashboard") as MockDash:
        mock_inst = MagicMock()
        mock_inst.render.return_value = ""
        MockDash.return_value = mock_inst
        main(["dashboard", "myjob", "--history-dir", "/tmp/hist"])
        MockHistory.assert_called_once_with(base_dir="/tmp/hist")


def test_parser_has_dashboard_and_history_subcommands():
    parser = _build_parser()
    # Should not raise
    parser.parse_args(["dashboard", "myjob"])
    parser.parse_args(["history", "myjob"])
