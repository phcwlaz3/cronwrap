"""Utilities for masking sensitive values in log output."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

_DEFAULT_PATTERNS: list[str] = [
    r"(?i)(password|passwd|secret|token|api[_-]?key|auth)[=:\s]+\S+",
    r"(?i)(bearer\s+)\S+",
]

_MASK = "***"


@dataclass
class SecretMaskConfig:
    """Configuration for the secret masker."""

    extra_patterns: list[str] = field(default_factory=list)
    mask: str = _MASK

    def __post_init__(self) -> None:
        if not self.mask:
            raise ValueError("mask must be a non-empty string")


class SecretMasker:
    """Replaces secret-looking substrings with a fixed mask string."""

    def __init__(self, config: SecretMaskConfig | None = None) -> None:
        self._config = config or SecretMaskConfig()
        all_patterns = _DEFAULT_PATTERNS + self._config.extra_patterns
        self._regexes = [re.compile(p) for p in all_patterns]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def mask(self, text: str) -> str:
        """Return *text* with all detected secrets replaced by the mask."""
        for rx in self._regexes:
            text = rx.sub(self._replace, text)
        return text

    def mask_dict(self, data: dict) -> dict:
        """Return a shallow copy of *data* with string values masked."""
        return {k: self.mask(v) if isinstance(v, str) else v for k, v in data.items()}

    def mask_env(self, env: dict[str, str], sensitive_keys: Iterable[str]) -> dict[str, str]:
        """Mask specific environment-variable keys in *env*."""
        keys = frozenset(k.upper() for k in sensitive_keys)
        return {
            k: (self._config.mask if k.upper() in keys else v)
            for k, v in env.items()
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _replace(self, match: re.Match) -> str:  # type: ignore[type-arg]
        """Regex substitution callback — keeps the key part, masks the value."""
        full = match.group(0)
        # Preserve everything up to the last space/equals/colon then append mask
        prefix_match = re.match(r"^(.*?[=:\s]+)", full)
        if prefix_match:
            return prefix_match.group(1) + self._config.mask
        return self._config.mask
