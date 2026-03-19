from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import yaml
from plyfile import PlyData, PlyElement

from priorprobe.features import FeatureExtractorConfig, extract_image_features
from priorprobe.geometry_features import (
    build_geometry_feature,
    combine_appearance_and_geometry,
    compute_silhouette_stats,
)
from priorprobe.prior_library.library import PriorEntry, PriorLibrary
from priorprobe.prior_library.metadata import PriorMetadata


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
SH_C0 = 0.28209479177387814
FLOOR_SUPPORTED_CATEGORIES = {"chair", "sofa", "table", "lamp"}


@dataclass(slots=True)
class StagedShapeSplatAsset:
    object_id: str
    category: str
    gaussian_path: Path
    canonical_seed_center_path: Path | None
    canonical_seed_floor_path: Path | None
    canonical_metadata_path: Path | None
    render_dir: Path | None
    feature_path: Path | None
    render_count: int
    feature_dim: int | None
    feature_backend: str
    source_split: str | None
    geometry_stats: dict[str, Any] | None = None


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def resolve_path(root: Path, path_value: str | None) -> Path | None:
    if path_value is None:
        return None
    path = Path(path_value)
    return path if path.is_absolute() else root / path


def _feature_backend(config: dict[str, Any]) -> str:
    asset_prep = config.get("asset_prep", {})
    return str(asset_prep.get("feature_backend", "open_clip"))


def _feature_config(config: dict[str, Any]) -> FeatureExtractorConfig:
    asset_prep = config.get("asset_prep", {})
    backend = _feature_backend(config)
    model_name = "mean_rgb" if backend == "fallback" else str(asset_prep.get("feature_model_name", "ViT-B-32"))
    return FeatureExtractorConfig(
        model_name=model_name,
        pretrained=str(asset_prep.get("feature_pretrained", "laion2b_s34b_b79k")),
        device=str(asset_prep.get("device", "cuda")),
        render_count=int(asset_prep.get("render_sample_count", 8)),
        allow_fallback=bool(asset_prep.get("allow_fallback", True)),
    )


def resolve_render_dir(root: Path, item: dict[str, Any]) -> Path | None:
    if item.get("render_dir") is None:
        return None
    return resolve_path(root, item.get("render_dir"))


def _iter_render_candidates(root: Path, item: dict[str, Any]) -> Iterable[Path]:
    explicit_paths = item.get("source_render_paths")
    if explicit_paths:
        for path_value in explicit_paths:
            path = resolve_path(root, str(path_value))
            if path is not None:
                yield path
        return

    source_render_dir = resolve_path(root, item.get("source_render_dir"))
    if source_render_dir is None:
        return

    render_glob = str(item.get("source_render_glob", "*"))
    for path in sorted(source_render_dir.glob(render_glob)):
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            yield path


def _copy_file(source_path: Path, destination_path: Path, *, overwrite: bool) -> None:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if destination_path.exists() and not overwrite:
        return
    if source_path.resolve() == destination_path.resolve():
        return
    shutil.copy2(source_path, destination_path)


