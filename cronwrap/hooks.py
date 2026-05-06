"""Pre/post command hook execution for cron jobs."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class HookConfig:
    """Configuration for pre/post hooks attached to a cron job."""

    pre_hooks: List[str] = field(default_factory=list)
    post_hooks: List[str] = field(default_factory=list)
    timeout: int = 30  # seconds per hook
    stop_on_failure: bool = True

    def __post_init__(self) -> None:
        if self.timeout <= 0:
            raise ValueError("timeout must be a positive integer")


@dataclass
class HookResult:
    """Result of a single hook execution."""

    command: str
    exit_code: int
    stdout: str
    stderr: str

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0


class HookRunner:
    """Runs pre/post hooks and collects results."""

    def __init__(self, config: HookConfig) -> None:
        self._config = config

    def _run_hook(self, command: str) -> HookResult:
        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self._config.timeout,
            )
            return HookResult(
                command=command,
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
        except subprocess.TimeoutExpired:
            return HookResult(
                command=command,
                exit_code=1,
                stdout="",
                stderr=f"Hook timed out after {self._config.timeout}s",
            )

    def run_pre_hooks(self) -> List[HookResult]:
        """Execute all pre-hooks; stop early on failure if configured."""
        return self._run_sequence(self._config.pre_hooks)

    def run_post_hooks(self) -> List[HookResult]:
        """Execute all post-hooks; stop early on failure if configured."""
        return self._run_sequence(self._config.post_hooks)

    def _run_sequence(self, commands: List[str]) -> List[HookResult]:
        results: List[HookResult] = []
        for cmd in commands:
            result = self._run_hook(cmd)
            results.append(result)
            if not result.succeeded and self._config.stop_on_failure:
                break
        return results
