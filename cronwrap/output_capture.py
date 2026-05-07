"""Capture stdout/stderr from a subprocess command into structured output."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CaptureConfig:
    """Configuration for output capture behaviour."""
    max_bytes: int = 1_048_576  # 1 MiB default cap
    capture_stdout: bool = True
    capture_stderr: bool = True
    encoding: str = "utf-8"
    errors: str = "replace"

    def __post_init__(self) -> None:
        if self.max_bytes < 0:
            raise ValueError("max_bytes must be >= 0")


@dataclass
class CapturedOutput:
    """Holds the result of a captured subprocess run."""
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    truncated: bool = False

    def combined(self) -> str:
        """Return stdout and stderr joined by a newline."""
        parts = [p for p in (self.stdout, self.stderr) if p]
        return "\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "truncated": self.truncated,
        }


class OutputCapture:
    """Runs a shell command and captures its output according to *CaptureConfig*."""

    def __init__(self, config: Optional[CaptureConfig] = None) -> None:
        self.config = config or CaptureConfig()

    def run(self, command: str) -> CapturedOutput:
        """Execute *command* in a shell and return a :class:`CapturedOutput`."""
        cfg = self.config
        stdout_pipe = subprocess.PIPE if cfg.capture_stdout else None
        stderr_pipe = subprocess.PIPE if cfg.capture_stderr else None

        result = subprocess.run(
            command,
            shell=True,
            stdout=stdout_pipe,
            stderr=stderr_pipe,
        )

        def _decode(raw: Optional[bytes]) -> str:
            if raw is None:
                return ""
            return raw.decode(cfg.encoding, errors=cfg.errors)

        stdout_text = _decode(result.stdout)
        stderr_text = _decode(result.stderr)

        truncated = False
        if cfg.max_bytes > 0:
            if len(stdout_text.encode(cfg.encoding)) > cfg.max_bytes:
                stdout_text = stdout_text.encode(cfg.encoding)[: cfg.max_bytes].decode(
                    cfg.encoding, errors=cfg.errors
                )
                truncated = True
            if len(stderr_text.encode(cfg.encoding)) > cfg.max_bytes:
                stderr_text = stderr_text.encode(cfg.encoding)[: cfg.max_bytes].decode(
                    cfg.encoding, errors=cfg.errors
                )
                truncated = True

        return CapturedOutput(
            stdout=stdout_text,
            stderr=stderr_text,
            exit_code=result.returncode,
            truncated=truncated,
        )
