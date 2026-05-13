"""Heartbeat pings for cron job liveness monitoring."""
from __future__ import annotations

import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HeartbeatConfig:
    """Configuration for heartbeat pings."""

    url: str = ""
    timeout_seconds: int = 10
    ping_on_start: bool = False
    ping_on_success: bool = True
    ping_on_failure: bool = False
    extra_params: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive integer")

    @property
    def enabled(self) -> bool:
        return bool(self.url)


class HeartbeatSender:
    """Sends HTTP GET pings to a heartbeat URL."""

    def __init__(self, config: HeartbeatConfig) -> None:
        self._config = config

    def _build_url(self, suffix: str = "") -> str:
        base = self._config.url.rstrip("/")
        return f"{base}/{suffix}".rstrip("/") if suffix else base

    def _ping(self, url: str) -> bool:
        """Send a GET request; return True on HTTP 2xx, False otherwise."""
        try:
            with urllib.request.urlopen(url, timeout=self._config.timeout_seconds) as resp:
                return 200 <= resp.status < 300
        except (urllib.error.URLError, OSError):
            return False

    def ping_start(self) -> Optional[bool]:
        if not self._config.enabled or not self._config.ping_on_start:
            return None
        return self._ping(self._build_url("start"))

    def ping_success(self) -> Optional[bool]:
        if not self._config.enabled or not self._config.ping_on_success:
            return None
        return self._ping(self._build_url())

    def ping_failure(self) -> Optional[bool]:
        if not self._config.enabled or not self._config.ping_on_failure:
            return None
        return self._ping(self._build_url("fail"))
