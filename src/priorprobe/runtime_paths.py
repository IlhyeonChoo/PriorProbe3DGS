from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


PROJECT_CONFIG_PATH = Path("configs/base/project.yaml")


@lru_cache(maxsize=None)
def _load_project_config(path: str) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        return {}
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def load_project_runtime(root: Path) -> dict[str, Any]:
    config_path = (root / PROJECT_CONFIG_PATH).resolve()
    payload = _load_project_config(str(config_path))
    runtime = payload.get("runtime", {})
    return dict(runtime) if isinstance(runtime, dict) else {}


def resolve_runtime_path(root: Path, key: str, *, fallback: str) -> Path:
    runtime = load_project_runtime(root)
    raw_value = runtime.get(key, fallback)
    path = Path(str(raw_value))
    return path if path.is_absolute() else root / path


def to_repo_relative_path(path: Path, *, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)
