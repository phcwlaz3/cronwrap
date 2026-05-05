"""Logging module for cronwrap — provides structured logging for cron job execution."""

import logging
import sys
from datetime import datetime
from typing import Optional


DEFAULT_FORMAT = "[%(asctime)s] [%(levelname)s] [%(job_name)s] %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class JobLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that injects job_name into every log record."""

    def process(self, msg, kwargs):
        return msg, {**kwargs, "extra": {**self.extra, **(kwargs.get("extra") or {})}}


class CronLogger:
    """Structured logger for a cron job run."""

    def __init__(self, job_name: str, log_file: Optional[str] = None, level: int = logging.INFO):
        self.job_name = job_name
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

        self._logger = logging.getLogger(f"cronwrap.{job_name}")
        self._logger.setLevel(level)
        self._logger.handlers.clear()

        formatter = logging.Formatter(fmt=DEFAULT_FORMAT, datefmt=DEFAULT_DATE_FORMAT)
        formatter.default_msec_format = ""

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

        # Optional file handler
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

        self._adapter = logging.LoggerAdapter(self._logger, extra={"job_name": job_name})

    def info(self, message: str) -> None:
        self._adapter.info(message)

    def warning(self, message: str) -> None:
        self._adapter.warning(message)

    def error(self, message: str) -> None:
        self._adapter.error(message)

    def debug(self, message: str) -> None:
        self._adapter.debug(message)

    def log_start(self) -> None:
        self.start_time = datetime.utcnow()
        self.info(f"Job started at {self.start_time.isoformat()}Z")

    def log_end(self, success: bool = True) -> None:
        self.end_time = datetime.utcnow()
        duration = (
            (self.end_time - self.start_time).total_seconds()
            if self.start_time
            else None
        )
        status = "SUCCESS" if success else "FAILURE"
        duration_str = f" | duration={duration:.3f}s" if duration is not None else ""
        self.info(f"Job finished — status={status}{duration_str}")
