"""Job runner with integrated retry support."""

import subprocess
from typing import Optional

from cronwrap.alerting import Alerter, AlertConfig
from cronwrap.logger import CronLogger
from cronwrap.retry import RetryConfig, RetryHandler


class JobRunner:
    """Runs a shell command as a cron job with logging, alerting, and retries."""

    def __init__(
        self,
        job_name: str,
        alerter: Optional[Alerter] = None,
        retry_config: Optional[RetryConfig] = None,
    ) -> None:
        self.job_name = job_name
        self.alerter = alerter
        self.logger = CronLogger(job_name)
        self.retry_handler = RetryHandler(retry_config or RetryConfig(max_attempts=1, delay_seconds=0))

    def run(self, command: str) -> int:
        """Execute *command* in a shell.  Returns the exit code."""
        self.logger.log_start()
        try:
            exit_code = self.retry_handler.run(self.run_job, command)
        except Exception as exc:
            self.logger.error("Job failed after all retry attempts: %s", exc)
            exit_code = 1
            if self.alerter:
                self.alerter.alert_failure(
                    self.job_name,
                    error_message=str(exc),
                )
        finally:
            self.logger.log_end()
        return exit_code

    def run_job(self, command: str) -> int:
        """Run *command* once and return the exit code.

        Raises :class:`RuntimeError` on non-zero exit so the retry handler
        can detect failure.
        """
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.stdout:
            self.logger.info(result.stdout.rstrip())
        if result.stderr:
            self.logger.error(result.stderr.rstrip())
        if result.returncode != 0:
            raise RuntimeError(
                f"Command exited with code {result.returncode}: {command}"
            )
        return result.returncode
