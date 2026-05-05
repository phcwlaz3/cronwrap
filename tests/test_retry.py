"""Tests for cronwrap.retry module."""

import pytest
from unittest.mock import MagicMock, patch

from cronwrap.retry import RetryConfig, RetryHandler


# ---------------------------------------------------------------------------
# RetryConfig tests
# ---------------------------------------------------------------------------

def test_retry_config_defaults():
    cfg = RetryConfig()
    assert cfg.max_attempts == 3
    assert cfg.delay_seconds == 5.0
    assert cfg.backoff_factor == 2.0


def test_retry_config_invalid_max_attempts():
    with pytest.raises(ValueError, match="max_attempts"):
        RetryConfig(max_attempts=0)


def test_retry_config_invalid_delay():
    with pytest.raises(ValueError, match="delay_seconds"):
        RetryConfig(delay_seconds=-1)


def test_retry_config_invalid_backoff():
    with pytest.raises(ValueError, match="backoff_factor"):
        RetryConfig(backoff_factor=0.5)


# ---------------------------------------------------------------------------
# RetryHandler tests
# ---------------------------------------------------------------------------

@pytest.fixture
def fast_config():
    """RetryConfig with no sleep delay for fast tests."""
    return RetryConfig(max_attempts=3, delay_seconds=0, backoff_factor=1.0)


def test_run_succeeds_on_first_attempt(fast_config):
    handler = RetryHandler(fast_config)
    func = MagicMock(return_value=42)
    assert handler.run(func) == 42
    func.assert_called_once()


def test_run_returns_value_after_retries(fast_config):
    handler = RetryHandler(fast_config)
    func = MagicMock(side_effect=[RuntimeError("fail"), RuntimeError("fail"), 99])
    assert handler.run(func) == 99
    assert func.call_count == 3


def test_run_raises_after_all_attempts_exhausted(fast_config):
    handler = RetryHandler(fast_config)
    func = MagicMock(side_effect=RuntimeError("always fails"))
    with pytest.raises(RuntimeError, match="always fails"):
        handler.run(func)
    assert func.call_count == fast_config.max_attempts


def test_run_does_not_retry_unexpected_exception(fast_config):
    """Only exceptions listed in config.exceptions trigger a retry."""
    cfg = RetryConfig(max_attempts=3, delay_seconds=0, backoff_factor=1.0,
                     exceptions=(ValueError,))
    handler = RetryHandler(cfg)
    func = MagicMock(side_effect=TypeError("wrong type"))
    with pytest.raises(TypeError):
        handler.run(func)
    func.assert_called_once()


def test_run_sleeps_between_attempts(fast_config):
    cfg = RetryConfig(max_attempts=2, delay_seconds=3.0, backoff_factor=1.0)
    handler = RetryHandler(cfg)
    func = MagicMock(side_effect=[RuntimeError("fail"), "ok"])
    with patch("cronwrap.retry.time.sleep") as mock_sleep:
        handler.run(func)
    mock_sleep.assert_called_once_with(3.0)


def test_run_applies_backoff():
    cfg = RetryConfig(max_attempts=3, delay_seconds=2.0, backoff_factor=3.0)
    handler = RetryHandler(cfg)
    func = MagicMock(side_effect=[RuntimeError(), RuntimeError(), "done"])
    with patch("cronwrap.retry.time.sleep") as mock_sleep:
        handler.run(func)
    calls = [c.args[0] for c in mock_sleep.call_args_list]
    assert calls == [2.0, 6.0]
