"""Unit tests for cronwrap.dependency_middleware."""
from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from cronwrap.dependency import DependencyConfig, DependencyNotMetError
from cronwrap.dependency_middleware import DependencyMiddleware
from cronwrap.history import RunRecord
import time


def _make_record(exit_code: int) -> RunRecord:
    ts = time.time()
    return RunRecord(job_name="dep", start_time=ts, end_time=ts, exit_code=exit_code)


def _mock_history(records: list) -> MagicMock:
    h = MagicMock()
    h.get_records.return_value = records
    return h


def test_disabled_middleware_calls_fn() -> None:
    cfg = DependencyConfig()  # no required_jobs
    mw = DependencyMiddleware(cfg)
    called = []
    mw.run(lambda: called.append(1))
    assert called == [1]


def test_fn_return_value_propagated() -> None:
    cfg = DependencyConfig()
    mw = DependencyMiddleware(cfg)
    result = mw.run(lambda: 42)
    assert result == 42


def test_fn_called_exactly_once_when_deps_met() -> None:
    history = _mock_history([_make_record(0)])
    cfg = DependencyConfig(required_jobs=["dep"])
    mw = DependencyMiddleware(cfg, history)
    fn = MagicMock(return_value=0)
    mw.run(fn)
    fn.assert_called_once()


def test_fn_not_called_when_deps_unmet() -> None:
    history = _mock_history([])
    cfg = DependencyConfig(required_jobs=["dep"])
    mw = DependencyMiddleware(cfg, history)
    fn = MagicMock(return_value=0)
    with pytest.raises(DependencyNotMetError):
        mw.run(fn)
    fn.assert_not_called()


def test_exception_from_fn_propagates() -> None:
    history = _mock_history([_make_record(0)])
    cfg = DependencyConfig(required_jobs=["dep"])
    mw = DependencyMiddleware(cfg, history)

    def boom():
        raise RuntimeError("oops")

    with pytest.raises(RuntimeError, match="oops"):
        mw.run(boom)
