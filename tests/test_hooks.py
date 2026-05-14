"""Tests for cronwrap.hooks."""
import pytest

from cronwrap.hooks import HookConfig, HookResult, HookRunner


# ---------------------------------------------------------------------------
# HookConfig
# ---------------------------------------------------------------------------

def test_hook_config_defaults():
    cfg = HookConfig()
    assert cfg.pre_hooks == []
    assert cfg.post_hooks == []
    assert cfg.timeout == 30
    assert cfg.stop_on_failure is True


def test_hook_config_invalid_timeout():
    with pytest.raises(ValueError, match="timeout"):
        HookConfig(timeout=0)


def test_hook_config_negative_timeout():
    """Negative timeout values should also raise ValueError."""
    with pytest.raises(ValueError, match="timeout"):
        HookConfig(timeout=-5)


# ---------------------------------------------------------------------------
# HookResult
# ---------------------------------------------------------------------------

def test_hook_result_succeeded_on_zero():
    r = HookResult(command="echo hi", exit_code=0, stdout="hi\n", stderr="")
    assert r.succeeded is True


def test_hook_result_failed_on_nonzero():
    r = HookResult(command="false", exit_code=1, stdout="", stderr="")
    assert r.succeeded is False


# ---------------------------------------------------------------------------
# HookRunner
# ---------------------------------------------------------------------------

@pytest.fixture()
def runner():
    cfg = HookConfig(
        pre_hooks=["echo pre"],
        post_hooks=["echo post"],
        timeout=5,
    )
    return HookRunner(cfg)


def test_run_pre_hooks_success(runner):
    results = runner.run_pre_hooks()
    assert len(results) == 1
    assert results[0].succeeded
    assert "pre" in results[0].stdout


def test_run_post_hooks_success(runner):
    results = runner.run_post_hooks()
    assert len(results) == 1
    assert results[0].succeeded


def test_stop_on_failure_halts_sequence():
    cfg = HookConfig(
        pre_hooks=["exit 1", "echo should_not_run"],
        stop_on_failure=True,
        timeout=5,
    )
    results = HookRunner(cfg).run_pre_hooks()
    assert len(results) == 1
    assert not results[0].succeeded


def test_continue_on_failure_runs_all():
    cfg = HookConfig(
        pre_hooks=["exit 1", "echo still_runs"],
        stop_on_failure=False,
        timeout=5,
    )
    results = HookRunner(cfg).run_pre_hooks()
    assert len(results) == 2


def test_timeout_returns_failure_result():
    cfg = HookConfig(pre_hooks=["sleep 10"], timeout=1)
    results = HookRunner(cfg).run_pre_hooks()
    assert len(results) == 1
    assert not results[0].succeeded
    assert "timed out" in results[0].stderr


def test_empty_hooks_returns_empty_list():
    cfg = HookConfig()
    runner = HookRunner(cfg)
    assert runner.run_pre_hooks() == []
    assert runner.run_post_hooks() == []


def test_hook_result_command_stored():
    """HookResult should preserve the original command string."""
    cmd = "echo hello"
    r = HookResult(command=cmd, exit_code=0, stdout="hello\n", stderr="")
    assert r.command == cmd
