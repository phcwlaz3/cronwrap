"""Integration tests: TimeoutHandler wired into a real subprocess command."""
from __future__ import annotations

import subprocess
import sys
import time

import pytest

from cronwrap.timeout import TimeoutConfig, TimeoutExpired, TimeoutHandler


def _run_command(cmd: str) -> int:
    return subprocess.run(cmd, shell=True).returncode  # noqa: S602,S603


def test_integration_fast_command_completes():
    cfg = TimeoutConfig(seconds=5)
    handler = TimeoutHandler(cfg)
    code = handler.run(lambda: _run_command("true"))
    assert code == 0


def test_integration_failing_command_returns_nonzero():
    cfg = TimeoutConfig(seconds=5)
    handler = TimeoutHandler(cfg)
    code = handler.run(lambda: _run_command("false"))
    assert code != 0


def test_integration_timeout_fires_on_slow_command():
    cfg = TimeoutConfig(seconds=1)
    handler = TimeoutHandler(cfg)

    def _slow() -> int:
        time.sleep(10)
        return 0

    with pytest.raises(TimeoutExpired):
        handler.run(_slow)


def test_integration_no_timeout_zero_seconds():
    cfg = TimeoutConfig(seconds=0)
    handler = TimeoutHandler(cfg)
    # Should complete immediately without raising
    code = handler.run(lambda: _run_command("true"))
    assert code == 0


def test_integration_exit_code_passthrough():
    cfg = TimeoutConfig(seconds=5)
    handler = TimeoutHandler(cfg)
    # `exit 3` in a subshell
    code = handler.run(lambda: _run_command(f"{sys.executable} -c 'raise SystemExit(3)'"))
    assert code == 3
