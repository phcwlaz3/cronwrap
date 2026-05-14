"""Unit tests for cronwrap.dependency."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from cronwrap.dependency import (
    DependencyChecker,
    DependencyConfig,
    DependencyNotMetError,
)
from cronwrap.history import RunRecord


# ---------------------------------------------------------------------------
# DependencyConfig
# ---------------------------------------------------------------------------

def test_config_defaults_are_empty() -> None:
    cfg = DependencyConfig()
    assert cfg.required_jobs == []
    assert cfg.max_age_seconds == 0
    assert cfg.enabled is False


def test_config_enabled_when_jobs_listed() -> None:
    cfg = DependencyConfig(required_jobs=["job_a"])
    assert cfg.enabled is True


def test_config_negative_max_age_raises() -> None:
    with pytest.raises(ValueError):
        DependencyConfig(max_age_seconds=-1)


def test_config_zero_max_age_is_valid() -> None:
    cfg = DependencyConfig(max_age_seconds=0)
    assert cfg.max_age_seconds == 0


# ---------------------------------------------------------------------------
# DependencyChecker helpers
# ---------------------------------------------------------------------------

def _make_record(exit_code: int, age_seconds: float = 0) -> RunRecord:
    ts = time.time() - age_seconds
    return RunRecord(job_name="dep_job", start_time=ts, end_time=ts, exit_code=exit_code)


def _mock_history(records: list) -> MagicMock:
    h = MagicMock()
    h.get_records.return_value = records
    return h


# ---------------------------------------------------------------------------
# DependencyChecker.check
# ---------------------------------------------------------------------------

def test_disabled_config_does_not_check() -> None:
    history = _mock_history([])
    checker = DependencyChecker(DependencyConfig(), history)
    checker.check()  # should not raise
    history.get_records.assert_not_called()


def test_check_passes_when_job_succeeded() -> None:
    history = _mock_history([_make_record(0)])
    cfg = DependencyConfig(required_jobs=["dep_job"])
    checker = DependencyChecker(cfg, history)
    checker.check()  # should not raise


def test_check_fails_when_no_records() -> None:
    history = _mock_history([])
    cfg = DependencyConfig(required_jobs=["dep_job"])
    checker = DependencyChecker(cfg, history)
    with pytest.raises(DependencyNotMetError, match="dep_job"):
        checker.check()


def test_check_fails_when_only_failures() -> None:
    history = _mock_history([_make_record(1), _make_record(2)])
    cfg = DependencyConfig(required_jobs=["dep_job"])
    checker = DependencyChecker(cfg, history)
    with pytest.raises(DependencyNotMetError):
        checker.check()


def test_check_passes_within_max_age() -> None:
    history = _mock_history([_make_record(0, age_seconds=30)])
    cfg = DependencyConfig(required_jobs=["dep_job"], max_age_seconds=60)
    checker = DependencyChecker(cfg, history)
    checker.check()  # should not raise


def test_check_fails_outside_max_age() -> None:
    history = _mock_history([_make_record(0, age_seconds=120)])
    cfg = DependencyConfig(required_jobs=["dep_job"], max_age_seconds=60)
    checker = DependencyChecker(cfg, history)
    with pytest.raises(DependencyNotMetError):
        checker.check()


def test_multiple_jobs_all_must_pass() -> None:
    def side_effect(job_name):
        if job_name == "job_a":
            return [_make_record(0)]
        return []

    history = MagicMock()
    history.get_records.side_effect = side_effect
    cfg = DependencyConfig(required_jobs=["job_a", "job_b"])
    checker = DependencyChecker(cfg, history)
    with pytest.raises(DependencyNotMetError, match="job_b"):
        checker.check()
