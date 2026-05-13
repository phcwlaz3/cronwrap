"""Integration tests for throttle behaviour across real filesystem state."""
from __future__ import annotations

import time
import pytest

from cronwrap.throttle import ThrottleConfig, Throttler, ThrottleViolation


@pytest.fixture()
def state_dir(tmp_path):
    return str(tmp_path / "throttle_int")


def _make_throttler(state_dir: str, interval: float, name: str = "intjob") -> Throttler:
    cfg = ThrottleConfig(min_interval_seconds=interval, state_dir=state_dir)
    return Throttler(cfg, name)


def test_first_run_always_allowed(state_dir):
    t = _make_throttler(state_dir, interval=10)
    results = []
    t.run(lambda: results.append("ran"))
    assert results == ["ran"]


def test_second_immediate_run_is_throttled(state_dir):
    t = _make_throttler(state_dir, interval=60)
    t.run(lambda: None)
    with pytest.raises(ThrottleViolation):
        t.run(lambda: None)


def test_run_after_interval_succeeds(state_dir):
    t = _make_throttler(state_dir, interval=0.1)
    t.run(lambda: None)
    time.sleep(0.15)
    results = []
    t.run(lambda: results.append("second"))
    assert results == ["second"]


def test_state_persists_across_throttler_instances(state_dir):
    t1 = _make_throttler(state_dir, interval=60, name="persistent")
    t1.run(lambda: None)
    # New instance, same state file
    t2 = _make_throttler(state_dir, interval=60, name="persistent")
    with pytest.raises(ThrottleViolation):
        t2.run(lambda: None)


def test_different_jobs_have_independent_state(state_dir):
    t_a = _make_throttler(state_dir, interval=60, name="job_a")
    t_b = _make_throttler(state_dir, interval=60, name="job_b")
    t_a.run(lambda: None)
    # job_b has never run — should be fine
    results = []
    t_b.run(lambda: results.append("b"))
    assert results == ["b"]
