"""Integration tests for dependency checking using a real JobHistory."""
from __future__ import annotations

import time

import pytest

from cronwrap.dependency import DependencyConfig, DependencyNotMetError
from cronwrap.dependency_middleware import DependencyMiddleware
from cronwrap.history import JobHistory, RunRecord


@pytest.fixture()
def tmp_history(tmp_path):
    return JobHistory(history_dir=str(tmp_path))


def _record(job_name: str, exit_code: int, age: float = 0) -> RunRecord:
    ts = time.time() - age
    return RunRecord(job_name=job_name, start_time=ts, end_time=ts, exit_code=exit_code)


def test_check_passes_after_successful_run(tmp_history) -> None:
    tmp_history.record(_record("setup", exit_code=0))
    cfg = DependencyConfig(required_jobs=["setup"])
    mw = DependencyMiddleware(cfg, tmp_history)
    results = []
    mw.run(lambda: results.append("ran"))
    assert results == ["ran"]


def test_check_blocked_with_no_history(tmp_history) -> None:
    cfg = DependencyConfig(required_jobs=["setup"])
    mw = DependencyMiddleware(cfg, tmp_history)
    with pytest.raises(DependencyNotMetError):
        mw.run(lambda: None)


def test_check_blocked_after_failed_run(tmp_history) -> None:
    tmp_history.record(_record("setup", exit_code=1))
    cfg = DependencyConfig(required_jobs=["setup"])
    mw = DependencyMiddleware(cfg, tmp_history)
    with pytest.raises(DependencyNotMetError):
        mw.run(lambda: None)


def test_max_age_respected(tmp_history) -> None:
    tmp_history.record(_record("setup", exit_code=0, age=200))
    cfg = DependencyConfig(required_jobs=["setup"], max_age_seconds=60)
    mw = DependencyMiddleware(cfg, tmp_history)
    with pytest.raises(DependencyNotMetError):
        mw.run(lambda: None)


def test_fresh_run_satisfies_max_age(tmp_history) -> None:
    tmp_history.record(_record("setup", exit_code=0, age=10))
    cfg = DependencyConfig(required_jobs=["setup"], max_age_seconds=60)
    mw = DependencyMiddleware(cfg, tmp_history)
    ran = []
    mw.run(lambda: ran.append(True))
    assert ran
