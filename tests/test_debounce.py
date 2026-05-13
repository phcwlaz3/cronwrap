"""Tests for cronwrap.debounce."""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cronwrap.debounce import DebounceConfig, DebounceMiddleware


# ---------------------------------------------------------------------------
# DebounceConfig
# ---------------------------------------------------------------------------

def test_config_default_disabled():
    cfg = DebounceConfig()
    assert cfg.enabled is False


def test_config_enabled_when_positive():
    cfg = DebounceConfig(window_seconds=5.0)
    assert cfg.enabled is True


def test_config_negative_raises():
    with pytest.raises(ValueError, match="window_seconds"):
        DebounceConfig(window_seconds=-1)


def test_config_zero_is_valid():
    cfg = DebounceConfig(window_seconds=0)
    assert cfg.enabled is False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def state_dir(tmp_path: Path) -> Path:
    return tmp_path / "debounce_state"


@pytest.fixture()
def cfg(state_dir: Path) -> DebounceConfig:
    return DebounceConfig(window_seconds=60.0, state_dir=str(state_dir))


@pytest.fixture()
def disabled_cfg(state_dir: Path) -> DebounceConfig:
    return DebounceConfig(window_seconds=0, state_dir=str(state_dir))


# ---------------------------------------------------------------------------
# DebounceMiddleware — disabled
# ---------------------------------------------------------------------------

def test_disabled_debounce_always_runs_fn(disabled_cfg):
    mw = DebounceMiddleware(disabled_cfg, "job")
    fn = MagicMock(return_value=42)
    assert mw.run(fn) == 42
    assert fn.call_count == 1


def test_disabled_debounce_runs_fn_multiple_times(disabled_cfg):
    mw = DebounceMiddleware(disabled_cfg, "job")
    fn = MagicMock(return_value=0)
    mw.run(fn)
    mw.run(fn)
    assert fn.call_count == 2


# ---------------------------------------------------------------------------
# DebounceMiddleware — enabled, first run
# ---------------------------------------------------------------------------

def test_first_run_executes_fn(cfg, state_dir):
    mw = DebounceMiddleware(cfg, "myjob")
    fn = MagicMock(return_value=99)
    result = mw.run(fn)
    assert result == 99
    fn.assert_called_once()


def test_first_run_creates_state_file(cfg, state_dir):
    mw = DebounceMiddleware(cfg, "myjob")
    mw.run(lambda: None)
    assert (state_dir / "myjob.debounce.json").exists()


# ---------------------------------------------------------------------------
# DebounceMiddleware — within window (suppressed)
# ---------------------------------------------------------------------------

def test_second_immediate_run_is_suppressed(cfg):
    mw = DebounceMiddleware(cfg, "myjob")
    fn = MagicMock(return_value=1)
    mw.run(fn)          # first run — records timestamp
    result = mw.run(fn) # second run — should be debounced
    assert result is None
    assert fn.call_count == 1


# ---------------------------------------------------------------------------
# DebounceMiddleware — outside window (allowed)
# ---------------------------------------------------------------------------

def test_run_after_window_is_allowed(cfg, state_dir):
    mw = DebounceMiddleware(cfg, "myjob")
    fn = MagicMock(return_value=7)
    # Seed state file with a timestamp well in the past
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "myjob.debounce.json").write_text(
        json.dumps({"last_run": time.time() - 120.0})
    )
    result = mw.run(fn)
    assert result == 7
    fn.assert_called_once()


# ---------------------------------------------------------------------------
# DebounceMiddleware — args/kwargs forwarding
# ---------------------------------------------------------------------------

def test_args_and_kwargs_forwarded(cfg):
    mw = DebounceMiddleware(cfg, "myjob")
    fn = MagicMock(return_value=0)
    mw.run(fn, 1, 2, key="val")
    fn.assert_called_once_with(1, 2, key="val")
