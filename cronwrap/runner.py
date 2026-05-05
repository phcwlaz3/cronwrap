"""Job runner module — executes shell commands and integrates logging + alerting."""

import subprocess
import time
from typing import Optional

from cronwrap.logger import CronLogger
from cronwrap.alerting import Alerter, AlertConfig


class JobRunner:
    """Runs a cron job command with logging and optional alerting."""

    def __init__(
        self,
        job_name: str,
        command: str,
        logger: Optional[CronLogger] = None,
        alerter: Optional[Alerter] = None,
        timeout: Optional[float] = None,
    ):
        self.job_name = job_name
        self.command = command
        self.logger = logger or CronLogger(job_name)
        self.alerter = alerter
        self.timeout = timeout

    def run(self) -> int:
        """Execute the command and return its exit code."""
        log = self.logger
        log.log_start()
        log.info(f"Running command: {self.command}")

        start = time.monotonic()
        exit_code = 0
        stderr_output = ""

        try:
            result = subprocess.run(
                self.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            exit_code = result.returncode
            stderr_output = result.stderr

            if result.stdout:
                log.info(f"stdout: {result.stdout.rstrip()}")
            if result.stderr:
                log.warning(f"stderr: {result.stderr.rstrip()}")

        except subprocess.TimeoutExpired as exc:
            exit_code = -1
            stderr_output = f"Timed out after {self.timeout}s"
            log.error(stderr_output)

        duration = time.monotonic() - start
        log.log_end(exit_code=exit_code)

        if exit_code != 0 and self.alerter:
            self.alerter.alert_failure(self.job_name, exit_code, stderr_output)

        if self.alerter and self.alerter.should_alert_duration(duration):
            self.alerter.alert_duration(self.job_name, duration)

        return exit_code


def run_job(
    job_name: str,
    command: str,
    alert_config: Optional[AlertConfig] = None,
    timeout: Optional[float] = None,
) -> int:
    """Convenience function to run a job with optional alert configuration."""
    alerter = Alerter(alert_config) if alert_config else None
    runner = JobRunner(job_name, command, alerter=alerter, timeout=timeout)
    return runner.run()
