"""Tests for cronwrap.ratelimit."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwrap.ratelimit import RateLimitConfig, RateLimiter


# ---------------------------------------------------------------------------
# RateLimitConfig
# ---------------------------------------------------------------------------

def test_rate_limit_config_default_disabled():
    cfg = RateLimitConfig()
    assert cfg.min_interval_seconds == 0
    assert cfg.enabled is False


def test_rate_limit_config_enabled_when_positive():
    cfg = RateLimitConfig(min_interval_seconds=60)
    assert cfg.enabled is True


def test_rate_limit_config_negative_raises():
    with pytest.raises(ValueError, match="min_interval_seconds"):
        RateLimitConfig(min_interval_seconds=-1)


def test_rate_limit_config_zero_is_valid():
    cfg = RateLimitConfig(min_interval_seconds=0)
    assert cfg.enabled is False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def state_dir(tmp_path: Path) -> Path:
    return tmp_path / "ratelimit"


@pytest.fixture()
def limiter(state_dir: Path) -> RateLimiter:
    return RateLimiter(
        config=RateLimitConfig(min_interval_seconds=60),
        state_dir=state_dir,
    )


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------

def test_allowed_when_no_state_exists(limiter: RateLimiter):
    assert limiter.is_allowed("my-job") is True


def test_allowed_when_disabled(state_dir: Path):
    rl = RateLimiter(config=RateLimitConfig(min_interval_seconds=0), state_dir=state_dir)
    rl.record_run("my-job")
    assert rl.is_allowed("my-job") is True


def test_not_allowed_immediately_after_run(limiter: RateLimiter):
    limiter.record_run("my-job")
    assert limiter.is_allowed("my-job") is False


def test_allowed_after_interval_passes(limiter: RateLimiter, state_dir: Path):
    # Write a timestamp far in the past
    path = state_dir / "my-job.json"
    state_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"last_run": time.time() - 120}))
    assert limiter.is_allowed("my-job") is True


def test_record_run_creates_state_file(limiter: RateLimiter, state_dir: Path):
    limiter.record_run("my-job")
    assert (state_dir / "my-job.json").exists()


def test_seconds_until_allowed_is_zero_when_no_state(limiter: RateLimiter):
    assert limiter.seconds_until_allowed("my-job") == 0.0


def test_seconds_until_allowed_positive_after_run(limiter: RateLimiter):
    limiter.record_run("my-job")
    remaining = limiter.seconds_until_allowed("my-job")
    assert 0 < remaining <= 60


def test_seconds_until_allowed_zero_when_disabled(state_dir: Path):
    rl = RateLimiter(config=RateLimitConfig(min_interval_seconds=0), state_dir=state_dir)
    rl.record_run("my-job")
    assert rl.seconds_until_allowed("my-job") == 0.0


def test_corrupt_state_file_treated_as_no_state(limiter: RateLimiter, state_dir: Path):
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "my-job.json").write_text("not-json")
    assert limiter.is_allowed("my-job") is True
