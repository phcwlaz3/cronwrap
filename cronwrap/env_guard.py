"""Environment variable guard — prevents accidental runs outside expected environments."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional


class EnvironmentMismatchError(Exception):
    """Raised when the current environment is not in the allowed list."""


@dataclass
class EnvGuardConfig:
    """Configuration for the environment guard."""

    allowed_envs: List[str] = field(default_factory=list)
    env_var: str = "APP_ENV"
    enabled: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.allowed_envs, list):
            raise TypeError("allowed_envs must be a list")
        if not self.env_var or not self.env_var.strip():
            raise ValueError("env_var must be a non-empty string")
        self.allowed_envs = [e.strip() for e in self.allowed_envs if e.strip()]


class EnvGuard:
    """Checks that the current environment is permitted before running a job."""

    def __init__(self, config: EnvGuardConfig) -> None:
        self._config = config

    @property
    def current_env(self) -> Optional[str]:
        return os.environ.get(self._config.env_var)

    def check(self) -> None:
        """Raise EnvironmentMismatchError if the current env is not allowed."""
        if not self._config.enabled:
            return
        if not self._config.allowed_envs:
            return
        current = self.current_env
        if current not in self._config.allowed_envs:
            allowed = ", ".join(self._config.allowed_envs)
            raise EnvironmentMismatchError(
                f"Environment '{current}' is not in the allowed list: [{allowed}]. "
                f"Set {self._config.env_var} to one of the allowed values."
            )

    def run(self, fn, *args, **kwargs):
        """Check environment then delegate to *fn*."""
        self.check()
        return fn(*args, **kwargs)
