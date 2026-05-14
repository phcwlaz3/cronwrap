"""Label/tag attachment and filtering for cron job runs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, Mapping


@dataclass
class LabelConfig:
    """Configuration for labels attached to a job run."""

    labels: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.labels, dict):
            raise TypeError("labels must be a dict")
        for k, v in self.labels.items():
            if not isinstance(k, str) or not k.strip():
                raise ValueError(f"Label key must be a non-empty string, got {k!r}")
            if not isinstance(v, str):
                raise TypeError(f"Label value must be a string, got {v!r}")
        # Normalise: strip whitespace from keys and values
        self.labels = {k.strip(): v.strip() for k, v in self.labels.items()}


class LabelMatcher:
    """Checks whether a set of labels satisfies a required selector."""

    def __init__(self, required: Mapping[str, str]) -> None:
        self._required: Dict[str, str] = dict(required)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def matches(self, labels: Mapping[str, str]) -> bool:
        """Return True if *all* required key/value pairs are present in *labels*."""
        for key, value in self._required.items():
            if labels.get(key) != value:
                return False
        return True

    def missing_keys(self, labels: Mapping[str, str]) -> FrozenSet[str]:
        """Return the set of required keys absent from *labels*."""
        return frozenset(k for k in self._required if k not in labels)


def merge_labels(*sources: Mapping[str, str]) -> Dict[str, str]:
    """Merge multiple label mappings left-to-right; later sources win."""
    result: Dict[str, str] = {}
    for source in sources:
        result.update(source)
    return result


def labels_to_str(labels: Mapping[str, str]) -> str:
    """Serialise labels to a comma-separated ``key=value`` string."""
    return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


def labels_from_str(raw: str) -> Dict[str, str]:
    """Parse a comma-separated ``key=value`` string back to a dict."""
    if not raw.strip():
        return {}
    result: Dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if "=" not in part:
            raise ValueError(f"Invalid label segment (expected key=value): {part!r}")
        key, _, value = part.partition("=")
        result[key.strip()] = value.strip()
    return result
