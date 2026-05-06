"""Tests for cronwrap.lock."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from cronwrap.lock import JobLock, LockAcquisitionError, LockConfig


# ---------------------------------------------------------------------------
# LockConfig tests
# ---------------------------------------------------------------------------

def test_lock_config_default_disabled():
    cfg = LockConfig()
    assert cfg.enabled is False


def test_lock_config_negative_stale_raises():
    with pytest.raises(ValueError):
        LockConfig(stale_after_seconds=-1)


def test_lock_config_zero_stale_is_valid():
    cfg = LockConfig(stale_after_seconds=0)
    assert cfg.stale_after_seconds == 0


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def cfg(tmp_path):
    return LockConfig(enabled=True, lock_dir=str(tmp_path / "locks"))


@pytest.fixture()
def lock(cfg):
    return JobLock("test_job", cfg)


# ---------------------------------------------------------------------------
# Acquisition / release
# ---------------------------------------------------------------------------

def test_acquire_creates_lock_file(lock, cfg):
    lock.acquire()
    lock_path = Path(cfg.lock_dir) / "test_job.lock"
    assert lock_path.exists()
    lock.release()


def test_acquire_writes_pid(lock, cfg):
    lock.acquire()
    pid = int((Path(cfg.lock_dir) / "test_job.lock").read_text())
    assert pid == os.getpid()
    lock.release()


def test_release_removes_lock_file(lock, cfg):
    lock.acquire()
    lock.release()
    assert not (Path(cfg.lock_dir) / "test_job.lock").exists()


def test_double_acquire_raises(cfg):
    l1 = JobLock("dup_job", cfg)
    l2 = JobLock("dup_job", cfg)
    l1.acquire()
    try:
        with pytest.raises(LockAcquisitionError):
            l2.acquire()
    finally:
        l1.release()


def test_is_held_reflects_state(lock):
    assert not lock.is_held
    lock.acquire()
    assert lock.is_held
    lock.release()
    assert not lock.is_held


# ---------------------------------------------------------------------------
# Stale lock
# ---------------------------------------------------------------------------

def test_stale_lock_is_overwritten(cfg):
    stale_cfg = LockConfig(enabled=True, lock_dir=cfg.lock_dir, stale_after_seconds=0)
    l1 = JobLock("stale_job", stale_cfg)
    l1.acquire()
    # Make the file appear old
    lock_path = Path(cfg.lock_dir) / "stale_job.lock"
    old_time = time.time() - 1
    os.utime(lock_path, (old_time, old_time))

    l2 = JobLock("stale_job", stale_cfg)
    l2.acquire()  # should not raise
    assert l2.is_held
    l2.release()


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

def test_context_manager_releases_on_exit(lock, cfg):
    with lock:
        assert lock.is_held
    assert not lock.is_held
    assert not (Path(cfg.lock_dir) / "test_job.lock").exists()
