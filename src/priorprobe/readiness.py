from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from priorprobe.datasets import load_dataset_spec, resolve_dataset_scene, validate_scene_layout


@dataclass(slots=True)
class PriorAssetCheck:
    object_id: str
    gaussian_path: Path
    gaussian_exists: bool
    feature_path: Path | None
    feature_exists: bool | None
    placeholder: bool
    blocking_issues: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return not self.blocking_issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "gaussian_path": str(self.gaussian_path),
            "gaussian_exists": self.gaussian_exists,
            "feature_path": str(self.feature_path) if self.feature_path else None,
            "feature_exists": self.feature_exists,
            "placeholder": self.placeholder,
            "ready": self.ready,
            "blocking_issues": list(self.blocking_issues),
            "warnings": list(self.warnings),
        }


@dataclass(slots=True)
class DatasetSceneCheck:
    dataset_name: str
    scene_id: str
    source_path: Path
    ready: bool
    blocking_issues: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "scene_id": self.scene_id,
            "source_path": str(self.source_path),
            "ready": self.ready,
            "blocking_issues": list(self.blocking_issues),
            "warnings": list(self.warnings),
        }


def _resolve_path(root: Path, path_value: str | None) -> Path | None:
    if path_value is None:
        return None
    path = Path(path_value)
    return path if path.is_absolute() else root / path


def check_prior_assets(
    config_path: Path,
    *,
    root: Path,
    require_features: bool = False,
) -> list[PriorAssetCheck]:
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    checks: list[PriorAssetCheck] = []

    for item in payload["library"].get("default_objects", []):
        gaussian_path = _resolve_path(root, item["gaussian_path"])
        feature_path = _resolve_path(root, item.get("feature_path"))
        gaussian_exists = gaussian_path.exists() if gaussian_path is not None else False
        feature_exists = feature_path.exists() if feature_path is not None else None
        placeholder = bool(item.get("placeholder", False))

        blocking_issues: list[str] = []
        warnings: list[str] = []

        if gaussian_path is None or not gaussian_exists:
            blocking_issues.append(f"missing gaussian_path for {item['object_id']}: {item['gaussian_path']}")
        if placeholder:
            blocking_issues.append(f"{item['object_id']} is still marked as a placeholder prior")
        if require_features and feature_path is not None and not feature_exists:
            blocking_issues.append(f"missing feature_path for {item['object_id']}: {item['feature_path']}")
        elif feature_path is not None and not feature_exists:
            warnings.append(f"feature_path missing for {item['object_id']}: {item['feature_path']}")

        checks.append(
            PriorAssetCheck(
                object_id=str(item["object_id"]),
                gaussian_path=gaussian_path if gaussian_path is not None else root / item["gaussian_path"],
                gaussian_exists=gaussian_exists,
                feature_path=feature_path,
                feature_exists=feature_exists,
                placeholder=placeholder,
                blocking_issues=tuple(blocking_issues),
                warnings=tuple(warnings),
            )
        )

    return checks


def check_dataset_scene(
    config_path: Path,
    *,
    root: Path,
    scene_id: str | None = None,
    root_override: Path | None = None,
) -> DatasetSceneCheck:
    spec = load_dataset_spec(config_path, root=root)
    scene = resolve_dataset_scene(spec, scene_id=scene_id, root_override=root_override)
    ready, blocking_issues = validate_scene_layout(scene)
    warnings: list[str] = []

    scene_meta = scene.source_path / "scene_meta.json"
    if not scene_meta.exists():
        warnings.append(f"missing scene_meta.json: {scene_meta}")

    return DatasetSceneCheck(
        dataset_name=scene.dataset_name,
        scene_id=scene.scene_id,
        source_path=scene.source_path,
        ready=ready and not warnings,
        blocking_issues=tuple(blocking_issues),
        warnings=tuple(warnings),
    )
