"""Tests for cronwrap.runner (including timeout integration)."""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from cronwrap.alerting import Alerter
from cronwrap.metrics import JobMetrics
from cronwrap.retry import RetryConfig
from cronwrap.runner import JobRunner
from cronwrap.timeout import TimeoutConfig


def make_runner(
    command: str = "true",
    alerter=None,
    retry_config=None,
    timeout_config=None,
) -> JobRunner:
    return JobRunner(
        command=command,
        alerter=alerter,
        retry_config=retry_config or RetryConfig(),
        timeout_config=timeout_config or TimeoutConfig(),
        metrics=JobMetrics(job_name="test"),
    )


def test_runner_returns_zero_on_success():
    runner = make_runner(command="true")
    assert runner.run() == 0


def test_runner_returns_nonzero_on_failure():
    runner = make_runner(command="false")
    assert runner.run() != 0


def test_runner_calls_alert_on_failure():
    alerter = MagicMock(spec=Alerter)
    runner = make_runner(command="false", alerter=alerter)
    runner.run()
    alerter.alert_failure.assert_called_once()


def test_runner_does_not_alert_on_success():
    alerter = MagicMock(spec=Alerter)
    runner = make_runner(command="true", alerter=alerter)
    runner.run()
    alerter.alert_failure.assert_not_called()


def test_runner_records_metrics_start_and_end():
    runner = make_runner(command="true")
    runner.run()
    assert runner.metrics.start_time is not None
    assert runner.metrics.end_time is not None


def test_runner_timeout_returns_124():
    """A job that sleeps longer than the timeout should return exit code 124."""
    timeout_cfg = TimeoutConfig(seconds=1)
    runner = make_runner(
        command="sleep 10",
        timeout_config=timeout_cfg,
    )
    # We mock run_job so the test stays fast
    def _slow() -> int:
        time.sleep(5)
        return 0

    with patch.object(runner, "run_job", side_effect=_slow):
        code = runner.run()

    assert code == 124


def test_runner_timeout_alerts_on_expire():
    alerter = MagicMock(spec=Alerter)
    timeout_cfg = TimeoutConfig(seconds=1)
    runner = make_runner(command="sleep 10", alerter=alerter, timeout_config=timeout_cfg)

    def _slow() -> int:
        time.sleep(5)
        return 0

    with patch.object(runner, "run_job", side_effect=_slow):
        runner.run()

    alerter.alert_failure.assert_called()


def test_runner_no_timeout_when_disabled():
    timeout_cfg = TimeoutConfig(seconds=0)
    runner = make_runner(command="true", timeout_config=timeout_cfg)
    assert runner.run() == 0
