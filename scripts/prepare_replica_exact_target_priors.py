#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from plyfile import PlyData, PlyElement

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.datasets import load_dataset_spec, resolve_dataset_scene
from priorprobe.insertion.alignment_search import TargetBox, default_anchor_mode, support_type_for_category
from priorprobe.prior_assets import build_prior_library, stage_shapesplat_assets
from priorprobe.replica_export import _load_mesh_arrays, _sample_mesh_triangles
from priorprobe.runtime_paths import to_repo_relative_path


SH_C0 = 0.28209479177387814


def resolve_path(path_value: Path) -> Path:
    return path_value if path_value.is_absolute() else ROOT / path_value


def load_scene_oracle_targets(scene_root: Path) -> list[dict[str, Any]]:
    targets_path = scene_root / "oracle" / "targets.json"
    payload = json.loads(targets_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"oracle/targets.json must contain a list: {targets_path}")
    return [dict(item) for item in payload]


def rgb_to_sh(rgb: np.ndarray) -> np.ndarray:
    rgb = np.clip(rgb.astype(np.float32), 0.0, 1.0)
    return (rgb - 0.5) / SH_C0


def inverse_sigmoid(value: float) -> float:
    return float(np.log(value / max(1.0 - value, 1e-6)))


def estimate_log_scale(points_xyz: np.ndarray) -> float:
    bbox_size = np.maximum(points_xyz.max(axis=0) - points_xyz.min(axis=0), 1e-6)
    bbox_diag = float(np.linalg.norm(bbox_size))
    point_count = max(int(points_xyz.shape[0]), 1)
    base_scale = max(bbox_diag / max(np.cbrt(point_count) * 8.0, 1.0), 1e-4)
    return float(np.log(base_scale))


def build_gaussian_vertex(points_xyz: np.ndarray, points_rgb: np.ndarray) -> np.ndarray:
    feature_dim = 3 * ((3 + 1) ** 2 - 1)
    dtype: list[tuple[str, str]] = [
        ("x", "f4"),
        ("y", "f4"),
        ("z", "f4"),
        ("nx", "f4"),
        ("ny", "f4"),
        ("nz", "f4"),
        ("f_dc_0", "f4"),
        ("f_dc_1", "f4"),
        ("f_dc_2", "f4"),
    ]
    dtype.extend((f"f_rest_{index}", "f4") for index in range(feature_dim))
    dtype.extend(
        [
            ("opacity", "f4"),
            ("scale_0", "f4"),
            ("scale_1", "f4"),
            ("scale_2", "f4"),
            ("rot_0", "f4"),
            ("rot_1", "f4"),
            ("rot_2", "f4"),
            ("rot_3", "f4"),
        ]
    )

    vertex = np.empty(points_xyz.shape[0], dtype=dtype)
    vertex["x"] = points_xyz[:, 0]
    vertex["y"] = points_xyz[:, 1]
    vertex["z"] = points_xyz[:, 2]
    vertex["nx"] = 0.0
    vertex["ny"] = 0.0
    vertex["nz"] = 0.0

    sh_dc = rgb_to_sh(points_rgb)
    vertex["f_dc_0"] = sh_dc[:, 0]
    vertex["f_dc_1"] = sh_dc[:, 1]
    vertex["f_dc_2"] = sh_dc[:, 2]
    for index in range(feature_dim):
        vertex[f"f_rest_{index}"] = 0.0

    log_scale = np.float32(estimate_log_scale(points_xyz))
    opacity = np.float32(inverse_sigmoid(0.1))
    vertex["opacity"] = opacity
    vertex["scale_0"] = log_scale
    vertex["scale_1"] = log_scale
    vertex["scale_2"] = log_scale
    vertex["rot_0"] = 1.0
    vertex["rot_1"] = 0.0
    vertex["rot_2"] = 0.0
    vertex["rot_3"] = 0.0
    return vertex


