from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class DatasetSceneOverride:
    """Per-scene overrides on top of a dataset-wide config."""

    scene_id: str
    relative_path: str | None = None
    source_path: str | None = None
    images: str | None = None
    depths: str | None = None
    eval: bool | None = None
    white_background: bool | None = None
    notes: tuple[str, ...] = ()


@dataclass(slots=True)
class DatasetSpec:
    """Resolved dataset specification loaded from YAML."""

    config_path: Path
    name: str
    phase: str | None = None
    root: Path = Path(".")
    format: str = "colmap"
    default_scene_id: str | None = None
    source_path_template: str = "{root}/{scene_id}"
    images: str = "images"
    depths: str = ""
    eval: bool = False
    white_background: bool = False
    notes: tuple[str, ...] = ()
    scenes: dict[str, DatasetSceneOverride] = field(default_factory=dict)


@dataclass(slots=True)
class ResolvedDatasetScene:
    """Concrete scene path and backend-relevant parameters."""

    dataset_name: str
    format: str
    scene_id: str
    source_path: Path
    images: str
    depths: str
    eval: bool
    white_background: bool
    notes: tuple[str, ...] = ()


def _resolve_path(root: Path, path_str: str | None) -> Path | None:
    if path_str is None:
        return None
    path = Path(path_str)
    return path if path.is_absolute() else root / path


def _normalize_notes(payload: Any) -> tuple[str, ...]:
    if payload is None:
        return ()
    if isinstance(payload, str):
        return (payload,)
    return tuple(str(item) for item in payload)


def load_dataset_spec(config_path: Path, *, root: Path) -> DatasetSpec:
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    dataset_payload = payload["dataset"]
    dataset_root = _resolve_path(root, dataset_payload.get("root")) or root

    scenes: dict[str, DatasetSceneOverride] = {}
    for scene_id, scene_payload in (dataset_payload.get("scenes") or {}).items():
        scenes[str(scene_id)] = DatasetSceneOverride(
            scene_id=str(scene_id),
            relative_path=scene_payload.get("relative_path"),
            source_path=str(scene_payload["source_path"]) if scene_payload.get("source_path") is not None else None,
            images=scene_payload.get("images"),
            depths=scene_payload.get("depths"),
            eval=scene_payload.get("eval"),
            white_background=scene_payload.get("white_background"),
            notes=_normalize_notes(scene_payload.get("notes")),
        )

    return DatasetSpec(
        config_path=config_path,
        name=str(dataset_payload["name"]),
        phase=dataset_payload.get("phase"),
        root=dataset_root,
        format=str(dataset_payload.get("format", "colmap")),
        default_scene_id=dataset_payload.get("default_scene_id"),
        source_path_template=str(dataset_payload.get("source_path_template", "{root}/{scene_id}")),
        images=str(dataset_payload.get("images", "images")),
        depths=str(dataset_payload.get("depths", "")),
        eval=bool(dataset_payload.get("eval", False)),
        white_background=bool(dataset_payload.get("white_background", False)),
        notes=_normalize_notes(dataset_payload.get("notes")),
        scenes=scenes,
    )


def resolve_dataset_scene(
    spec: DatasetSpec,
    *,
    scene_id: str | None = None,
    root_override: Path | None = None,
) -> ResolvedDatasetScene:
    dataset_root = root_override.resolve() if root_override else spec.root
    resolved_scene_id = scene_id or spec.default_scene_id
    if resolved_scene_id is None:
        raise ValueError(
            f"dataset {spec.name} requires a scene_id; set dataset.default_scene_id or pass an override"
        )

    scene_override = spec.scenes.get(resolved_scene_id)
    if scene_override and scene_override.source_path is not None:
        source_path = _resolve_path(dataset_root, scene_override.source_path)
    elif scene_override and scene_override.relative_path is not None:
        source_path = dataset_root / scene_override.relative_path
    else:
        source_path = Path(
            spec.source_path_template.format(
                root=str(dataset_root),
                scene_id=resolved_scene_id,
            )
        )
    if not source_path.is_absolute():
        source_path = dataset_root / source_path

    notes = list(spec.notes)
    if scene_override is not None:
        notes.extend(scene_override.notes)

    return ResolvedDatasetScene(
        dataset_name=spec.name,
        format=spec.format,
        scene_id=resolved_scene_id,
        source_path=source_path.resolve(),
        images=scene_override.images if scene_override and scene_override.images is not None else spec.images,
        depths=scene_override.depths if scene_override and scene_override.depths is not None else spec.depths,
        eval=scene_override.eval if scene_override and scene_override.eval is not None else spec.eval,
        white_background=(
            scene_override.white_background
            if scene_override and scene_override.white_background is not None
            else spec.white_background
        ),
        notes=tuple(notes),
    )
