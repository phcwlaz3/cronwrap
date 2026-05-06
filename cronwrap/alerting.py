"""Alerting module for cronwrap — sends notifications on job failure or threshold breach."""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass, field
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class AlertConfig:
    """Configuration for alerting behaviour."""
    recipients: List[str] = field(default_factory=list)
    sender: str = "cronwrap@localhost"
    smtp_host: str = "localhost"
    smtp_port: int = 25
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    use_tls: bool = False
    max_duration_seconds: Optional[float] = None  # alert if job exceeds this


class Alerter:
    """Sends email alerts for cron job events."""

    def __init__(self, config: AlertConfig):
        self.config = config

    def _send_email(self, subject: str, body: str) -> None:
        """Send an email alert to all configured recipients."""
        if not self.config.recipients:
            return

        msg = MIMEMultipart()
        msg["From"] = self.config.sender
        msg["To"] = ", ".join(self.config.recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                if self.config.use_tls:
                    server.starttls()
                if self.config.smtp_user and self.config.smtp_password:
                    server.login(self.config.smtp_user, self.config.smtp_password)
                server.sendmail(self.config.sender, self.config.recipients, msg.as_string())
        except smtplib.SMTPException as exc:
            logger.error("Failed to send alert email '%s': %s", subject, exc)
        except OSError as exc:
            logger.error("Could not connect to SMTP server %s:%d — %s",
                         self.config.smtp_host, self.config.smtp_port, exc)

    def alert_failure(self, job_name: str, exit_code: int, stderr: str = "") -> None:
        """Send an alert when a job fails."""
        subject = f"[cronwrap] Job FAILED: {job_name}"
        body = (
            f"Job '{job_name}' exited with code {exit_code}.\n\n"
            f"Stderr output:\n{stderr or '(none)'}\n"
        )
        self._send_email(subject, body)

    def alert_duration(self, job_name: str, duration: float) -> None:
        """Send an alert when a job exceeds the max allowed duration."""
        limit = self.config.max_duration_seconds
        subject = f"[cronwrap] Job SLOW: {job_name}"
        body = (
            f"Job '{job_name}' took {duration:.2f}s, "
            f"exceeding the limit of {limit}s.\n"
        )
        self._send_email(subject, body)

    def should_alert_duration(self, duration: float) -> bool:
        """Return True if the duration exceeds the configured threshold."""
        if self.config.max_duration_seconds is None:
            return False
        return duration > self.config.max_duration_seconds
