"""Middleware that attaches labels to a job run and enforces label selectors."""
from __future__ import annotations

from typing import Callable, Mapping, TypeVar

from .label import LabelConfig, LabelMatcher

T = TypeVar("T")


class LabelMiddleware:
    """Wraps a callable, enforcing that required labels are present before
    execution and attaching run-level labels to any returned mapping.

    Parameters
    ----------
    config:
        Labels that will be attached to the run.
    required:
        Optional selector that *config.labels* must satisfy before the
        wrapped function is called.  If the labels do not match,
        ``run`` raises ``ValueError`` and the function is *not* called.
    """

    def __init__(
        self,
        config: LabelConfig,
        required: Mapping[str, str] | None = None,
    ) -> None:
        self._config = config
        self._matcher = LabelMatcher(required) if required else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, fn: Callable[[], T]) -> T:
        """Validate labels (if a selector is configured) then call *fn*."""
        if self._matcher is not None:
            missing = self._matcher.missing_keys(self._config.labels)
            if missing:
                raise ValueError(
                    f"Required label keys missing from job config: {sorted(missing)}"
                )
            if not self._matcher.matches(self._config.labels):
                raise ValueError(
                    "Job labels do not satisfy the required selector."
                )
        return fn()
