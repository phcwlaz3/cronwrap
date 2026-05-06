"""Notification hooks for cron job lifecycle events."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from cronwrap.metrics import JobMetrics

logger = logging.getLogger(__name__)

NotifyHook = Callable[[str, JobMetrics], None]


@dataclass
class NotifierConfig:
    """Configuration for the Notifier."""
    on_start: List[NotifyHook] = field(default_factory=list)
    on_success: List[NotifyHook] = field(default_factory=list)
    on_failure: List[NotifyHook] = field(default_factory=list)
    on_finish: List[NotifyHook] = field(default_factory=list)


class Notifier:
    """Dispatches lifecycle notifications for a cron job."""

    def __init__(self, job_name: str, config: Optional[NotifierConfig] = None) -> None:
        self.job_name = job_name
        self.config = config or NotifierConfig()

    def _dispatch(self, hooks: List[NotifyHook], metrics: JobMetrics) -> None:
        for hook in hooks:
            try:
                hook(self.job_name, metrics)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning(
                    "Notifier hook %s raised an exception: %s",
                    getattr(hook, "__name__", repr(hook)),
                    exc,
                )

    def notify_start(self, metrics: JobMetrics) -> None:
        """Fire on-start hooks."""
        logger.debug("Job '%s' started.", self.job_name)
        self._dispatch(self.config.on_start, metrics)

    def notify_success(self, metrics: JobMetrics) -> None:
        """Fire on-success and on-finish hooks."""
        logger.debug("Job '%s' succeeded.", self.job_name)
        self._dispatch(self.config.on_success, metrics)
        self._dispatch(self.config.on_finish, metrics)

    def notify_failure(self, metrics: JobMetrics) -> None:
        """Fire on-failure and on-finish hooks."""
        logger.debug("Job '%s' failed.", self.job_name)
        self._dispatch(self.config.on_failure, metrics)
        self._dispatch(self.config.on_finish, metrics)
