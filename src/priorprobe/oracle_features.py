from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from priorprobe.geometry_features import (
    build_geometry_feature,
    combine_appearance_and_geometry,
    compute_silhouette_stats,
)
from priorprobe.features import FeatureExtractorConfig, extract_image_features, list_render_images


def build_feature_config(
    backend: str,
    *,
    model_name: str | None = None,
    pretrained: str | None = None,
    device: str = "cuda",
    render_count: int = 8,
) -> FeatureExtractorConfig:
    normalized = str(backend).strip().lower()
    if normalized == "mean_rgb":
        return FeatureExtractorConfig(
            model_name="mean_rgb",
            pretrained="",
            device=device,
            render_count=render_count,
            allow_fallback=False,
        )
    if normalized == "clip":
        return FeatureExtractorConfig(
            model_name=model_name or "ViT-B-32",
            pretrained=pretrained or "laion2b_s34b_b79k",
            device=device,
            render_count=render_count,
            allow_fallback=False,
        )
    if normalized == "clip_geom":
        return FeatureExtractorConfig(
            model_name=model_name or "ViT-B-32",
            pretrained=pretrained or "laion2b_s34b_b79k",
            device=device,
            render_count=render_count,
            allow_fallback=False,
        )
    raise ValueError(f"Unsupported feature backend: {backend}")


def feature_output_name(backend: str) -> str:
    normalized = str(backend).strip().lower()
    if normalized not in {"mean_rgb", "clip", "clip_geom"}:
        raise ValueError(f"Unsupported feature backend: {backend}")
    return f"query_feature_{normalized}.npy"


