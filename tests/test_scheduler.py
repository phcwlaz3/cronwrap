"""Tests for cronwrap.scheduler."""
from __future__ import annotations

import importlib
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest

from cronwrap.scheduler import ScheduleInfo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_croniter_unavailable():
    """Context manager that hides croniter from the scheduler module."""
    return patch("cronwrap.scheduler.croniter", None)


# ---------------------------------------------------------------------------
# is_valid
# ---------------------------------------------------------------------------

def test_is_valid_returns_true_for_standard_expression():
    info = ScheduleInfo(expression="0 * * * *")
    assert info.is_valid() is True


def test_is_valid_returns_false_for_bad_expression():
    info = ScheduleInfo(expression="not-a-cron")
    assert info.is_valid() is False


def test_is_valid_raises_when_croniter_missing():
    info = ScheduleInfo(expression="0 * * * *")
    with _make_croniter_unavailable():
        with pytest.raises(RuntimeError, match="croniter is required"):
            info.is_valid()


# ---------------------------------------------------------------------------
# next_run
# ---------------------------------------------------------------------------

def test_next_run_returns_datetime():
    info = ScheduleInfo(expression="0 * * * *")
    base = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    result = info.next_run(base=base)
    assert isinstance(result, datetime)
    assert result > base


def test_next_run_raises_for_invalid_expression():
    info = ScheduleInfo(expression="bad expr")
    with pytest.raises(ValueError, match="Invalid cron expression"):
        info.next_run()


def test_next_run_raises_when_croniter_missing():
    info = ScheduleInfo(expression="0 * * * *")
    with _make_croniter_unavailable():
        with pytest.raises(RuntimeError, match="croniter is required"):
            info.next_run()


# ---------------------------------------------------------------------------
# is_overdue
# ---------------------------------------------------------------------------

def test_is_overdue_returns_false_when_no_last_run():
    info = ScheduleInfo(expression="0 * * * *")
    assert info.is_overdue() is False


def test_is_overdue_returns_true_when_past_due():
    # Last run was 2 hours ago; hourly job → next was 1 h ago → overdue
    two_hours_ago = datetime.now(tz=timezone.utc) - timedelta(hours=2)
    info = ScheduleInfo(expression="0 * * * *", last_run=two_hours_ago)
    assert info.is_overdue() is True


def test_is_overdue_returns_false_when_not_yet_due():
    # Last run was 30 minutes ago; hourly job → next is 30 min from now
    thirty_min_ago = datetime.now(tz=timezone.utc) - timedelta(minutes=30)
    info = ScheduleInfo(expression="0 * * * *", last_run=thirty_min_ago)
    assert info.is_overdue() is False


# ---------------------------------------------------------------------------
# to_dict
# ---------------------------------------------------------------------------

def test_to_dict_with_last_run():
    ts = datetime(2024, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
    info = ScheduleInfo(expression="30 8 * * *", last_run=ts)
    d = info.to_dict()
    assert d["expression"] == "30 8 * * *"
    assert "2024-06-01" in d["last_run"]


def test_to_dict_without_last_run():
    info = ScheduleInfo(expression="*/5 * * * *")
    d = info.to_dict()
    assert d["last_run"] is None
