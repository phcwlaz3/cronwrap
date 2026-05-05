"""Tests for the cronwrap job runner module."""

from unittest.mock import MagicMock, patch

import pytest

from cronwrap.alerting import AlertConfig, Alerter
from cronwrap.runner import JobRunner, run_job


def make_runner(command="echo hello", alerter=None, timeout=None):
    return JobRunner(
        job_name="test-job",
        command=command,
        alerter=alerter,
        timeout=timeout,
    )


def test_runner_returns_zero_on_success():
    runner = make_runner(command="echo ok")
    assert runner.run() == 0


def test_runner_returns_nonzero_on_failure():
    runner = make_runner(command="exit 42")
    assert runner.run() == 42


def test_runner_calls_alert_on_failure():
    mock_alerter = MagicMock(spec=Alerter)
    mock_alerter.should_alert_duration.return_value = False
    runner = make_runner(command="exit 1", alerter=mock_alerter)
    runner.run()
    mock_alerter.alert_failure.assert_called_once()
    call_kwargs = mock_alerter.alert_failure.call_args
    assert call_kwargs[0][0] == "test-job"
    assert call_kwargs[0][1] == 1


def test_runner_does_not_alert_on_success():
    mock_alerter = MagicMock(spec=Alerter)
    mock_alerter.should_alert_duration.return_value = False
    runner = make_runner(command="echo ok", alerter=mock_alerter)
    runner.run()
    mock_alerter.alert_failure.assert_not_called()


def test_runner_alerts_on_slow_job():
    mock_alerter = MagicMock(spec=Alerter)
    mock_alerter.should_alert_duration.return_value = True
    runner = make_runner(command="echo ok", alerter=mock_alerter)
    runner.run()
    mock_alerter.alert_duration.assert_called_once()


def test_runner_handles_timeout():
    runner = make_runner(command="sleep 10", timeout=0.01)
    exit_code = runner.run()
    assert exit_code == -1


def test_run_job_convenience_success():
    code = run_job("quick-job", "echo hi")
    assert code == 0


def test_run_job_with_alert_config():
    cfg = AlertConfig(recipients=["dev@example.com"])
    with patch("cronwrap.runner.Alerter") as MockAlerter:
        mock_alerter = MagicMock()
        mock_alerter.should_alert_duration.return_value = False
        MockAlerter.return_value = mock_alerter
        code = run_job("job", "echo test", alert_config=cfg)
    assert code == 0
    MockAlerter.assert_called_once_with(cfg)
