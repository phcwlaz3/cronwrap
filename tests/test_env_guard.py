"""Tests for cronwrap.env_guard."""
from __future__ import annotations

import pytest

from cronwrap.env_guard import EnvGuard, EnvGuardConfig, EnvironmentMismatchError


# ---------------------------------------------------------------------------
# EnvGuardConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = EnvGuardConfig()
    assert cfg.allowed_envs == []
    assert cfg.env_var == "APP_ENV"
    assert cfg.enabled is True


def test_config_strips_whitespace():
    cfg = EnvGuardConfig(allowed_envs=[" production ", "staging"])
    assert cfg.allowed_envs == ["production", "staging"]


def test_config_filters_blank_entries():
    cfg = EnvGuardConfig(allowed_envs=["", "  ", "production"])
    assert cfg.allowed_envs == ["production"]


def test_config_invalid_env_var_raises():
    with pytest.raises(ValueError):
        EnvGuardConfig(env_var="")


def test_config_invalid_allowed_envs_type_raises():
    with pytest.raises(TypeError):
        EnvGuardConfig(allowed_envs="production")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# EnvGuard.check
# ---------------------------------------------------------------------------

def test_check_passes_when_disabled(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    cfg = EnvGuardConfig(allowed_envs=["production"], enabled=False)
    guard = EnvGuard(cfg)
    guard.check()  # should not raise


def test_check_passes_when_no_allowed_envs(monkeypatch):
    monkeypatch.setenv("APP_ENV", "anything")
    cfg = EnvGuardConfig(allowed_envs=[])
    guard = EnvGuard(cfg)
    guard.check()  # should not raise


def test_check_passes_when_env_matches(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    cfg = EnvGuardConfig(allowed_envs=["production", "staging"])
    guard = EnvGuard(cfg)
    guard.check()  # should not raise


def test_check_raises_when_env_not_in_allowed(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    cfg = EnvGuardConfig(allowed_envs=["production", "staging"])
    guard = EnvGuard(cfg)
    with pytest.raises(EnvironmentMismatchError, match="local"):
        guard.check()


def test_check_raises_when_env_var_unset(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    cfg = EnvGuardConfig(allowed_envs=["production"])
    guard = EnvGuard(cfg)
    with pytest.raises(EnvironmentMismatchError):
        guard.check()


def test_current_env_reads_custom_var(monkeypatch):
    monkeypatch.setenv("DEPLOY_ENV", "staging")
    cfg = EnvGuardConfig(env_var="DEPLOY_ENV", allowed_envs=["staging"])
    guard = EnvGuard(cfg)
    assert guard.current_env == "staging"
    guard.check()  # should not raise


# ---------------------------------------------------------------------------
# EnvGuard.run
# ---------------------------------------------------------------------------

def test_run_calls_fn_when_env_matches(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    cfg = EnvGuardConfig(allowed_envs=["production"])
    guard = EnvGuard(cfg)
    result = guard.run(lambda x: x * 2, 21)
    assert result == 42


def test_run_raises_before_calling_fn_on_mismatch(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    cfg = EnvGuardConfig(allowed_envs=["production"])
    guard = EnvGuard(cfg)
    called = []
    with pytest.raises(EnvironmentMismatchError):
        guard.run(lambda: called.append(True))
    assert called == []
