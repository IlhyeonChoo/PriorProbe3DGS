from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from PIL import Image
from plyfile import PlyData

from priorprobe.prior_assets import build_prior_library, stage_shapesplat_assets
from priorprobe.runtime_paths import to_repo_relative_path


SH_C0 = 0.28209479177387814
FLOOR_SUPPORTED_CATEGORIES = {"chair", "sofa", "table", "lamp"}


@dataclass(slots=True)
class ModelNetObjectAsset:
    object_id: str
    split: str
    gaussian_path: Path
    render_dir: Path
    bbox_size: tuple[float, float, float]


def _support_type_for_category(category: str) -> str:
    return "floor" if str(category) in FLOOR_SUPPORTED_CATEGORIES else "unknown"


def list_modelnet_point_clouds(
    zip_path: Path,
    *,
    category: str,
    split: str = "train",
) -> list[tuple[str, str]]:
    with zipfile.ZipFile(zip_path) as archive:
        results: list[tuple[str, str]] = []
        prefix = f"{split}/{category}_"
        for name in sorted(archive.namelist()):
            if not name.endswith("/point_cloud.ply"):
                continue
            if not name.startswith(prefix):
                continue
            parts = Path(name).parts
            if len(parts) < 3:
                continue
            object_id = parts[1]
            results.append((object_id, name))
    return results


