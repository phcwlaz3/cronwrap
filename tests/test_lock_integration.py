"""Integration tests: lock + middleware working end-to-end."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from cronwrap.lock import LockConfig
from cronwrap.lock_middleware import LockMiddleware


@pytest.fixture()
def cfg(tmp_path):
    return LockConfig(enabled=True, lock_dir=str(tmp_path / "locks"), stale_after_seconds=3600)


def test_only_one_thread_runs_job(cfg):
    """When two threads race, exactly one should execute the job body."""
    executions = []
    barrier = threading.Barrier(2)

    def job():
        barrier.wait()  # both threads start simultaneously
        mw = LockMiddleware("concurrent_job", cfg)
        mw.run(lambda: (executions.append(1), 0)[1])

    t1 = threading.Thread(target=job)
    t2 = threading.Thread(target=job)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    # Due to the lock, only one thread should have appended
    assert len(executions) == 1


def test_sequential_runs_both_execute(cfg):
    """Sequential invocations should each execute the job."""
    results = []
    mw = LockMiddleware("seq_job", cfg)
    mw.run(lambda: (results.append("first"), 0)[1])
    mw.run(lambda: (results.append("second"), 0)[1])
    assert results == ["first", "second"]


def test_lock_dir_created_automatically(tmp_path, cfg):
    lock_dir = Path(cfg.lock_dir)
    assert not lock_dir.exists()
    mw = LockMiddleware("dir_job", cfg)
    mw.run(lambda: 0)
    assert lock_dir.exists()


def test_exit_code_preserved_through_middleware(cfg):
    mw = LockMiddleware("exit_job", cfg)
    assert mw.run(lambda: 7) == 7
