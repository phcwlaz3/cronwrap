"""Tests for cronwrap.timeout."""
from __future__ import annotations

import time
import pytest

from cronwrap.timeout import TimeoutConfig, TimeoutExpired, TimeoutHandler


# ---------------------------------------------------------------------------
# TimeoutConfig
# ---------------------------------------------------------------------------

def test_timeout_config_default_disabled():
    cfg = TimeoutConfig()
    assert cfg.enabled is False


def test_timeout_config_enabled_when_positive():
    cfg = TimeoutConfig(seconds=5)
    assert cfg.enabled is True


def test_timeout_config_negative_raises():
    with pytest.raises(ValueError, match=">= 0"):
        TimeoutConfig(seconds=-1)


def test_timeout_config_zero_is_valid():
    cfg = TimeoutConfig(seconds=0)
    assert cfg.seconds == 0


# ---------------------------------------------------------------------------
# TimeoutHandler — no timeout
# ---------------------------------------------------------------------------

def test_no_timeout_runs_function():
    handler = TimeoutHandler(TimeoutConfig(seconds=0))
    called = []
    result = handler.run(lambda: (called.append(1), 0)[1])
    assert result == 0
    assert called == [1]


def test_no_timeout_returns_exit_code():
    handler = TimeoutHandler(TimeoutConfig(seconds=0))
    assert handler.run(lambda: 42) == 42


# ---------------------------------------------------------------------------
# TimeoutHandler — with timeout (thread-based)
# ---------------------------------------------------------------------------

def test_fast_function_completes_before_timeout():
    handler = TimeoutHandler(TimeoutConfig(seconds=5))
    assert handler.run(lambda: 0) == 0


def test_slow_function_raises_timeout_expired():
    handler = TimeoutHandler(TimeoutConfig(seconds=1))

    def _slow() -> int:
        time.sleep(10)
        return 0

    with pytest.raises(TimeoutExpired) as exc_info:
        handler.run(_slow)

    assert exc_info.value.timeout_seconds == 1


def test_timeout_expired_message():
    err = TimeoutExpired(30)
    assert "30" in str(err)


def test_exception_inside_func_propagates():
    handler = TimeoutHandler(TimeoutConfig(seconds=5))

    def _boom() -> int:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        handler.run(_boom)


def test_exit_code_propagated_through_thread():
    handler = TimeoutHandler(TimeoutConfig(seconds=5))
    assert handler.run(lambda: 7) == 7


# ---------------------------------------------------------------------------
# TimeoutHandler — SIGALRM variant
# ---------------------------------------------------------------------------

def test_sigalrm_fast_function_completes():
    handler = TimeoutHandler(TimeoutConfig(seconds=5))
    assert handler.run_with_sigalrm(lambda: 0) == 0


def test_sigalrm_no_timeout_calls_func():
    handler = TimeoutHandler(TimeoutConfig(seconds=0))
    assert handler.run_with_sigalrm(lambda: 3) == 3