def _write_structured_ply(path: Path, data: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    PlyData([PlyElement.describe(data, "vertex")]).write(path)


def _detect_asset_format(vertex: np.ndarray) -> str:
    names = set(vertex.dtype.names or ())
    if {"opacity", "f_dc_0", "scale_0", "rot_0"}.issubset(names):
        return "gaussian"
    if {"red", "green", "blue"}.issubset(names):
        return "point_cloud"
    raise ValueError(f"Unsupported PLY schema: {vertex.dtype.names}")


def _sh2rgb(sh: np.ndarray) -> np.ndarray:
    return np.clip(sh * SH_C0 + 0.5, 0.0, 1.0)


def _build_point_cloud_vertex_from_structured(vertex: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    xyz = np.stack([vertex["x"], vertex["y"], vertex["z"]], axis=1).astype(np.float32)
    dtype = [
        ("x", "f4"),
        ("y", "f4"),
        ("z", "f4"),
        ("nx", "f4"),
        ("ny", "f4"),
        ("nz", "f4"),
        ("red", "u1"),
        ("green", "u1"),
        ("blue", "u1"),
    ]
    output = np.empty(xyz.shape[0], dtype=dtype)
    output["x"] = xyz[:, 0]
    output["y"] = xyz[:, 1]
    output["z"] = xyz[:, 2]

    asset_format = _detect_asset_format(vertex)
    if asset_format == "gaussian":
        output["nx"] = 0.0
        output["ny"] = 0.0
        output["nz"] = 0.0
        colors = np.stack([vertex["f_dc_0"], vertex["f_dc_1"], vertex["f_dc_2"]], axis=1).astype(np.float32)
        colors = np.round(_sh2rgb(colors) * 255.0).astype(np.uint8)
        output["red"] = colors[:, 0]
        output["green"] = colors[:, 1]
        output["blue"] = colors[:, 2]
    else:
        output["nx"] = vertex["nx"] if "nx" in (vertex.dtype.names or ()) else 0.0
        output["ny"] = vertex["ny"] if "ny" in (vertex.dtype.names or ()) else 0.0
        output["nz"] = vertex["nz"] if "nz" in (vertex.dtype.names or ()) else 0.0
        output["red"] = vertex["red"]
        output["green"] = vertex["green"]
        output["blue"] = vertex["blue"]
    return xyz, output


def _support_type_for_category(category: str, explicit_value: str | None = None) -> str:
    if explicit_value:
        return str(explicit_value)
    return "floor" if str(category) in FLOOR_SUPPORTED_CATEGORIES else "unknown"


def _canonical_seed_paths(root: Path, item: dict[str, Any], gaussian_path: Path) -> tuple[Path, Path, Path]:
    center_path = resolve_path(root, item.get("canonical_seed_center_path"))
    floor_path = resolve_path(root, item.get("canonical_seed_floor_path"))
    metadata_path = resolve_path(root, item.get("canonical_metadata_path"))
    asset_dir = gaussian_path.parent
    return (
        center_path or (asset_dir / "canonical_seed_center.ply"),
        floor_path or (asset_dir / "canonical_seed_floor.ply"),
        metadata_path or (asset_dir / "canonical_metadata.json"),
    )


def _maybe_relativize(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _load_or_build_canonical_metadata(
    gaussian_path: Path,
    *,
    center_seed_path: Path,
    floor_seed_path: Path,
    metadata_path: Path,
    support_type: str,
    overwrite: bool,
) -> dict[str, Any]:
    if (
        not overwrite
        and center_seed_path.exists()
        and floor_seed_path.exists()
        and metadata_path.exists()
    ):
        return json.loads(metadata_path.read_text(encoding="utf-8"))

    ply = PlyData.read(gaussian_path)
    vertex = np.array(ply["vertex"].data, copy=True)
    xyz, point_cloud_vertex = _build_point_cloud_vertex_from_structured(vertex)
    bbox_min = xyz.min(axis=0).astype(np.float32)
    bbox_max = xyz.max(axis=0).astype(np.float32)
    bbox_size = np.maximum(bbox_max - bbox_min, 1e-6).astype(np.float32)
    bbox_center = ((bbox_min + bbox_max) * 0.5).astype(np.float32)
    bottom_center = np.asarray([bbox_center[0], bbox_center[1], bbox_min[2]], dtype=np.float32)

    center_vertex = np.array(point_cloud_vertex, copy=True)
    center_vertex["x"] = xyz[:, 0] - bbox_center[0]
    center_vertex["y"] = xyz[:, 1] - bbox_center[1]
    center_vertex["z"] = xyz[:, 2] - bbox_center[2]
    _write_structured_ply(center_seed_path, center_vertex)

    floor_vertex = np.array(point_cloud_vertex, copy=True)
    floor_vertex["x"] = xyz[:, 0] - bottom_center[0]
    floor_vertex["y"] = xyz[:, 1] - bottom_center[1]
    floor_vertex["z"] = xyz[:, 2] - bottom_center[2]
    _write_structured_ply(floor_seed_path, floor_vertex)

    metadata = {
        "support_type": support_type,
        "up_axis": "z",
        "bbox_min": bbox_min.tolist(),
        "bbox_max": bbox_max.tolist(),
        "bbox_center": bbox_center.tolist(),
        "bbox_size": bbox_size.tolist(),
        "anchor_center": bbox_center.tolist(),
        "anchor_bottom_center": bottom_center.tolist(),
        "canonical_seed_center_path": str(center_seed_path),
        "canonical_seed_floor_path": str(floor_seed_path),
        "default_anchor_mode": "floor" if support_type == "floor" else "center",
    }
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def _stage_renders(
    render_paths: list[Path],
    destination_dir: Path | None,
    *,
    overwrite: bool,
) -> tuple[Path | None, list[Path]]:
    if destination_dir is None:
        return None, render_paths

    destination_dir.mkdir(parents=True, exist_ok=True)
    staged_paths: list[Path] = []
    for index, path in enumerate(render_paths):
        suffix = path.suffix.lower() if path.suffix else ".png"
        destination_path = destination_dir / f"{index:03d}{suffix}"
        _copy_file(path, destination_path, overwrite=overwrite)
        staged_paths.append(destination_path)
    return destination_dir, staged_paths


def _extract_feature(
    render_paths: list[Path],
    feature_path: Path | None,
    *,
    backend: str,
    scale_meters: tuple[float, float, float] | None,
    config: FeatureExtractorConfig,
    overwrite: bool,
) -> tuple[Path | None, int | None, str, dict[str, Any] | None]:
    normalized_backend = str(backend).strip().lower()
    backend_name = "fallback" if config.model_name == "mean_rgb" else normalized_backend
    if feature_path is None:
        return None, None, backend_name, None

    feature_path.parent.mkdir(parents=True, exist_ok=True)
    if feature_path.exists() and not overwrite:
        payload = np.load(feature_path)
        return feature_path, int(payload.reshape(-1).shape[0]), backend_name, None

    feature = extract_image_features(render_paths, config=config)
    geometry_stats: dict[str, Any] | None = None
    if normalized_backend == "clip_geom":
        if scale_meters is None:
            raise ValueError("clip_geom prior features require scale_meters")
        silhouette_stats = compute_silhouette_stats(render_paths)
        geometry_feature = build_geometry_feature(scale_meters, silhouette_stats)
        feature = combine_appearance_and_geometry(feature, geometry_feature)
        geometry_stats = {
            "size_xyz": [float(value) for value in scale_meters],
            "silhouette_stats": silhouette_stats.to_dict(),
            "geometry_feature": geometry_feature.tolist(),
        }
    np.save(feature_path, feature.astype(np.float32))
    return feature_path, int(feature.reshape(-1).shape[0]), backend_name, geometry_stats


def stage_shapesplat_assets(
    config: dict[str, Any],
    *,
    root: Path,
    overwrite: bool = False,
) -> list[StagedShapeSplatAsset]:
    staged: list[StagedShapeSplatAsset] = []
    feature_config = _feature_config(config)
    feature_backend = _feature_backend(config)
    min_render_count = int(config.get("asset_prep", {}).get("min_render_count", feature_config.render_count))

    for item in config.get("library", {}).get("default_objects", []):
        object_id = str(item["object_id"])
        category = str(item["category"])
        gaussian_path = resolve_path(root, item.get("gaussian_path"))
        if gaussian_path is None:
            raise ValueError(f"gaussian_path is required for {object_id}")

        source_gaussian_path = resolve_path(root, item.get("source_gaussian_path") or item.get("source_asset_path"))
        if source_gaussian_path is not None:
            if not source_gaussian_path.exists():
                raise FileNotFoundError(f"source_gaussian_path missing for {object_id}: {source_gaussian_path}")
            _copy_file(source_gaussian_path, gaussian_path, overwrite=overwrite)
        elif not gaussian_path.exists():
            raise FileNotFoundError(f"gaussian_path missing for {object_id}: {gaussian_path}")

        support_type = _support_type_for_category(category, item.get("support_type"))
        center_seed_path, floor_seed_path, canonical_metadata_path = _canonical_seed_paths(root, item, gaussian_path)
        canonical_metadata = _load_or_build_canonical_metadata(
            gaussian_path,
            center_seed_path=center_seed_path,
            floor_seed_path=floor_seed_path,
            metadata_path=canonical_metadata_path,
            support_type=support_type,
            overwrite=overwrite,
        )
        item["support_type"] = support_type
        item["canonical_seed_center_path"] = _maybe_relativize(center_seed_path, root)
        item["canonical_seed_floor_path"] = _maybe_relativize(floor_seed_path, root)
        item["canonical_metadata_path"] = _maybe_relativize(canonical_metadata_path, root)
        item["canonical_bbox_size"] = canonical_metadata["bbox_size"]
        item["canonical_bbox_center"] = canonical_metadata["bbox_center"]
        item["canonical_bbox_min"] = canonical_metadata["bbox_min"]
        item["canonical_bbox_max"] = canonical_metadata["bbox_max"]
        item["canonical_anchor_center"] = canonical_metadata["anchor_center"]
        item["canonical_anchor_bottom_center"] = canonical_metadata["anchor_bottom_center"]
        item["canonical_anchor_mode"] = canonical_metadata["default_anchor_mode"]

        source_render_paths = list(_iter_render_candidates(root, item))
        render_dir = resolve_render_dir(root, item)
        staged_render_dir, staged_render_paths = _stage_renders(
            source_render_paths,
            render_dir,
            overwrite=overwrite,
        )

        render_count = len(staged_render_paths)
        if render_count < min_render_count:
            raise ValueError(
                f"{object_id} needs at least {min_render_count} renders, found {render_count}"
            )

        feature_path = resolve_path(root, item.get("feature_path"))
        scale_meters = (
            tuple(float(value) for value in item.get("scale_meters", []))
            if item.get("scale_meters")
            else None
        )
        staged_feature_path, feature_dim, staged_feature_backend, geometry_stats = _extract_feature(
            staged_render_paths,
            feature_path,
            backend=feature_backend,
            scale_meters=scale_meters,
            config=feature_config,
            overwrite=overwrite,
        )
        if geometry_stats is not None:
            item["geometry_stats"] = geometry_stats

        staged.append(
            StagedShapeSplatAsset(
                object_id=object_id,
                category=category,
                gaussian_path=gaussian_path,
                canonical_seed_center_path=center_seed_path,
                canonical_seed_floor_path=floor_seed_path,
                canonical_metadata_path=canonical_metadata_path,
                render_dir=staged_render_dir,
                feature_path=staged_feature_path,
                render_count=render_count,
                feature_dim=feature_dim,
                feature_backend=staged_feature_backend,
                source_split=str(item.get("source_split")) if item.get("source_split") else None,
                geometry_stats=geometry_stats,
            )
        )

    return staged


def summarize_staged_assets(results: list[StagedShapeSplatAsset]) -> str:
    payload = [
        {
            "object_id": item.object_id,
            "category": item.category,
            "gaussian_path": str(item.gaussian_path),
            "render_dir": str(item.render_dir) if item.render_dir else None,
            "feature_path": str(item.feature_path) if item.feature_path else None,
            "render_count": item.render_count,
            "feature_dim": item.feature_dim,
            "feature_backend": item.feature_backend,
            "source_split": item.source_split,
            "geometry_stats": item.geometry_stats,
        }
        for item in results
    ]
    return json.dumps(payload, indent=2)


def build_prior_library(config: dict[str, Any], *, root: Path) -> PriorLibrary:
    library = PriorLibrary()
    for item in config.get("library", {}).get("default_objects", []):
        gaussian_path = resolve_path(root, item.get("gaussian_path"))
        feature_path = resolve_path(root, item.get("feature_path"))
        render_dir = resolve_render_dir(root, item)
        render_count = 0 if render_dir is None or not render_dir.exists() else sum(
            1 for path in render_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        )
        feature_dim = None
        if feature_path is not None and feature_path.exists():
            payload = np.load(feature_path)
            feature_dim = int(payload.reshape(-1).shape[0])
        canonical_seed_center_path, canonical_seed_floor_path, canonical_metadata_path = _canonical_seed_paths(
            root,
            item,
            gaussian_path,
        )
        support_type = _support_type_for_category(category=str(item["category"]), explicit_value=item.get("support_type"))
        canonical_metadata = _load_or_build_canonical_metadata(
            gaussian_path,
            center_seed_path=canonical_seed_center_path,
            floor_seed_path=canonical_seed_floor_path,
            metadata_path=canonical_metadata_path,
            support_type=support_type,
            overwrite=False,
        )

        metadata = PriorMetadata(
            category=str(item["category"]),
            source=str(config.get("library", {}).get("source", "unknown")),
            scale_meters=tuple(float(value) for value in item["scale_meters"])
            if item.get("scale_meters")
            else None,
            tags=tuple(str(tag) for tag in item.get("tags", [])),
            extras={
                "source_split": item.get("source_split"),
                "render_dir": str(render_dir) if render_dir else None,
                "render_count": render_count,
                "feature_dim": feature_dim,
                "feature_backend": _feature_backend(config),
                "geometry_stats": item.get("geometry_stats"),
                "support_type": support_type,
                "canonical_seed_center_path": str(canonical_seed_center_path),
                "canonical_seed_floor_path": str(canonical_seed_floor_path),
                "canonical_metadata_path": str(canonical_metadata_path),
                "canonical_anchor_mode": item.get("canonical_anchor_mode", canonical_metadata.get("default_anchor_mode")),
                "canonical_bbox_size": item.get("canonical_bbox_size", canonical_metadata.get("bbox_size")),
                "canonical_bbox_center": item.get("canonical_bbox_center", canonical_metadata.get("bbox_center")),
                "canonical_bbox_min": item.get("canonical_bbox_min", canonical_metadata.get("bbox_min")),
                "canonical_bbox_max": item.get("canonical_bbox_max", canonical_metadata.get("bbox_max")),
                "canonical_anchor_center": item.get("canonical_anchor_center", canonical_metadata.get("anchor_center")),
                "canonical_anchor_bottom_center": item.get("canonical_anchor_bottom_center", canonical_metadata.get("anchor_bottom_center")),
            },
        )
        if gaussian_path is None:
            raise ValueError(f"gaussian_path is required for {item['object_id']}")

        library.add_entry(
            PriorEntry(
                object_id=str(item["object_id"]),
                category=str(item["category"]),
                gaussian_path=gaussian_path,
                feature_path=feature_path,
                metadata=metadata,
            )
        )

    return library
