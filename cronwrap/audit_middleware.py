"""Middleware that wraps a callable job and emits audit events automatically."""
from __future__ import annotations

from typing import Callable, Optional

from cronwrap.audit import AuditEvent, AuditLog


class AuditMiddleware:
    """Wraps a job callable and writes audit events before and after execution.

    Parameters
    ----------
    job_name:
        Identifier used in every :class:`~cronwrap.audit.AuditEvent`.
    audit_log:
        :class:`~cronwrap.audit.AuditLog` instance to write events to.
    attempt:
        Current attempt number (1-based); forwarded to each event.
    """

    def __init__(
        self,
        job_name: str,
        audit_log: AuditLog,
        attempt: int = 1,
    ) -> None:
        self._job_name = job_name
        self._log = audit_log
        self._attempt = attempt

    def run(self, fn: Callable[[], int]) -> int:
        """Execute *fn*, record audit events, and return its exit code.

        The callable must return an integer exit code (0 = success).
        Any uncaught exception is recorded as a failure event and re-raised.
        """
        self._log.record(
            AuditEvent(
                job_name=self._job_name,
                event="start",
                attempt=self._attempt,
            )
        )
        try:
            exit_code: int = fn()
        except Exception as exc:  # noqa: BLE001
            self._log.record(
                AuditEvent(
                    job_name=self._job_name,
                    event="failure",
                    exit_code=1,
                    attempt=self._attempt,
                    detail=str(exc),
                )
            )
            raise

        event_name = "success" if exit_code == 0 else "failure"
        self._log.record(
            AuditEvent(
                job_name=self._job_name,
                event=event_name,
                exit_code=exit_code,
                attempt=self._attempt,
            )
        )
        return exit_code
