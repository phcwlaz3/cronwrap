"""JobRunner — executes a cron command with optional alerting, retry, and rate limiting."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Optional

from cronwrap.alerting import Alerter
from cronwrap.metrics import JobMetrics
from cronwrap.ratelimit import RateLimiter, RateLimitConfig


@dataclass
class JobRunner:
    command: str
    job_name: str = "unnamed"
    alerter: Optional[Alerter] = None
    rate_limiter: Optional[RateLimiter] = None
    timeout: Optional[int] = None  # seconds; None means no timeout

    def run(self) -> int:
        """Run the job, respecting rate limits.  Returns the exit code."""
        if self.rate_limiter is not None:
            if not self.rate_limiter.is_allowed(self.job_name):
                remaining = self.rate_limiter.seconds_until_allowed(self.job_name)
                print(
                    f"[cronwrap] Job '{self.job_name}' skipped — "
                    f"rate limited for another {remaining:.0f}s."
                )
                return 0

        metrics = JobMetrics(job_name=self.job_name, command=self.command)
        metrics.log_start()

        exit_code = self._execute(metrics)

        metrics.log_end(exit_code)

        if self.rate_limiter is not None:
            self.rate_limiter.record_run(self.job_name)

        if exit_code != 0 and self.alerter is not None:
            self.alerter.alert_failure(metrics)

        return exit_code

    def _execute(self, metrics: JobMetrics) -> int:
        try:
            result = subprocess.run(
                self.command,
                shell=True,
                timeout=self.timeout,
            )
            return result.returncode
        except subprocess.TimeoutExpired:
            print(f"[cronwrap] Job '{self.job_name}' timed out after {self.timeout}s.")
            return 124
        except Exception as exc:  # noqa: BLE001
            print(f"[cronwrap] Job '{self.job_name}' raised an unexpected error: {exc}")
            return 1


def run_job(command: str, **kwargs) -> int:  # pragma: no cover
    """Convenience wrapper — create a runner and execute immediately."""
    return JobRunner(command=command, **kwargs).run()
