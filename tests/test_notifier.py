"""Tests for cronwrap.notifier."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwrap.metrics import JobMetrics
from cronwrap.notifier import Notifier, NotifierConfig


@pytest.fixture()
def metrics() -> JobMetrics:
    m = JobMetrics(job_name="test-job")
    m.start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    m.end_time = datetime(2024, 1, 1, 12, 0, 5, tzinfo=timezone.utc)
    m.exit_code = 0
    return m


def test_notify_start_calls_on_start_hooks(metrics):
    hook = MagicMock()
    cfg = NotifierConfig(on_start=[hook])
    notifier = Notifier("test-job", cfg)
    notifier.notify_start(metrics)
    hook.assert_called_once_with("test-job", metrics)


def test_notify_success_calls_on_success_and_on_finish(metrics):
    success_hook = MagicMock()
    finish_hook = MagicMock()
    cfg = NotifierConfig(on_success=[success_hook], on_finish=[finish_hook])
    notifier = Notifier("test-job", cfg)
    notifier.notify_success(metrics)
    success_hook.assert_called_once_with("test-job", metrics)
    finish_hook.assert_called_once_with("test-job", metrics)


def test_notify_failure_calls_on_failure_and_on_finish(metrics):
    failure_hook = MagicMock()
    finish_hook = MagicMock()
    cfg = NotifierConfig(on_failure=[failure_hook], on_finish=[finish_hook])
    notifier = Notifier("test-job", cfg)
    notifier.notify_failure(metrics)
    failure_hook.assert_called_once_with("test-job", metrics)
    finish_hook.assert_called_once_with("test-job", metrics)


def test_notify_success_does_not_call_failure_hook(metrics):
    failure_hook = MagicMock()
    cfg = NotifierConfig(on_failure=[failure_hook])
    notifier = Notifier("test-job", cfg)
    notifier.notify_success(metrics)
    failure_hook.assert_not_called()


def test_notify_failure_does_not_call_success_hook(metrics):
    success_hook = MagicMock()
    cfg = NotifierConfig(on_success=[success_hook])
    notifier = Notifier("test-job", cfg)
    notifier.notify_failure(metrics)
    success_hook.assert_not_called()


def test_failing_hook_does_not_raise(metrics):
    def bad_hook(name, m):
        raise RuntimeError("boom")

    cfg = NotifierConfig(on_start=[bad_hook])
    notifier = Notifier("test-job", cfg)
    # Should not propagate the exception
    notifier.notify_start(metrics)


def test_default_config_has_empty_hooks(metrics):
    notifier = Notifier("test-job")
    # None of these should raise
    notifier.notify_start(metrics)
    notifier.notify_success(metrics)
    notifier.notify_failure(metrics)


def test_multiple_hooks_all_called(metrics):
    hooks = [MagicMock(), MagicMock(), MagicMock()]
    cfg = NotifierConfig(on_finish=hooks)
    notifier = Notifier("test-job", cfg)
    notifier.notify_success(metrics)
    for h in hooks:
        h.assert_called_once_with("test-job", metrics)
