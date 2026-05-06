"""TOML/JSON file-based config loading for cronwrap."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore

from cronwrap.config import CronJobConfig, load_from_env


def _load_toml(path: Path) -> Dict[str, Any]:
    if tomllib is None:
        raise RuntimeError(
            "TOML support requires Python 3.11+ or the 'tomli' package."
        )
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open() as fh:
        return json.load(fh)


def load_config_file(path: str | Path) -> Dict[str, Any]:
    """Load raw config dict from a TOML or JSON file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")
    suffix = p.suffix.lower()
    if suffix == ".toml":
        return _load_toml(p)
    if suffix == ".json":
        return _load_json(p)
    raise ValueError(f"Unsupported config format: '{suffix}'. Use .toml or .json.")


def build_config(
    file_path: str | Path | None = None,
    env_prefix: str = "CRONWRAP",
    overrides: Dict[str, Any] | None = None,
) -> CronJobConfig:
    """Build a :class:`CronJobConfig` by merging (in priority order):

    1. File-based config (lowest priority)
    2. Environment variables
    3. Explicit *overrides* dict (highest priority)
    """
    merged: Dict[str, Any] = {}

    if file_path is not None:
        merged.update(load_config_file(file_path))

    merged.update(load_from_env(prefix=env_prefix))

    if overrides:
        merged.update(overrides)

    return CronJobConfig(**merged)
