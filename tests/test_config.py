"""Tests for CronJobConfig and load_from_env."""
import pytest

from cronwrap.config import CronJobConfig, load_from_env


# ---------------------------------------------------------------------------
# CronJobConfig validation
# ---------------------------------------------------------------------------

def _base(**kwargs):
    defaults = {"job_name": "my-job", "command": "echo hello"}
    defaults.update(kwargs)
    return CronJobConfig(**defaults)


def test_valid_config_creates_instance():
    cfg = _base()
    assert cfg.job_name == "my-job"
    assert cfg.command == "echo hello"


def test_empty_job_name_raises():
    with pytest.raises(ValueError, match="job_name"):
        _base(job_name="")


def test_empty_command_raises():
    with pytest.raises(ValueError, match="command"):
        _base(command="")


def test_invalid_smtp_port_raises():
    with pytest.raises(ValueError, match="smtp_port"):
        _base(smtp_port=0)
    with pytest.raises(ValueError, match="smtp_port"):
        _base(smtp_port=99999)


def test_defaults():
    cfg = _base()
    assert cfg.alert_on_failure is True
    assert cfg.alert_on_duration is False
    assert cfg.alert_recipients == []
    assert cfg.retry_enabled is False
    assert cfg.retry_max_attempts == 1
    assert cfg.log_level == "INFO"
    assert cfg.log_file is None
    assert cfg.max_duration_seconds is None


# ---------------------------------------------------------------------------
# load_from_env
# ---------------------------------------------------------------------------

def test_load_from_env_returns_empty_when_no_vars_set(monkeypatch):
    for key in list(__import__("os").environ):
        if key.startswith("CRONWRAP_"):
            monkeypatch.delenv(key, raising=False)
    result = load_from_env()
    assert result == {}


def test_load_from_env_picks_up_job_name(monkeypatch):
    monkeypatch.setenv("CRONWRAP_JOB_NAME", "backup")
    result = load_from_env()
    assert result["job_name"] == "backup"


def test_load_from_env_parses_bool_true(monkeypatch):
    monkeypatch.setenv("CRONWRAP_RETRY_ENABLED", "true")
    result = load_from_env()
    assert result["retry_enabled"] is True


def test_load_from_env_parses_bool_false(monkeypatch):
    monkeypatch.setenv("CRONWRAP_ALERT_ON_FAILURE", "0")
    result = load_from_env()
    assert result["alert_on_failure"] is False


def test_load_from_env_parses_recipients_list(monkeypatch):
    monkeypatch.setenv("CRONWRAP_ALERT_RECIPIENTS", "a@x.com, b@x.com")
    result = load_from_env()
    assert result["alert_recipients"] == ["a@x.com", "b@x.com"]


def test_load_from_env_custom_prefix(monkeypatch):
    monkeypatch.setenv("MYJOB_JOB_NAME", "nightly")
    result = load_from_env(prefix="MYJOB")
    assert result["job_name"] == "nightly"


def test_load_from_env_parses_numeric_types(monkeypatch):
    monkeypatch.setenv("CRONWRAP_SMTP_PORT", "587")
    monkeypatch.setenv("CRONWRAP_RETRY_DELAY", "2.5")
    result = load_from_env()
    assert result["smtp_port"] == 587
    assert result["retry_delay"] == 2.5