def _resolve_path(scene_root: Path, path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else scene_root / path


def _relative_to_scene(scene_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(scene_root))
    except ValueError:
        return str(path)


def _appearance_feature(
    crop_paths: list[Path],
    *,
    backend: str,
    config: FeatureExtractorConfig,
) -> np.ndarray:
    normalized = str(backend).strip().lower()
    if normalized == "mean_rgb":
        return extract_image_features(crop_paths, config=config)
    if normalized in {"clip", "clip_geom"}:
        return extract_image_features(crop_paths, config=config)
    raise ValueError(f"Unsupported feature backend: {backend}")


def _query_geometry_stats(
    *,
    scene_root: Path,
    crop_dir: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    crop_paths = list_render_images(crop_dir)
    if not crop_paths:
        raise ValueError(f"No crop images found in {crop_dir}")
    size_xyz = np.asarray(payload.get("sizes"), dtype=np.float32)
    if size_xyz.shape != (3,):
        raise ValueError(f"oracle target sizes are required for clip_geom: {payload}")
    silhouette_stats = compute_silhouette_stats(
        crop_paths,
        full_image_dir=scene_root / "images",
    )
    geometry_feature = build_geometry_feature(size_xyz, silhouette_stats)
    return {
        "size_xyz": size_xyz.tolist(),
        "silhouette_stats": silhouette_stats.to_dict(),
        "geometry_feature": geometry_feature.tolist(),
    }


def _write_feature(
    scene_root: Path,
    payload: dict[str, Any],
    *,
    backend: str,
    crop_dir: Path,
    output_path: Path,
    config: FeatureExtractorConfig,
    overwrite: bool,
) -> tuple[Path, dict[str, Any] | None]:
    if output_path.exists() and not overwrite:
        return output_path, payload.get("geometry_stats")
    crop_paths = list_render_images(crop_dir)
    if not crop_paths:
        raise ValueError(f"No crop images found in {crop_dir}")
    feature = _appearance_feature(crop_paths, backend=backend, config=config)
    geometry_stats_payload: dict[str, Any] | None = None
    if str(backend).strip().lower() == "clip_geom":
        geometry_stats_payload = _query_geometry_stats(
            scene_root=scene_root,
            crop_dir=crop_dir,
            payload=payload,
        )
        geometry_feature = np.asarray(geometry_stats_payload["geometry_feature"], dtype=np.float32)
        feature = combine_appearance_and_geometry(feature, geometry_feature)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, feature.astype(np.float32))
    return output_path, geometry_stats_payload


def build_single_target_feature(
    scene_root: Path,
    *,
    backend: str,
    model_name: str | None = None,
    pretrained: str | None = None,
    device: str = "cuda",
    render_count: int = 8,
    overwrite: bool = False,
) -> Path:
    target_path = scene_root / "oracle" / "target.json"
    payload = json.loads(target_path.read_text(encoding="utf-8"))
    crop_dir = _resolve_path(scene_root, str(payload.get("crop_dir", "oracle/crops")))
    output_path = scene_root / "oracle" / feature_output_name(backend)
    config = build_feature_config(
        backend,
        model_name=model_name,
        pretrained=pretrained,
        device=device,
        render_count=render_count,
    )
    _, geometry_stats = _write_feature(
        scene_root,
        payload,
        backend=backend,
        crop_dir=crop_dir,
        output_path=output_path,
        config=config,
        overwrite=overwrite,
    )
    query_feature_paths = dict(payload.get("query_feature_paths", {}))
    query_feature_paths[str(backend)] = _relative_to_scene(scene_root, output_path)
    payload["query_feature_paths"] = query_feature_paths
    if geometry_stats is not None:
        payload["geometry_stats"] = geometry_stats
    if str(backend).lower() == "mean_rgb":
        payload["query_feature_path"] = query_feature_paths[str(backend)]
    target_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def build_multi_target_features(
    scene_root: Path,
    *,
    backend: str,
    model_name: str | None = None,
    pretrained: str | None = None,
    device: str = "cuda",
    render_count: int = 8,
    overwrite: bool = False,
) -> list[Path]:
    targets_path = scene_root / "oracle" / "targets.json"
    payload = json.loads(targets_path.read_text(encoding="utf-8"))
    config = build_feature_config(
        backend,
        model_name=model_name,
        pretrained=pretrained,
        device=device,
        render_count=render_count,
    )
    output_paths: list[Path] = []
    for item in payload:
        object_id = str(item["object_id"])
        crop_dir = _resolve_path(scene_root, str(item["crop_dir"]))
        output_path = scene_root / "oracle" / "objects" / object_id / feature_output_name(backend)
        _, geometry_stats = _write_feature(
            scene_root,
            item,
            backend=backend,
            crop_dir=crop_dir,
            output_path=output_path,
            config=config,
            overwrite=overwrite,
        )
        query_feature_paths = dict(item.get("query_feature_paths", {}))
        query_feature_paths[str(backend)] = _relative_to_scene(scene_root, output_path)
        item["query_feature_paths"] = query_feature_paths
        if geometry_stats is not None:
            item["geometry_stats"] = geometry_stats
        output_paths.append(output_path)
    targets_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_paths


def build_oracle_query_features(
    scene_root: Path,
    *,
    backend: str,
    model_name: str | None = None,
    pretrained: str | None = None,
    device: str = "cuda",
    render_count: int = 8,
    overwrite: bool = False,
) -> list[Path]:
    outputs: list[Path] = []
    target_path = scene_root / "oracle" / "target.json"
    targets_path = scene_root / "oracle" / "targets.json"
    if target_path.exists():
        outputs.append(
            build_single_target_feature(
                scene_root,
                backend=backend,
                model_name=model_name,
                pretrained=pretrained,
                device=device,
                render_count=render_count,
                overwrite=overwrite,
            )
        )
    if targets_path.exists():
        outputs.extend(
            build_multi_target_features(
                scene_root,
                backend=backend,
                model_name=model_name,
                pretrained=pretrained,
                device=device,
                render_count=render_count,
                overwrite=overwrite,
            )
        )
    if not outputs:
        raise FileNotFoundError(f"No oracle target metadata found under {scene_root / 'oracle'}")
    return outputs