def write_gaussian_ply(path: Path, vertex: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    PlyData([PlyElement.describe(vertex, "vertex")]).write(path)


def sample_exact_object_points(
    *,
    raw_scene_root: Path,
    object_id: int,
    num_points: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    mesh_path = raw_scene_root / "habitat" / "mesh_semantic.ply"
    xyz, rgb, triangles, triangle_object_ids = _load_mesh_arrays(mesh_path, include_object_ids=True)
    assert triangle_object_ids is not None
    object_triangles = triangles[triangle_object_ids == int(object_id)]
    if object_triangles.size == 0:
        raise ValueError(f"No semantic mesh triangles for object_id={object_id} in {mesh_path}")
    samples, colors, _ = _sample_mesh_triangles(
        xyz,
        rgb,
        object_triangles,
        num_points=num_points,
        seed=seed,
    )
    return samples.astype(np.float32), colors.astype(np.float32) / 255.0


def canonicalize_points(
    *,
    points_xyz: np.ndarray,
    target_payload: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, str]:
    target_box = TargetBox.from_payload(target_payload)
    support_type = support_type_for_category(str(target_payload["category"]))
    anchor_mode = default_anchor_mode(str(target_payload["category"]), support_type)
    anchor_point = target_box.anchor_point(anchor_mode).astype(np.float32)
    local_xyz = (points_xyz - anchor_point[None, :]) @ target_box.rotation_matrix
    return local_xyz.astype(np.float32), target_box.sizes.astype(np.float32), anchor_mode


def build_target_item(
    *,
    stage_root: Path,
    dataset_scene_root: Path,
    scene_id: str,
    target_payload: dict[str, Any],
    source_gaussian_path: Path,
    bbox_size: np.ndarray,
) -> dict[str, Any]:
    object_id = int(target_payload["object_id"])
    category = str(target_payload["category"])
    object_name = f"replica_{scene_id}_obj_{object_id}"
    crop_dir = dataset_scene_root / "oracle" / "objects" / str(object_id) / "crops"
    return {
        "object_id": object_name,
        "category": category,
        "source_split": "replica_target_exact",
        "source_gaussian_path": str(source_gaussian_path),
        "source_render_dir": str(crop_dir),
        "gaussian_path": str(stage_root / "assets" / category / object_name / "splat.ply"),
        "render_dir": str(stage_root / "assets" / category / object_name / "renders"),
        "feature_path": str(stage_root / "features" / category / f"{object_name}.npy"),
        "scale_meters": [float(value) for value in bbox_size.tolist()],
        "tags": ["replica", "same_scene_exact", scene_id, category],
        "metadata_extras": {
            "source_domain": "replica",
            "replica_scene_id": scene_id,
            "replica_object_id": object_id,
            "exact_match_key": f"{scene_id}:{object_id}",
            "exact_target_match": True,
            "same_scene_match": True,
        },
    }


def build_minimal_prior_config(*, manifest_path: Path) -> dict[str, object]:
    return {
        "library": {
            "name": manifest_path.stem,
            "source": "replica_same_scene_exact",
            "manifest_path": to_repo_relative_path(manifest_path, root=ROOT),
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build exact-instance Replica gaussian priors for target scenes.")
    parser.add_argument("--dataset-config", default=Path("configs/datasets/replica_multi_shared.yaml"), type=Path)
    parser.add_argument("--scene-id", action="append", dest="scene_ids", help="Target scene id to include.")
    parser.add_argument(
        "--raw-root",
        default=Path("/mnt/hddg1/3dgs-data/priorprobe3dgs/replica_dataset/raw"),
        type=Path,
    )
    parser.add_argument(
        "--stage-root",
        default=Path("outputs/gaussian_direct/prior_library/replica_target_exact_clip"),
        type=Path,
    )
    parser.add_argument(
        "--manifest-out",
        default=Path("outputs/gaussian_direct/prior_library/replica_target_exact_clip_manifest.json"),
        type=Path,
    )
    parser.add_argument(
        "--config-out",
        default=Path("outputs/gaussian_direct/prior_library/replica_target_exact_clip.yaml"),
        type=Path,
    )
    parser.add_argument("--inventory-out", type=Path)
    parser.add_argument("--points-per-object", default=25000, type=int)
    parser.add_argument("--seed", default=42, type=int)
    args = parser.parse_args()

    dataset_config = resolve_path(args.dataset_config)
    raw_root = resolve_path(args.raw_root)
    stage_root = resolve_path(args.stage_root)
    manifest_out = resolve_path(args.manifest_out)
    config_out = resolve_path(args.config_out)
    inventory_out = (
        resolve_path(args.inventory_out)
        if args.inventory_out is not None
        else stage_root.parent / "replica_target_exact_clip_inventory.json"
    )

    spec = load_dataset_spec(dataset_config, root=ROOT)
    scene_ids = list(args.scene_ids or spec.scenes.keys())

    default_objects: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []

    for scene_id in scene_ids:
        dataset_scene = resolve_dataset_scene(spec, scene_id=scene_id)
        raw_scene_root = raw_root / scene_id
        if not raw_scene_root.exists():
            raise FileNotFoundError(f"Replica raw scene is missing: {raw_scene_root}")

        targets = load_scene_oracle_targets(dataset_scene.source_path)
        if not targets:
            raise FileNotFoundError(f"oracle/targets.json is missing for {scene_id}: {dataset_scene.source_path}")

        for index, target_payload in enumerate(targets):
            object_id = int(target_payload["object_id"])
            sampled_xyz, sampled_rgb = sample_exact_object_points(
                raw_scene_root=raw_scene_root,
                object_id=object_id,
                num_points=args.points_per_object,
                seed=args.seed + index,
            )
            local_xyz, bbox_size, anchor_mode = canonicalize_points(
                points_xyz=sampled_xyz,
                target_payload=target_payload,
            )

            source_gaussian_path = stage_root / "source_assets" / scene_id / str(object_id) / "splat.ply"
            write_gaussian_ply(source_gaussian_path, build_gaussian_vertex(local_xyz, sampled_rgb))

            default_objects.append(
                build_target_item(
                    stage_root=stage_root,
                    dataset_scene_root=dataset_scene.source_path,
                    scene_id=scene_id,
                    target_payload=target_payload,
                    source_gaussian_path=source_gaussian_path,
                    bbox_size=bbox_size,
                )
            )
            inventory.append(
                {
                    "scene_id": scene_id,
                    "object_id": object_id,
                    "category": str(target_payload["category"]),
                    "point_count": int(local_xyz.shape[0]),
                    "bbox_size": [float(value) for value in bbox_size.tolist()],
                    "anchor_mode": anchor_mode,
                    "source_gaussian_path": str(source_gaussian_path),
                }
            )

    prep_config = {
        "asset_prep": {
            "feature_backend": "clip",
            "feature_model_name": "ViT-B-32",
            "feature_pretrained": "laion2b_s34b_b79k",
            "render_sample_count": 8,
            "min_render_count": 8,
            "allow_fallback": False,
            "device": "cuda",
        },
        "library": {
            "name": "replica_target_exact_clip",
            "source": "replica_same_scene_exact",
            "manifest_path": to_repo_relative_path(manifest_out, root=ROOT),
            "default_objects": default_objects,
        },
    }

    stage_shapesplat_assets(prep_config, root=ROOT, overwrite=True)
    library = build_prior_library(prep_config, root=ROOT)
    library.dump_manifest(manifest_out)

    config_out.parent.mkdir(parents=True, exist_ok=True)
    config_out.write_text(
        yaml.safe_dump(build_minimal_prior_config(manifest_path=manifest_out), sort_keys=False),
        encoding="utf-8",
    )
    inventory_out.parent.mkdir(parents=True, exist_ok=True)
    inventory_out.write_text(json.dumps(inventory, indent=2), encoding="utf-8")

    print(f"Wrote manifest to {manifest_out}")
    print(f"Wrote prior config to {config_out}")
    print(f"Wrote inventory to {inventory_out}")
    print(json.dumps({"scene_ids": scene_ids, "object_count": len(default_objects)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
