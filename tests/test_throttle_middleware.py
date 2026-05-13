"""Unit tests for cronwrap.throttle_middleware."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from cronwrap.throttle import ThrottleConfig, ThrottleViolation, ThrottleState, Throttler
from cronwrap.throttle_middleware import ThrottleMiddleware


@pytest.fixture()
def state_dir(tmp_path):
    return str(tmp_path / "throttle")


@pytest.fixture()
def cfg(state_dir):
    return ThrottleConfig(min_interval_seconds=60, state_dir=state_dir)


@pytest.fixture()
def disabled_cfg(state_dir):
    return ThrottleConfig(min_interval_seconds=0, state_dir=state_dir)


def test_disabled_throttle_runs_fn(disabled_cfg):
    mw = ThrottleMiddleware(disabled_cfg, "job")
    assert mw.run(lambda: 99) == 99


def test_fn_return_value_propagated(cfg):
    mw = ThrottleMiddleware(cfg, "job")
    assert mw.run(lambda: "hello") == "hello"


def test_fn_called_exactly_once(cfg):
    calls = []
    mw = ThrottleMiddleware(cfg, "job")
    mw.run(lambda: calls.append(1))
    assert calls == [1]


def test_throttled_returns_none_by_default(cfg):
    import time
    t = Throttler(cfg, "job")
    t._save_state(ThrottleState(last_run=time.time()))
    mw = ThrottleMiddleware(cfg, "job")
    result = mw.run(lambda: 42)
    assert result is None


def test_throttled_calls_skip_fn(cfg):
    import time
    t = Throttler(cfg, "job")
    t._save_state(ThrottleState(last_run=time.time()))
    skip = MagicMock()
    mw = ThrottleMiddleware(cfg, "job", skip_fn=skip)
    mw.run(lambda: None)
    skip.assert_called_once()
    assert isinstance(skip.call_args[0][0], ThrottleViolation)


def test_throttled_raises_when_configured(cfg):
    import time
    t = Throttler(cfg, "job")
    t._save_state(ThrottleState(last_run=time.time()))
    mw = ThrottleMiddleware(cfg, "job", raise_on_throttle=True)
    with pytest.raises(ThrottleViolation):
        mw.run(lambda: None)


def test_fn_not_called_when_throttled(cfg):
    import time
    t = Throttler(cfg, "job")
    t._save_state(ThrottleState(last_run=time.time()))
    calls = []
    mw = ThrottleMiddleware(cfg, "job")
    mw.run(lambda: calls.append(1))
    assert calls == []
