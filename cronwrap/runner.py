"""Job runner with optional retry, alerting, and timeout support."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Optional

from cronwrap.alerting import Alerter
from cronwrap.metrics import JobMetrics
from cronwrap.retry import RetryConfig, RetryHandler
from cronwrap.timeout import TimeoutConfig, TimeoutExpired, TimeoutHandler


@dataclass
class JobRunner:
    command: str
    alerter: Optional[Alerter] = None
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    timeout_config: TimeoutConfig = field(default_factory=TimeoutConfig)
    metrics: JobMetrics = field(default_factory=JobMetrics)

    def run(self) -> int:
        """Execute the job, applying retry and timeout logic."""
        retry_handler = RetryHandler(self.retry_config)
        timeout_handler = TimeoutHandler(self.timeout_config)

        self.metrics.log_start()
        try:
            exit_code = retry_handler.run(
                lambda: timeout_handler.run(self.run_job)
            )
        except TimeoutExpired as exc:
            exit_code = 124  # same convention as the `timeout` shell command
            if self.alerter:
                self.alerter.alert_failure(
                    self.command,
                    self.metrics,
                    reason=str(exc),
                )
        finally:
            self.metrics.log_end(exit_code if 'exit_code' in dir() else 1)  # type: ignore[possibly-undefined]

        if exit_code != 0 and self.alerter:
            self.alerter.alert_failure(self.command, self.metrics)

        return exit_code

    def run_job(self) -> int:
        """Spawn the command in a subprocess and return its exit code."""
        result = subprocess.run(  # noqa: S603
            self.command,
            shell=True,  # noqa: S602
        )
        return result.returncode
