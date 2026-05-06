"""Tests for file-based config loading and build_config merging."""
import json
import pytest

from cronwrap.config import CronJobConfig
from cronwrap.config_loader import build_config, load_config_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MIN_JSON = {"job_name": "test-job", "command": "true"}


def write_json(tmp_path, data):
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data))
    return p


# ---------------------------------------------------------------------------
# load_config_file
# ---------------------------------------------------------------------------

def test_load_json_file(tmp_path):
    p = write_json(tmp_path, MIN_JSON)
    result = load_config_file(p)
    assert result["job_name"] == "test-job"


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config_file(tmp_path / "missing.json")


def test_load_unsupported_extension_raises(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text("job_name: x")
    with pytest.raises(ValueError, match="Unsupported"):
        load_config_file(p)


# ---------------------------------------------------------------------------
# build_config merging
# ---------------------------------------------------------------------------

def test_build_config_from_json_file(tmp_path):
    p = write_json(tmp_path, MIN_JSON)
    cfg = build_config(file_path=p)
    assert isinstance(cfg, CronJobConfig)
    assert cfg.job_name == "test-job"


def test_env_overrides_file(tmp_path, monkeypatch):
    p = write_json(tmp_path, {**MIN_JSON, "log_level": "DEBUG"})
    monkeypatch.setenv("CRONWRAP_LOG_LEVEL", "WARNING")
    cfg = build_config(file_path=p)
    assert cfg.log_level == "WARNING"


def test_overrides_dict_takes_highest_priority(tmp_path, monkeypatch):
    p = write_json(tmp_path, {**MIN_JSON, "smtp_port": 25})
    monkeypatch.setenv("CRONWRAP_SMTP_PORT", "465")
    cfg = build_config(file_path=p, overrides={"smtp_port": 587})
    assert cfg.smtp_port == 587


def test_build_config_without_file(monkeypatch):
    monkeypatch.setenv("CRONWRAP_JOB_NAME", "env-job")
    monkeypatch.setenv("CRONWRAP_COMMAND", "ls")
    cfg = build_config()
    assert cfg.job_name == "env-job"
    assert cfg.command == "ls"


def test_build_config_overrides_only():
    cfg = build_config(overrides={"job_name": "override-job", "command": "pwd"})
    assert cfg.job_name == "override-job"
