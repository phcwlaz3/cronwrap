"""Unit tests for cronwrap.throttle."""
from __future__ import annotations

import json
import time
import pytest
from pathlib import Path
from unittest.mock import patch

from cronwrap.throttle import ThrottleConfig, Throttler, ThrottleViolation, ThrottleState


# ---------------------------------------------------------------------------
# ThrottleConfig
# ---------------------------------------------------------------------------

def test_throttle_config_default_disabled():
    cfg = ThrottleConfig()
    assert cfg.enabled is False


def test_throttle_config_enabled_when_positive():
    cfg = ThrottleConfig(min_interval_seconds=30)
    assert cfg.enabled is True


def test_throttle_config_negative_raises():
    with pytest.raises(ValueError):
        ThrottleConfig(min_interval_seconds=-1)


def test_throttle_config_zero_is_valid():
    cfg = ThrottleConfig(min_interval_seconds=0)
    assert cfg.enabled is False


# ---------------------------------------------------------------------------
# ThrottleState
# ---------------------------------------------------------------------------

def test_throttle_state_round_trips():
    ts = ThrottleState(last_run=12345.0)
    assert ThrottleState.from_dict(ts.to_dict()).last_run == 12345.0


def test_throttle_state_missing_key():
    ts = ThrottleState.from_dict({})
    assert ts.last_run is None


# ---------------------------------------------------------------------------
# Throttler
# ---------------------------------------------------------------------------

@pytest.fixture()
def state_dir(tmp_path):
    return str(tmp_path / "throttle")


@pytest.fixture()
def cfg(state_dir):
    return ThrottleConfig(min_interval_seconds=60, state_dir=state_dir)


@pytest.fixture()
def throttler(cfg):
    return Throttler(cfg, "test_job")


def test_check_passes_when_no_previous_run(throttler):
    throttler.check()  # should not raise


def test_check_passes_after_interval_elapsed(throttler):
    old_time = time.time() - 120
    throttler._save_state(ThrottleState(last_run=old_time))
    throttler.check()  # 120s > 60s — should not raise


def test_check_raises_within_interval(throttler):
    throttler._save_state(ThrottleState(last_run=time.time()))
    with pytest.raises(ThrottleViolation, match="throttled"):
        throttler.check()


def test_record_writes_state_file(throttler, state_dir):
    throttler.record()
    path = Path(state_dir) / "test_job.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert "last_run" in data
    assert data["last_run"] == pytest.approx(time.time(), abs=2)


def test_disabled_throttler_never_raises(state_dir):
    cfg = ThrottleConfig(min_interval_seconds=0, state_dir=state_dir)
    t = Throttler(cfg, "job")
    t._save_state(ThrottleState(last_run=time.time()))
    t.check()  # should not raise even though just ran


def test_run_calls_fn_and_records(throttler):
    called = []
    result = throttler.run(lambda: called.append(1) or 42)
    assert result == 42
    assert called == [1]
    state = throttler._load_state()
    assert state.last_run is not None


def test_corrupted_state_file_treated_as_empty(throttler, state_dir):
    Path(state_dir).mkdir(parents=True, exist_ok=True)
    (Path(state_dir) / "test_job.json").write_text("not-json")
    throttler.check()  # should not raise
