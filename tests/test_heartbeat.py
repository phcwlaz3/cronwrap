"""Tests for cronwrap.heartbeat."""
from unittest.mock import MagicMock, patch

import pytest

from cronwrap.heartbeat import HeartbeatConfig, HeartbeatSender


# ---------------------------------------------------------------------------
# HeartbeatConfig
# ---------------------------------------------------------------------------

def test_config_defaults_disabled():
    cfg = HeartbeatConfig()
    assert cfg.enabled is False


def test_config_enabled_with_url():
    cfg = HeartbeatConfig(url="https://hc-ping.example.com/abc")
    assert cfg.enabled is True


def test_config_invalid_timeout_raises():
    with pytest.raises(ValueError, match="timeout_seconds"):
        HeartbeatConfig(url="https://example.com", timeout_seconds=0)


def test_config_negative_timeout_raises():
    with pytest.raises(ValueError):
        HeartbeatConfig(url="https://example.com", timeout_seconds=-5)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def cfg():
    return HeartbeatConfig(
        url="https://hc-ping.example.com/token",
        ping_on_start=True,
        ping_on_success=True,
        ping_on_failure=True,
    )


@pytest.fixture()
def sender(cfg):
    return HeartbeatSender(cfg)


def _mock_response(status: int):
    resp = MagicMock()
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ---------------------------------------------------------------------------
# HeartbeatSender
# ---------------------------------------------------------------------------

def test_ping_success_returns_true_on_2xx(sender):
    with patch("urllib.request.urlopen", return_value=_mock_response(200)):
        assert sender.ping_success() is True


def test_ping_success_returns_false_on_network_error(sender):
    import urllib.error
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
        assert sender.ping_success() is False


def test_ping_start_uses_start_suffix(sender):
    with patch("urllib.request.urlopen", return_value=_mock_response(200)) as mock_open:
        sender.ping_start()
        called_url = mock_open.call_args[0][0]
        assert called_url.endswith("/start")


def test_ping_failure_uses_fail_suffix(sender):
    with patch("urllib.request.urlopen", return_value=_mock_response(200)) as mock_open:
        sender.ping_failure()
        called_url = mock_open.call_args[0][0]
        assert called_url.endswith("/fail")


def test_disabled_sender_returns_none():
    s = HeartbeatSender(HeartbeatConfig())
    assert s.ping_start() is None
    assert s.ping_success() is None
    assert s.ping_failure() is None


def test_ping_start_skipped_when_flag_false():
    cfg = HeartbeatConfig(url="https://example.com", ping_on_start=False)
    s = HeartbeatSender(cfg)
    assert s.ping_start() is None
