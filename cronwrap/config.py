"""Configuration loading and validation for cronwrap jobs."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CronJobConfig:
    """Top-level configuration for a cronwrap-managed job."""

    # Job identity
    job_name: str
    command: str

    # Alerting
    alert_on_failure: bool = True
    alert_on_duration: bool = False
    alert_recipients: List[str] = field(default_factory=list)
    smtp_host: str = "localhost"
    smtp_port: int = 25
    max_duration_seconds: Optional[float] = None

    # Retry
    retry_enabled: bool = False
    retry_max_attempts: int = 1
    retry_delay: float = 0.0
    retry_backoff: float = 1.0

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.job_name:
            raise ValueError("job_name must not be empty")
        if not self.command:
            raise ValueError("command must not be empty")
        if self.smtp_port < 1 or self.smtp_port > 65535:
            raise ValueError(f"smtp_port must be between 1 and 65535, got {self.smtp_port}")


def load_from_env(prefix: str = "CRONWRAP") -> dict:
    """Load configuration values from environment variables.

    Variables are expected in the form ``<PREFIX>_<KEY>`` (upper-cased).
    Returns a dict suitable for unpacking into :class:`CronJobConfig`.
    """
    mapping = {
        "JOB_NAME": ("job_name", str),
        "COMMAND": ("command", str),
        "ALERT_ON_FAILURE": ("alert_on_failure", lambda v: v.lower() in ("1", "true", "yes")),
        "ALERT_ON_DURATION": ("alert_on_duration", lambda v: v.lower() in ("1", "true", "yes")),
        "ALERT_RECIPIENTS": ("alert_recipients", lambda v: [r.strip() for r in v.split(",") if r.strip()]),
        "SMTP_HOST": ("smtp_host", str),
        "SMTP_PORT": ("smtp_port", int),
        "MAX_DURATION_SECONDS": ("max_duration_seconds", float),
        "RETRY_ENABLED": ("retry_enabled", lambda v: v.lower() in ("1", "true", "yes")),
        "RETRY_MAX_ATTEMPTS": ("retry_max_attempts", int),
        "RETRY_DELAY": ("retry_delay", float),
        "RETRY_BACKOFF": ("retry_backoff", float),
        "LOG_LEVEL": ("log_level", str),
        "LOG_FILE": ("log_file", str),
    }
    result: dict = {}
    for env_key, (attr, cast) in mapping.items():
        full_key = f"{prefix}_{env_key}"
        value = os.environ.get(full_key)
        if value is not None:
            result[attr] = cast(value)
    return result
