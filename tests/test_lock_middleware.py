"""Tests for cronwrap.lock_middleware."""

from __future__ import annotations

import pytest

from cronwrap.lock import JobLock, LockConfig
from cronwrap.lock_middleware import LockMiddleware


@pytest.fixture()
def cfg(tmp_path):
    return LockConfig(enabled=True, lock_dir=str(tmp_path / "locks"))


@pytest.fixture()
def disabled_cfg(tmp_path):
    return LockConfig(enabled=False, lock_dir=str(tmp_path / "locks"))


# ---------------------------------------------------------------------------
# Disabled locking
# ---------------------------------------------------------------------------

def test_disabled_lock_runs_fn(disabled_cfg):
    called = []
    mw = LockMiddleware("job", disabled_cfg)
    result = mw.run(lambda: (called.append(1), 0)[1])
    assert result == 0
    assert called == [1]


# ---------------------------------------------------------------------------
# Successful lock acquisition
# ---------------------------------------------------------------------------

def test_fn_return_value_propagated(cfg):
    mw = LockMiddleware("job_ok", cfg)
    assert mw.run(lambda: 42) == 42


def test_fn_is_called_exactly_once(cfg):
    calls = []
    mw = LockMiddleware("job_once", cfg)
    mw.run(lambda: (calls.append(1), 0)[1])
    assert len(calls) == 1


def test_lock_released_after_run(cfg):
    from pathlib import Path
    mw = LockMiddleware("job_release", cfg)
    mw.run(lambda: 0)
    lock_path = Path(cfg.lock_dir) / "job_release.lock"
    assert not lock_path.exists()


def test_lock_released_even_on_exception(cfg):
    from pathlib import Path
    mw = LockMiddleware("job_exc", cfg)
    with pytest.raises(RuntimeError):
        mw.run(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    lock_path = Path(cfg.lock_dir) / "job_exc.lock"
    assert not lock_path.exists()


# ---------------------------------------------------------------------------
# Lock already held
# ---------------------------------------------------------------------------

def test_skip_exit_code_returned_when_locked(cfg):
    outer = JobLock("job_busy", cfg)
    outer.acquire()
    try:
        mw = LockMiddleware("job_busy", cfg, skip_exit_code=75)
        result = mw.run(lambda: 0)
        assert result == 75
    finally:
        outer.release()


def test_fn_not_called_when_locked(cfg):
    outer = JobLock("job_skip", cfg)
    outer.acquire()
    called = []
    try:
        mw = LockMiddleware("job_skip", cfg)
        mw.run(lambda: (called.append(1), 0)[1])
        assert called == []
    finally:
        outer.release()
