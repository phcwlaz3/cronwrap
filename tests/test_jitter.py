"""Tests for cronwrap.jitter."""

from __future__ import annotations

import pytest

from cronwrap.jitter import JitterConfig, JitterMiddleware


# ---------------------------------------------------------------------------
# JitterConfig
# ---------------------------------------------------------------------------


def test_config_default_disabled():
    cfg = JitterConfig()
    assert cfg.max_seconds == 0.0
    assert not cfg.enabled


def test_config_enabled_when_positive():
    cfg = JitterConfig(max_seconds=5.0)
    assert cfg.enabled


def test_config_negative_raises():
    with pytest.raises(ValueError, match="max_seconds must be >= 0"):
        JitterConfig(max_seconds=-1.0)


def test_config_zero_is_valid():
    cfg = JitterConfig(max_seconds=0.0)
    assert cfg.max_seconds == 0.0


# ---------------------------------------------------------------------------
# JitterMiddleware — disabled path
# ---------------------------------------------------------------------------


def test_disabled_jitter_does_not_sleep():
    slept: list[float] = []
    cfg = JitterConfig(max_seconds=0.0)
    mw = JitterMiddleware(cfg, sleep_fn=slept.append)

    mw.run(lambda: 0)

    assert slept == [], "sleep should not be called when jitter is disabled"


def test_disabled_jitter_propagates_return_value():
    cfg = JitterConfig(max_seconds=0.0)
    mw = JitterMiddleware(cfg, sleep_fn=lambda _: None)

    result = mw.run(lambda: 42)

    assert result == 42


# ---------------------------------------------------------------------------
# JitterMiddleware — enabled path
# ---------------------------------------------------------------------------


def test_enabled_jitter_sleeps_once():
    slept: list[float] = []
    cfg = JitterConfig(max_seconds=10.0, seed=0)
    mw = JitterMiddleware(cfg, sleep_fn=slept.append)

    mw.run(lambda: 0)

    assert len(slept) == 1


def test_enabled_jitter_delay_within_bounds():
    slept: list[float] = []
    max_s = 7.5
    cfg = JitterConfig(max_seconds=max_s, seed=42)
    mw = JitterMiddleware(cfg, sleep_fn=slept.append)

    for _ in range(20):
        mw.run(lambda: 0)

    assert all(0.0 <= d <= max_s for d in slept)


def test_enabled_jitter_propagates_return_value():
    cfg = JitterConfig(max_seconds=1.0, seed=1)
    mw = JitterMiddleware(cfg, sleep_fn=lambda _: None)

    result = mw.run(lambda: 7)

    assert result == 7


def test_fn_called_exactly_once():
    calls: list[int] = []
    cfg = JitterConfig(max_seconds=1.0, seed=0)
    mw = JitterMiddleware(cfg, sleep_fn=lambda _: None)

    def fn() -> int:
        calls.append(1)
        return 0

    mw.run(fn)
    assert len(calls) == 1


def test_seed_produces_deterministic_delay():
    delays_a: list[float] = []
    delays_b: list[float] = []
    cfg = JitterConfig(max_seconds=5.0, seed=99)

    JitterMiddleware(cfg, sleep_fn=delays_a.append).run(lambda: 0)
    JitterMiddleware(cfg, sleep_fn=delays_b.append).run(lambda: 0)

    assert delays_a == delays_b


def test_config_exposed_via_property():
    cfg = JitterConfig(max_seconds=3.0)
    mw = JitterMiddleware(cfg, sleep_fn=lambda _: None)
    assert mw.config is cfg
