"""Redact sensitive fields from log output and recorded data."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_DEFAULT_PATTERNS: tuple[str, ...] = (
    r"(?i)(password|passwd|secret|token|api[_-]?key|auth)[=:\s]+\S+",
    r"(?i)(bearer\s+)\S+",
)

_PLACEHOLDER = "[REDACTED]"


@dataclass
class RedactConfig:
    """Configuration for the Redactor."""

    patterns: tuple[str, ...] = field(default_factory=lambda: _DEFAULT_PATTERNS)
    placeholder: str = _PLACEHOLDER
    redact_dict_keys: tuple[str, ...] = field(
        default_factory=lambda: (
            "password",
            "passwd",
            "secret",
            "token",
            "api_key",
            "apikey",
            "auth",
        )
    )

    def __post_init__(self) -> None:
        if not self.placeholder:
            raise ValueError("placeholder must not be empty")
        if not self.patterns:
            raise ValueError("patterns must not be empty")


class Redactor:
    """Redacts sensitive information from strings and dicts."""

    def __init__(self, config: RedactConfig | None = None) -> None:
        self._cfg = config or RedactConfig()
        self._compiled = [
            re.compile(p) for p in self._cfg.patterns
        ]

    def redact_string(self, text: str) -> str:
        """Return *text* with sensitive patterns replaced by the placeholder."""
        result = text
        for pattern in self._compiled:
            result = pattern.sub(self._cfg.placeholder, result)
        return result

    def redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Return a shallow copy of *data* with sensitive keys masked."""
        sensitive = {k.lower() for k in self._cfg.redact_dict_keys}
        out: dict[str, Any] = {}
        for key, value in data.items():
            if key.lower() in sensitive:
                out[key] = self._cfg.placeholder
            elif isinstance(value, str):
                out[key] = self.redact_string(value)
            else:
                out[key] = value
        return out