def _copy_zip_member(
    archive: zipfile.ZipFile,
    member_name: str,
    destination: Path,
    *,
    overwrite: bool,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not overwrite:
        return
    with archive.open(member_name) as src, destination.open("wb") as dst:
        shutil.copyfileobj(src, dst)


def _rotation_x(angle_rad: float) -> np.ndarray:
    c = np.cos(angle_rad)
    s = np.sin(angle_rad)
    return np.asarray(
        [
            [1.0, 0.0, 0.0],
            [0.0, c, -s],
            [0.0, s, c],
        ],
        dtype=np.float32,
    )


def _rotation_y(angle_rad: float) -> np.ndarray:
    c = np.cos(angle_rad)
    s = np.sin(angle_rad)
    return np.asarray(
        [
            [c, 0.0, s],
            [0.0, 1.0, 0.0],
            [-s, 0.0, c],
        ],
        dtype=np.float32,
    )


def _load_ply_xyz_rgb(path: Path) -> tuple[np.ndarray, np.ndarray]:
    ply = PlyData.read(path)
    vertex = np.array(ply["vertex"].data, copy=False)
    names = set(vertex.dtype.names or ())
    xyz = np.stack([vertex["x"], vertex["y"], vertex["z"]], axis=1).astype(np.float32)
    if {"red", "green", "blue"}.issubset(names):
        rgb = np.stack([vertex["red"], vertex["green"], vertex["blue"]], axis=1).astype(np.float32) / 255.0
    elif {"f_dc_0", "f_dc_1", "f_dc_2"}.issubset(names):
        sh = np.stack([vertex["f_dc_0"], vertex["f_dc_1"], vertex["f_dc_2"]], axis=1).astype(np.float32)
        rgb = np.clip(sh * SH_C0 + 0.5, 0.0, 1.0)
    else:
        raise ValueError(f"Unsupported PLY schema for rendering: {vertex.dtype.names}")
    return xyz, rgb


def _normalized_points(xyz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    bbox_min = xyz.min(axis=0)
    bbox_max = xyz.max(axis=0)
    bbox_size = np.maximum(bbox_max - bbox_min, 1e-6)
    center = (bbox_min + bbox_max) * 0.5
    scale = float(bbox_size.max())
    normalized = (xyz - center) / scale
    return normalized.astype(np.float32), bbox_size.astype(np.float32)


def render_point_cloud_views(
    ply_path: Path,
    render_dir: Path,
    *,
    num_views: int = 8,
    image_size: int = 256,
    point_limit: int = 12000,
    elevation_deg: float = 20.0,
    overwrite: bool = False,
) -> tuple[list[Path], tuple[float, float, float]]:
    xyz, rgb = _load_ply_xyz_rgb(ply_path)
    normalized_xyz, bbox_size = _normalized_points(xyz)
    render_dir.mkdir(parents=True, exist_ok=True)

    if point_limit > 0 and normalized_xyz.shape[0] > point_limit:
        indices = np.linspace(0, normalized_xyz.shape[0] - 1, num=point_limit, dtype=int)
        normalized_xyz = normalized_xyz[indices]
        rgb = rgb[indices]

    radius = 1 if image_size <= 256 else 2
    offsets = np.asarray(
        [(dx, dy) for dy in range(-radius, radius + 1) for dx in range(-radius, radius + 1)],
        dtype=np.int32,
    )
    rgb_uint8 = np.round(np.clip(rgb, 0.0, 1.0) * 255.0).astype(np.uint8)
    elevation = np.deg2rad(float(elevation_deg))
    output_paths: list[Path] = []

    for view_index in range(num_views):
        output_path = render_dir / f"{view_index:03d}.png"
        output_paths.append(output_path)
        if output_path.exists() and not overwrite:
            continue

        azimuth = 2.0 * np.pi * float(view_index) / float(num_views)
        rotation = _rotation_y(azimuth) @ _rotation_x(-elevation)
        view_xyz = normalized_xyz @ rotation.T
        depth = view_xyz[:, 2]
        x = view_xyz[:, 0] * 1.6
        y = view_xyz[:, 1] * 1.6
        u = np.round((x * 0.5 + 0.5) * (image_size - 1)).astype(np.int32)
        v = np.round((0.5 - y * 0.5) * (image_size - 1)).astype(np.int32)

        uu = u[:, None] + offsets[None, :, 0]
        vv = v[:, None] + offsets[None, :, 1]
        valid = (uu >= 0) & (uu < image_size) & (vv >= 0) & (vv < image_size)
        if not np.any(valid):
            Image.new("RGB", (image_size, image_size), color=(255, 255, 255)).save(output_path)
            continue

        base_depth = np.repeat(depth[:, None], offsets.shape[0], axis=1)
        base_rgb = np.repeat(rgb_uint8[:, None, :], offsets.shape[0], axis=1)

        flat = (vv[valid] * image_size + uu[valid]).astype(np.int64)
        flat_depth = base_depth[valid]
        flat_rgb = base_rgb[valid]

        order = np.lexsort((flat_depth, flat))
        flat_sorted = flat[order]
        rgb_sorted = flat_rgb[order]
        keep = np.ones(flat_sorted.shape[0], dtype=bool)
        keep[:-1] = flat_sorted[:-1] != flat_sorted[1:]

        selected_pixels = flat_sorted[keep]
        selected_rgb = rgb_sorted[keep]

        canvas = np.full((image_size, image_size, 3), 255, dtype=np.uint8)
        rows = selected_pixels // image_size
        cols = selected_pixels % image_size
        canvas[rows, cols] = selected_rgb
        Image.fromarray(canvas, mode="RGB").save(output_path)

    return output_paths, tuple(float(value) for value in bbox_size.tolist())


def extract_modelnet_assets(
    zip_path: Path,
    extract_root: Path,
    *,
    category: str,
    split: str = "train",
    max_objects: int = 128,
    num_views: int = 8,
    image_size: int = 256,
    point_limit: int = 12000,
    overwrite: bool = False,
) -> list[ModelNetObjectAsset]:
    results: list[ModelNetObjectAsset] = []
    entries = list_modelnet_point_clouds(zip_path, category=category, split=split)
    if max_objects > 0:
        entries = entries[:max_objects]

    with zipfile.ZipFile(zip_path) as archive:
        for object_id, member_name in entries:
            object_root = extract_root / object_id
            gaussian_path = object_root / "splat.ply"
            render_dir = object_root / "renders"
            _copy_zip_member(archive, member_name, gaussian_path, overwrite=overwrite)
            _, bbox_size = render_point_cloud_views(
                gaussian_path,
                render_dir,
                num_views=num_views,
                image_size=image_size,
                point_limit=point_limit,
                overwrite=overwrite,
            )
            results.append(
                ModelNetObjectAsset(
                    object_id=object_id,
                    split=split,
                    gaussian_path=gaussian_path,
                    render_dir=render_dir,
                    bbox_size=bbox_size,
                )
            )
    return results


def build_modelnet_prior_config(
    assets: list[ModelNetObjectAsset],
    *,
    manifest_path: Path,
    stage_root: Path,
    category: str,
    root: Path | None = None,
    feature_backend: str = "open_clip",
    feature_model_name: str = "ViT-B-32",
    feature_pretrained: str = "laion2b_s34b_b79k",
    render_sample_count: int = 8,
    min_render_count: int = 8,
    allow_fallback: bool = True,
    device: str = "cuda",
) -> dict[str, Any]:
    manifest_path_value = (
        to_repo_relative_path(manifest_path, root=root) if root is not None else str(manifest_path)
    )
    default_objects = []
    for asset in assets:
        default_objects.append(
            {
                "object_id": asset.object_id,
                "category": category,
                "source_split": f"modelnet_{asset.split}",
                "source_gaussian_path": str(asset.gaussian_path),
                "source_render_dir": str(asset.render_dir),
                "gaussian_path": str(stage_root / "assets" / category / asset.object_id / "splat.ply"),
                "canonical_seed_center_path": str(stage_root / "assets" / category / asset.object_id / "canonical_seed_center.ply"),
                "canonical_seed_floor_path": str(stage_root / "assets" / category / asset.object_id / "canonical_seed_floor.ply"),
                "canonical_metadata_path": str(stage_root / "assets" / category / asset.object_id / "canonical_metadata.json"),
                "render_dir": str(stage_root / "assets" / category / asset.object_id / "renders"),
                "feature_path": str(stage_root / "features" / category / f"{asset.object_id}.npy"),
                "scale_meters": [float(value) for value in asset.bbox_size],
                "support_type": _support_type_for_category(category),
                "tags": ["modelnet", category, asset.split],
            }
        )

    return {
        "asset_prep": {
            "feature_backend": feature_backend,
            "feature_model_name": feature_model_name,
            "feature_pretrained": feature_pretrained,
            "render_sample_count": render_sample_count,
            "min_render_count": min_render_count,
            "allow_fallback": allow_fallback,
            "device": device,
        },
        "library": {
            "name": f"shapesplat_modelnet_{category}",
            "source": "shapesplat_modelnet",
            "manifest_path": manifest_path_value,
            "default_objects": default_objects,
        },
    }


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def prepare_modelnet_prior_library(
    *,
    zip_path: Path,
    extract_root: Path,
    stage_root: Path,
    config_out: Path,
    manifest_out: Path,
    category: str = "chair",
    split: str = "train",
    max_objects: int = 128,
    num_views: int = 8,
    image_size: int = 256,
    point_limit: int = 12000,
    overwrite: bool = False,
    feature_backend: str = "fallback",
    feature_model_name: str = "ViT-B-32",
    feature_pretrained: str = "laion2b_s34b_b79k",
    allow_fallback: bool = True,
    device: str = "cuda",
    root: Path,
) -> dict[str, Any]:
    assets = extract_modelnet_assets(
        zip_path,
        extract_root,
        category=category,
        split=split,
        max_objects=max_objects,
        num_views=num_views,
        image_size=image_size,
        point_limit=point_limit,
        overwrite=overwrite,
    )
    config = build_modelnet_prior_config(
        assets,
        manifest_path=manifest_out,
        stage_root=stage_root,
        category=category,
        root=root,
        feature_backend=feature_backend,
        feature_model_name=feature_model_name,
        feature_pretrained=feature_pretrained,
        render_sample_count=num_views,
        min_render_count=min(8, num_views),
        allow_fallback=allow_fallback,
        device=device,
    )
    write_yaml(config_out, config)
    stage_shapesplat_assets(config, root=root, overwrite=overwrite)
    library = build_prior_library(config, root=root)
    library.dump_manifest(manifest_out)

    return {
        "asset_count": len(assets),
        "config_path": str(config_out),
        "manifest_path": str(manifest_out),
        "stage_root": str(stage_root),
        "extract_root": str(extract_root),
        "category": category,
        "split": split,
    }


def build_modelnet_prior_bundle_config(
    assets_by_category: dict[str, list[ModelNetObjectAsset]],
    *,
    manifest_path: Path,
    stage_root: Path,
    root: Path | None = None,
    feature_backend: str = "open_clip",
    feature_model_name: str = "ViT-B-32",
    feature_pretrained: str = "laion2b_s34b_b79k",
    render_sample_count: int = 8,
    min_render_count: int = 8,
    allow_fallback: bool = True,
    device: str = "cuda",
) -> dict[str, Any]:
    manifest_path_value = (
        to_repo_relative_path(manifest_path, root=root) if root is not None else str(manifest_path)
    )
    default_objects: list[dict[str, Any]] = []
    for category, assets in assets_by_category.items():
        for asset in assets:
            default_objects.append(
                {
                    "object_id": asset.object_id,
                    "category": category,
                    "source_split": f"modelnet_{asset.split}",
                    "source_gaussian_path": str(asset.gaussian_path),
                    "source_render_dir": str(asset.render_dir),
                    "gaussian_path": str(stage_root / "assets" / category / asset.object_id / "splat.ply"),
                    "canonical_seed_center_path": str(stage_root / "assets" / category / asset.object_id / "canonical_seed_center.ply"),
                    "canonical_seed_floor_path": str(stage_root / "assets" / category / asset.object_id / "canonical_seed_floor.ply"),
                    "canonical_metadata_path": str(stage_root / "assets" / category / asset.object_id / "canonical_metadata.json"),
                    "render_dir": str(stage_root / "assets" / category / asset.object_id / "renders"),
                    "feature_path": str(stage_root / "features" / category / f"{asset.object_id}.npy"),
                    "scale_meters": [float(value) for value in asset.bbox_size],
                    "support_type": _support_type_for_category(category),
                    "tags": ["modelnet", category, asset.split],
                }
            )
    return {
        "asset_prep": {
            "feature_backend": feature_backend,
            "feature_model_name": feature_model_name,
            "feature_pretrained": feature_pretrained,
            "render_sample_count": render_sample_count,
            "min_render_count": min_render_count,
            "allow_fallback": allow_fallback,
            "device": device,
        },
        "library": {
            "name": "shapesplat_modelnet_bundle",
            "source": "shapesplat_modelnet",
            "manifest_path": manifest_path_value,
            "default_objects": default_objects,
        },
    }


def prepare_modelnet_prior_bundle(
    *,
    category_zips: dict[str, Path],
    extract_root: Path,
    stage_root: Path,
    config_out: Path,
    manifest_out: Path,
    split: str = "train",
    max_objects_per_category: int = 128,
    num_views: int = 8,
    image_size: int = 256,
    point_limit: int = 12000,
    overwrite: bool = False,
    feature_backend: str = "fallback",
    feature_model_name: str = "ViT-B-32",
    feature_pretrained: str = "laion2b_s34b_b79k",
    allow_fallback: bool = True,
    device: str = "cuda",
    root: Path,
) -> dict[str, Any]:
    assets_by_category: dict[str, list[ModelNetObjectAsset]] = {}
    for category, zip_path in category_zips.items():
        assets_by_category[category] = extract_modelnet_assets(
            zip_path,
            extract_root / category,
            category=category,
            split=split,
            max_objects=max_objects_per_category,
            num_views=num_views,
            image_size=image_size,
            point_limit=point_limit,
            overwrite=overwrite,
        )
    config = build_modelnet_prior_bundle_config(
        assets_by_category,
        manifest_path=manifest_out,
        stage_root=stage_root,
        root=root,
        feature_backend=feature_backend,
        feature_model_name=feature_model_name,
        feature_pretrained=feature_pretrained,
        render_sample_count=num_views,
        min_render_count=min(8, num_views),
        allow_fallback=allow_fallback,
        device=device,
    )
    write_yaml(config_out, config)
    stage_shapesplat_assets(config, root=root, overwrite=overwrite)
    library = build_prior_library(config, root=root)
    library.dump_manifest(manifest_out)
    return {
        "asset_count": sum(len(values) for values in assets_by_category.values()),
        "category_counts": {key: len(values) for key, values in assets_by_category.items()},
        "config_path": str(config_out),
        "manifest_path": str(manifest_out),
        "stage_root": str(stage_root),
        "extract_root": str(extract_root),
        "categories": sorted(assets_by_category.keys()),
        "split": split,
    }
