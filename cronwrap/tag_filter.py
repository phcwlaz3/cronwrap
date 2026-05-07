"""Tag-based filtering for cron jobs.

Allows jobs to declare tags and provides a filter that decides
whether a job should run based on an inclusion/exclusion list.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Collection, FrozenSet, Optional


@dataclass
class TagFilterConfig:
    """Configuration for tag-based job filtering."""

    include: FrozenSet[str] = field(default_factory=frozenset)
    exclude: FrozenSet[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        # Normalise to frozensets so the config is hashable / immutable.
        object.__setattr__(self, "include", frozenset(self.include))
        object.__setattr__(self, "exclude", frozenset(self.exclude))

        overlap = self.include & self.exclude
        if overlap:
            raise ValueError(
                f"Tags appear in both include and exclude lists: {sorted(overlap)}"
            )

    # Make the dataclass effectively frozen after __post_init__.
    def __setattr__(self, name: str, value: object) -> None:  # type: ignore[override]
        raise AttributeError("TagFilterConfig is immutable")


class TagFilter:
    """Decides whether a job with a given set of tags should run."""

    def __init__(self, config: Optional[TagFilterConfig] = None) -> None:
        self._config = config or TagFilterConfig()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def should_run(self, job_tags: Collection[str]) -> bool:
        """Return *True* if the job should run given its tags.

        Rules (applied in order):
        1. If *exclude* is non-empty and the job has **any** excluded tag
           → skip.
        2. If *include* is non-empty and the job has **no** included tag
           → skip.
        3. Otherwise → run.
        """
        tags = frozenset(job_tags)
        cfg = self._config

        if cfg.exclude and tags & cfg.exclude:
            return False

        if cfg.include and not (tags & cfg.include):
            return False

        return True

    def matching_tags(self, job_tags: Collection[str]) -> FrozenSet[str]:
        """Return the subset of *job_tags* that match the include list."""
        if not self._config.include:
            return frozenset(job_tags)
        return frozenset(job_tags) & self._config.include
