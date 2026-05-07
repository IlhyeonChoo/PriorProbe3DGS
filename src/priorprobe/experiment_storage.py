from __future__ import annotations

import re
from pathlib import Path


GAUSSIAN_DIRECT_PREFIX = "gaussian_direct_"
DATED_EXPERIMENT_RE = re.compile(r"^\d{2}-\d{2}-.+-\d{4}$")


def storage_experiment_name(experiment_name: str, *, outputs_root: Path | None = None) -> str:
    name = str(experiment_name).strip()
    if not name:
        return name
    if DATED_EXPERIMENT_RE.fullmatch(name):
        return name
    root_name = Path(outputs_root).name if outputs_root is not None else None
    if root_name is None or root_name == "gaussian_direct":
        if name.startswith(GAUSSIAN_DIRECT_PREFIX):
            return name.removeprefix(GAUSSIAN_DIRECT_PREFIX)
    return name


def experiment_storage_dir(outputs_root: Path, bucket: str, experiment_name: str) -> Path:
    return Path(outputs_root) / bucket / storage_experiment_name(experiment_name, outputs_root=outputs_root)


def resolve_experiment_storage_dir(outputs_root: Path, bucket: str, experiment_name: str) -> Path:
    outputs_root = Path(outputs_root)
    primary = experiment_storage_dir(outputs_root, bucket, experiment_name)
    if primary.exists():
        return primary

    original = outputs_root / bucket / str(experiment_name)
    if original.exists():
        return original

    stripped = storage_experiment_name(experiment_name, outputs_root=outputs_root)
    if stripped == experiment_name:
        prefixed = outputs_root / bucket / f"{GAUSSIAN_DIRECT_PREFIX}{experiment_name}"
        if prefixed.exists():
            return prefixed

    return primary
