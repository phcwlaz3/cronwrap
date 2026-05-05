"""Tests for the cronwrap alerting module."""

import smtplib
from unittest.mock import MagicMock, patch

import pytest

from cronwrap.alerting import AlertConfig, Alerter


@pytest.fixture
def config():
    return AlertConfig(
        recipients=["ops@example.com"],
        sender="cronwrap@example.com",
        smtp_host="localhost",
        smtp_port=25,
    )


@pytest.fixture
def alerter(config):
    return Alerter(config)


def test_alert_failure_sends_email(alerter):
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        alerter.alert_failure("my-job", exit_code=1, stderr="something went wrong")

        mock_server.sendmail.assert_called_once()
        args = mock_server.sendmail.call_args[0]
        assert "ops@example.com" in args[1]
        assert "FAILED" in args[2]
        assert "my-job" in args[2]


def test_alert_failure_no_recipients_does_not_send():
    cfg = AlertConfig(recipients=[])
    alerter = Alerter(cfg)
    with patch("smtplib.SMTP") as mock_smtp_cls:
        alerter.alert_failure("job", exit_code=2)
        mock_smtp_cls.assert_not_called()


def test_alert_duration_sends_email(alerter):
    alerter.config.max_duration_seconds = 60.0
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        alerter.alert_duration("slow-job", duration=120.5)

        mock_server.sendmail.assert_called_once()
        body = mock_server.sendmail.call_args[0][2]
        assert "SLOW" in body
        assert "120.50s" in body


def test_should_alert_duration_below_threshold(alerter):
    alerter.config.max_duration_seconds = 100.0
    assert alerter.should_alert_duration(50.0) is False


def test_should_alert_duration_above_threshold(alerter):
    alerter.config.max_duration_seconds = 100.0
    assert alerter.should_alert_duration(150.0) is True


def test_should_alert_duration_no_threshold(alerter):
    alerter.config.max_duration_seconds = None
    assert alerter.should_alert_duration(9999.0) is False


def test_alert_uses_tls(config):
    config.use_tls = True
    config.smtp_user = "user"
    config.smtp_password = "pass"
    alerter = Alerter(config)
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server
        alerter.alert_failure("job", exit_code=1)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user", "pass")
