"""Structured logger for cron job execution."""
from __future__ import annotations

import logging
import time
from typing import Any

from cronwrap.secret_mask import SecretMasker, SecretMaskConfig


class JobLoggerAdapter(logging.LoggerAdapter):
    """Injects job-level context into every log record."""

    def process(self, msg: str, kwargs: Any) -> tuple[str, Any]:  # type: ignore[override]
        job_name = self.extra.get("job_name", "unknown")
        return f"[{job_name}] {msg}", kwargs


class CronLogger:
    """High-level logger used by the job runner.

    Parameters
    ----------
    job_name:
        Identifier embedded in every log line.
    level:
        Python logging level (default ``logging.INFO``).
    masker:
        Optional :class:`SecretMasker` applied to all messages before emission.
    """

    def __init__(
        self,
        job_name: str,
        level: int = logging.INFO,
        masker: SecretMasker | None = None,
    ) -> None:
        self._job_name = job_name
        self._masker = masker or SecretMasker(SecretMaskConfig())
        base = logging.getLogger(f"cronwrap.{job_name}")
        base.setLevel(level)
        if not base.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(message)s")
            )
            base.addHandler(handler)
        self._logger = JobLoggerAdapter(base, {"job_name": job_name})
        self._start: float | None = None
        self._end: float | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def log_start(self) -> None:
        """Record the job start time and emit an info line."""
        self._start = time.monotonic()
        self._logger.info("Job started")

    def log_end(self, exit_code: int) -> None:
        """Record the job end time and emit a summary line."""
        self._end = time.monotonic()
        duration = (
            round(self._end - self._start, 3) if self._start is not None else None
        )
        status = "succeeded" if exit_code == 0 else "failed"
        self._logger.info(
            "Job %s | exit_code=%d | duration=%s",
            status,
            exit_code,
            f"{duration}s" if duration is not None else "unknown",
        )

    # ------------------------------------------------------------------
    # Forwarded logging methods
    # ------------------------------------------------------------------

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.info(self._masker.mask(msg), *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.warning(self._masker.mask(msg), *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.error(self._masker.mask(msg), *args, **kwargs)

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.debug(self._masker.mask(msg), *args, **kwargs)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def start_time(self) -> float | None:
        return self._start

    @property
    def end_time(self) -> float | None:
        return self._end
