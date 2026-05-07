#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.datasets import load_dataset_spec, resolve_dataset_scene
from priorprobe.prior_assets import build_prior_library, stage_shapesplat_assets
from priorprobe.replica_export import (
    CameraFrame,
    ReplicaOracleTarget,
    generate_orbit_camera_poses,
    write_colmap_text_scene,
)
from priorprobe.replica_surface import (
    ReplicaEGLRenderer,
    build_surface_dataset_config_payload,
    canonicalize_gaussian_asset_to_seed_frame,
    load_colmap_camera_model,
    load_colmap_text_frames,
    object_mesh_arrays,
    sample_object_mesh_points,
)
from priorprobe.runtime_paths import to_repo_relative_path


SHARED_PHASE5_OUTPUT_DEFAULTS = {
    "dataset-config-out": Path("configs/datasets/replica_multi_roomwide_v2_384_surface_rgb_shared.yaml"),
    "manifest-out": Path("outputs/gaussian_direct/prior_library/replica_target_surface_exact_trained_clip_manifest.json"),
    "config-out": Path("outputs/gaussian_direct/prior_library/replica_target_surface_exact_trained_clip.yaml"),
    "inventory-out": Path("outputs/gaussian_direct/prior_library/replica_target_surface_exact_trained_clip_inventory.json"),
    "report-out": Path("docs/notes/03-23_phase5_surface_prep_2026.md"),
    "prior-stage-root": Path("outputs/gaussian_direct/prior_library/replica_target_surface_exact_trained_clip"),
}


def resolve_path(path_value: Path) -> Path:
    return path_value if path_value.is_absolute() else ROOT / path_value


def ensure_clean_dir(path: Path, *, overwrite: bool) -> None:
    if path.exists() and overwrite:
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def target_payload_to_target(payload: dict[str, Any]) -> ReplicaOracleTarget:
    return ReplicaOracleTarget(
        scene_id=str(payload["scene_id"]),
        object_id=int(payload["object_id"]),
        category=str(payload["category"]),
        center=json_array_to_float32(payload["center"]),
        sizes=json_array_to_float32(payload["sizes"]),
        rotation_xyzw=json_array_to_float32(payload["rotation_xyzw"]),
        volume=float(payload["volume"]),
    )


def json_array_to_float32(values: Any) -> Any:
    import numpy as np

    return np.asarray(values, dtype=np.float32)


def load_targets_from_scene(scene_root: Path) -> list[dict[str, Any]]:
    targets_path = scene_root / "oracle" / "targets.json"
    payload = json.loads(targets_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"targets.json must be a list: {targets_path}")
    return [dict(item) for item in payload]


def intrinsics_to_hfov_deg(*, width: int, fx: float) -> float:
    return math.degrees(2.0 * math.atan(float(width) / (2.0 * float(fx))))


def render_surface_scene_from_reference(
    *,
    reference_scene_root: Path,
    raw_scene_root: Path,
    output_scene_root: Path,
    overwrite: bool,
) -> dict[str, Any]:
    camera_model, frames = load_colmap_text_frames(reference_scene_root)
    images_dir = output_scene_root / "images"
    ensure_clean_dir(images_dir, overwrite=overwrite)

    renderer = ReplicaEGLRenderer(
        width=camera_model.width,
        height=camera_model.height,
        fx=camera_model.fx,
        fy=camera_model.fy,
        cx=camera_model.cx,
        cy=camera_model.cy,
        mesh_path=raw_scene_root / "mesh.ply",
        ambient_light=(0.1, 0.1, 0.1),
        directional_intensity=0.5,
    )
    try:
        for frame in frames:
            image_path = images_dir / frame.image_name
            if image_path.exists() and not overwrite:
                continue
            color, _ = renderer.render(position=frame.position, rotation_cam2world=frame.rotation_cam2world)
            Image.fromarray(color).save(image_path)
    finally:
        renderer.close()

    sparse_source = reference_scene_root / "sparse"
    sparse_dest = output_scene_root / "sparse"
    if sparse_dest.exists() and overwrite:
        shutil.rmtree(sparse_dest)
    if not sparse_dest.exists():
        shutil.copytree(sparse_source, sparse_dest)

    reference_scene_meta = json.loads((reference_scene_root / "scene_meta.json").read_text(encoding="utf-8"))
    targets = load_targets_from_scene(reference_scene_root)
    oracle_dir = output_scene_root / "oracle"
    oracle_dir.mkdir(parents=True, exist_ok=True)
    (oracle_dir / "targets.json").write_text(json.dumps(targets, indent=2), encoding="utf-8")
    primary_target_path = reference_scene_root / "oracle" / "target.json"
    if primary_target_path.exists():
        shutil.copy2(primary_target_path, oracle_dir / "target.json")

    scene_meta = dict(reference_scene_meta)
    scene_meta["render_backend"] = "pyrender_egl_vertex_color"
    scene_meta["reference_scene_root"] = str(reference_scene_root)
    scene_meta["raw_scene_root"] = str(raw_scene_root)
    scene_meta["phase5_surface_rgb"] = True
    notes = list(scene_meta.get("notes", []))
    notes.append("Images were rerendered from raw Replica vertex-colored mesh using EGL offscreen rendering.")
    notes.append("Sparse/0 and oracle target metadata were copied from the roomwide_v2_384 GT-staged dataset.")
    notes.append("oracle/objects/*/crops are object-only surface renders used for Phase 5 prior preparation.")
    scene_meta["notes"] = notes
    (output_scene_root / "scene_meta.json").write_text(json.dumps(scene_meta, indent=2), encoding="utf-8")
    return {
        "scene_root": str(output_scene_root),
        "frame_count": len(frames),
        "camera_model": {
            "width": camera_model.width,
            "height": camera_model.height,
            "fx": camera_model.fx,
            "fy": camera_model.fy,
            "cx": camera_model.cx,
            "cy": camera_model.cy,
        },
        "target_count": len(targets),
    }


def export_object_surface_dataset(
    *,
    raw_scene_root: Path,
    target_payload: dict[str, Any],
    output_scene_root: Path,
    width: int,
    height: int,
    hfov_deg: float,
    total_views: int,
    test_views: int,
    mesh_point_count: int,
    seed: int,
    radius_min: float,
    radius_max: float,
    overwrite: bool,
) -> dict[str, Any]:
    ensure_clean_dir(output_scene_root, overwrite=overwrite)
    images_dir = output_scene_root / "images"
    oracle_dir = output_scene_root / "oracle"
    images_dir.mkdir(parents=True, exist_ok=True)
    oracle_dir.mkdir(parents=True, exist_ok=True)

    target = target_payload_to_target(target_payload)
    frames_raw = generate_orbit_camera_poses(
        target,
        count=total_views,
        seed=seed,
        radius_min=radius_min,
        radius_max=radius_max,
    )
    test_indices = set(
        int(index)
        for index in list(np.linspace(0, max(total_views - 1, 0), num=test_views, dtype=int).tolist())
    )
    frames = []
    for index, (position, rotation) in enumerate(frames_raw):
        frames.append(
            CameraFrame(
                image_name=f"{index:05d}.png",
                position=position,
                rotation_cam2world=rotation,
                visible_ratio=1.0,
                split="test" if index in test_indices else "train",
            )
        )

    object_xyz, object_rgb, object_faces = object_mesh_arrays(raw_scene_root, object_id=target.object_id)
    renderer = ReplicaEGLRenderer(
        width=width,
        height=height,
        fx=(width / 2.0) / math.tan(math.radians(hfov_deg) / 2.0),
        fy=(width / 2.0) / math.tan(math.radians(hfov_deg) / 2.0),
        cx=width / 2.0,
        cy=height / 2.0,
        vertices=object_xyz,
        faces=object_faces,
        colors=object_rgb,
        ambient_light=(0.15, 0.15, 0.15),
        directional_intensity=0.7,
    )
    try:
        for frame in frames:
            image_path = images_dir / frame.image_name
            if image_path.exists() and not overwrite:
                continue
            color, _ = renderer.render(position=frame.position, rotation_cam2world=frame.rotation_cam2world)
            Image.fromarray(color).save(image_path)
    finally:
        renderer.close()

    points_xyz, points_rgb = sample_object_mesh_points(
        raw_scene_root,
        object_id=target.object_id,
        num_points=mesh_point_count,
        seed=seed,
    )
    write_colmap_text_scene(
        output_scene_root,
        frames=frames,
        width=width,
        height=height,
        hfov_deg=hfov_deg,
        points_xyz=points_xyz,
        points_rgb=points_rgb,
    )

    object_meta = dict(target_payload)
    object_meta["view_count"] = total_views
    object_meta["train_view_count"] = total_views - test_views
    object_meta["test_view_count"] = test_views
    object_meta["render_backend"] = "pyrender_egl_vertex_color"
    object_meta["object_scene_root"] = str(output_scene_root)
    (oracle_dir / "target.json").write_text(json.dumps(object_meta, indent=2), encoding="utf-8")
    return {
        "object_scene_root": str(output_scene_root),
        "object_id": target.object_id,
        "category": target.category,
        "view_count": total_views,
        "train_view_count": total_views - test_views,
        "test_view_count": test_views,
    }


def train_object_prior(
    *,
    dataset_scene_root: Path,
    model_path: Path,
    repo_path: Path,
    python_executable: Path,
    iterations: int,
    overwrite: bool,
) -> Path:
    final_point_cloud = model_path / "point_cloud" / f"iteration_{iterations}" / "point_cloud.ply"
    if final_point_cloud.exists() and not overwrite:
        return final_point_cloud

    if model_path.exists() and overwrite:
        shutil.rmtree(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(python_executable),
        str(ROOT / "scripts" / "train_vanilla_3dgs_backend.py"),
        "--repo-path",
        str(repo_path),
        "--source_path",
        str(dataset_scene_root),
        "--model_path",
        str(model_path),
        "--images",
        "images",
        "--sh_degree",
        "3",
        "--iterations",
        str(iterations),
        "--test_iterations",
        str(iterations),
        "--save_iterations",
        str(iterations),
        "--disable_viewer",
        "--eval",
        "--quiet",
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    if not final_point_cloud.exists():
        raise FileNotFoundError(f"Missing final point_cloud.ply after prior training: {final_point_cloud}")
    return final_point_cloud


def build_manifest_config(
    *,
    manifest_path: Path,
) -> dict[str, Any]:
    return {
        "library": {
            "name": manifest_path.stem,
            "source": "replica_surface_exact_trained",
            "manifest_path": to_repo_relative_path(manifest_path, root=ROOT),
        }
    }


def copy_object_images_to_scene_crops(
    *,
    object_scene_root: Path,
    scene_surface_root: Path,
    object_id: int,
    overwrite: bool,
) -> int:
    source_dir = object_scene_root / "images"
    destination_dir = scene_surface_root / "oracle" / "objects" / str(object_id) / "crops"
    ensure_clean_dir(destination_dir, overwrite=overwrite)
    copied = 0
    for source_path in sorted(source_dir.glob("*.png")):
        shutil.copy2(source_path, destination_dir / source_path.name)
        copied += 1
    return copied


def phase5_anchor_mode_for_category(category: str) -> str:
    return "floor" if str(category) in {"chair", "sofa", "table", "lamp"} else "center"


def shared_phase5_output_defaults() -> dict[str, Path]:
    return {flag: resolve_path(path).resolve() for flag, path in SHARED_PHASE5_OUTPUT_DEFAULTS.items()}


def is_partial_phase5_run(
    *,
    requested_scene_ids: list[str] | None,
    available_scene_ids: list[str],
    requested_object_ids: set[int],
) -> bool:
    if requested_object_ids:
        return True
    if requested_scene_ids is None:
        return False
    return sorted(requested_scene_ids) != sorted(available_scene_ids)


def validate_phase5_output_paths(*, is_partial_run: bool, output_paths: dict[str, Path]) -> None:
    if not is_partial_run:
        return
    shared_defaults = shared_phase5_output_defaults()
    blocked_flags = [
        flag
        for flag, output_path in output_paths.items()
        if output_path.resolve() == shared_defaults[flag]
    ]
    if blocked_flags:
        joined = ", ".join(f"--{flag}" for flag in blocked_flags)
        raise ValueError(
            "Partial Phase 5 runs must not reuse shared default outputs. "
            f"Provide custom paths for: {joined}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Phase 5 surface-rendered Replica scene datasets and learned same-scene priors.")
    parser.add_argument("--reference-dataset-config", default=Path("configs/datasets/replica_multi_roomwide_v2_384_shared.yaml"), type=Path)
    parser.add_argument("--scene-id", action="append", dest="scene_ids")
    parser.add_argument("--target-object-id", action="append", dest="target_object_ids", type=int)
    parser.add_argument("--raw-root", default=Path("/mnt/hddg1/3dgs-data/priorprobe3dgs/replica_dataset/raw"), type=Path)
    parser.add_argument("--scene-output-root", default=Path("/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_v2_384_surface_rgb"), type=Path)
    parser.add_argument("--dataset-config-out", default=Path("configs/datasets/replica_multi_roomwide_v2_384_surface_rgb_shared.yaml"), type=Path)
    parser.add_argument("--object-dataset-root", default=Path("/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_object_surface_exact_rgb"), type=Path)
    parser.add_argument("--prior-training-root", default=Path("outputs/gaussian_direct/prior_training/replica_surface_exact_trained_7000"), type=Path)
    parser.add_argument("--prior-stage-root", default=Path("outputs/gaussian_direct/prior_library/replica_target_surface_exact_trained_clip"), type=Path)
    parser.add_argument("--manifest-out", default=Path("outputs/gaussian_direct/prior_library/replica_target_surface_exact_trained_clip_manifest.json"), type=Path)
    parser.add_argument("--config-out", default=Path("outputs/gaussian_direct/prior_library/replica_target_surface_exact_trained_clip.yaml"), type=Path)
    parser.add_argument("--inventory-out", default=Path("outputs/gaussian_direct/prior_library/replica_target_surface_exact_trained_clip_inventory.json"), type=Path)
    parser.add_argument("--report-out", default=Path("docs/notes/03-23_phase5_surface_prep_2026.md"), type=Path)
    parser.add_argument("--object-total-views", default=96, type=int)
    parser.add_argument("--object-test-views", default=16, type=int)
    parser.add_argument("--object-mesh-point-count", default=25000, type=int)
    parser.add_argument("--prior-train-iterations", default=7000, type=int)
    parser.add_argument("--seed", default=42, type=int)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    reference_dataset_config = resolve_path(args.reference_dataset_config)
    raw_root = resolve_path(args.raw_root)
    scene_output_root = resolve_path(args.scene_output_root)
    dataset_config_out = resolve_path(args.dataset_config_out)
    object_dataset_root = resolve_path(args.object_dataset_root)
    prior_training_root = resolve_path(args.prior_training_root)
    prior_stage_root = resolve_path(args.prior_stage_root)
    manifest_out = resolve_path(args.manifest_out)
    config_out = resolve_path(args.config_out)
    inventory_out = resolve_path(args.inventory_out)
    report_out = resolve_path(args.report_out)

    spec = load_dataset_spec(reference_dataset_config, root=ROOT)
    scene_ids = list(args.scene_ids or spec.scenes.keys())
    if not scene_ids:
        raise ValueError("No scene ids resolved for Phase 5 preparation")

    scene_records: list[dict[str, Any]] = []
    object_records: list[dict[str, Any]] = []
    prior_default_objects: list[dict[str, Any]] = []
    requested_object_ids = {int(value) for value in (args.target_object_ids or [])}
    partial_run = is_partial_phase5_run(
        requested_scene_ids=list(args.scene_ids) if args.scene_ids is not None else None,
        available_scene_ids=list(spec.scenes.keys()),
        requested_object_ids=requested_object_ids,
    )
    validate_phase5_output_paths(
        is_partial_run=partial_run,
        output_paths={
            "dataset-config-out": dataset_config_out,
            "manifest-out": manifest_out,
            "config-out": config_out,
            "inventory-out": inventory_out,
            "report-out": report_out,
            "prior-stage-root": prior_stage_root,
        },
    )

    repo_path = (ROOT / "../3DGS/gaussian-splatting").resolve()
    python_executable = repo_path / "venv" / "bin" / "python"

    for scene_index, scene_id in enumerate(scene_ids):
        dataset_scene = resolve_dataset_scene(spec, scene_id=scene_id)
        raw_scene_root = raw_root / scene_id
        surface_scene_root = scene_output_root / scene_id
        scene_record = render_surface_scene_from_reference(
            reference_scene_root=dataset_scene.source_path,
            raw_scene_root=raw_scene_root,
            output_scene_root=surface_scene_root,
            overwrite=args.overwrite,
        )
        scene_records.append(scene_record)

        camera_model = load_colmap_camera_model(dataset_scene.source_path)
        hfov_deg = intrinsics_to_hfov_deg(width=camera_model.width, fx=camera_model.fx)
        target_payloads = load_targets_from_scene(dataset_scene.source_path)
        for target_index, target_payload in enumerate(target_payloads):
            object_id = int(target_payload["object_id"])
            if requested_object_ids and object_id not in requested_object_ids:
                continue
            object_scene_root = object_dataset_root / scene_id / str(object_id)
            object_record = export_object_surface_dataset(
                raw_scene_root=raw_scene_root,
                target_payload=target_payload,
                output_scene_root=object_scene_root,
                width=camera_model.width,
                height=camera_model.height,
                hfov_deg=hfov_deg,
                total_views=int(args.object_total_views),
                test_views=int(args.object_test_views),
                mesh_point_count=int(args.object_mesh_point_count),
                seed=int(args.seed) + scene_index * 100 + target_index,
                radius_min=0.45,
                radius_max=3.0,
                overwrite=args.overwrite,
            )
            copied_crop_count = copy_object_images_to_scene_crops(
                object_scene_root=object_scene_root,
                scene_surface_root=surface_scene_root,
                object_id=object_id,
                overwrite=args.overwrite,
            )
            model_path = prior_training_root / scene_id / str(object_id)
            final_point_cloud = train_object_prior(
                dataset_scene_root=object_scene_root,
                model_path=model_path,
                repo_path=repo_path,
                python_executable=python_executable,
                iterations=int(args.prior_train_iterations),
                overwrite=args.overwrite,
            )
            object_name = f"replica_{scene_id}_obj_{object_id}"
            category = str(target_payload["category"])
            anchor_mode = phase5_anchor_mode_for_category(category)
            canonicalized_point_cloud = model_path / f"canonicalized_{anchor_mode}_seed_frame.ply"
            canonicalization_record = canonicalize_gaussian_asset_to_seed_frame(
                final_point_cloud,
                canonicalized_point_cloud,
                target_payload=target_payload,
                anchor_mode=anchor_mode,
            )
            prior_default_objects.append(
                {
                    "object_id": object_name,
                    "category": category,
                    "source_split": "replica_target_surface_exact",
                    "source_gaussian_path": str(canonicalized_point_cloud),
                    "source_render_dir": str(object_scene_root / "images"),
                    "gaussian_path": str(prior_stage_root / "assets" / category / object_name / "splat.ply"),
                    "render_dir": str(prior_stage_root / "assets" / category / object_name / "renders"),
                    "feature_path": str(prior_stage_root / "features" / category / f"{object_name}.npy"),
                    "scale_meters": [float(value) for value in target_payload["sizes"]],
                    "tags": ["replica", "surface_rgb", "same_scene_exact", scene_id, category],
                    "metadata_extras": {
                        "source_domain": "replica",
                        "replica_scene_id": scene_id,
                        "replica_object_id": object_id,
                        "exact_match_key": f"{scene_id}:{object_id}",
                        "exact_target_match": True,
                        "same_scene_match": True,
                        "prior_source": "surface_rgb_object_training",
                        "render_backend": "pyrender_egl_vertex_color",
                        "anchor_mode": anchor_mode,
                        "object_scene_root": str(object_scene_root),
                        "prior_training_model_path": str(model_path),
                        "raw_prior_final_point_cloud": str(final_point_cloud),
                        "canonicalized_source_gaussian_path": str(canonicalized_point_cloud),
                    },
                }
            )
            object_records.append(
                {
                    **object_record,
                    "copied_scene_crop_count": copied_crop_count,
                    "prior_training_model_path": str(model_path),
                    "prior_final_point_cloud": str(final_point_cloud),
                    "canonicalized_prior_point_cloud": str(canonicalized_point_cloud),
                    "anchor_mode": anchor_mode,
                    "canonicalization": canonicalization_record,
                }
            )

    dataset_config_payload = build_surface_dataset_config_payload(
        root=scene_output_root,
        scene_ids=scene_ids,
    )
    dataset_config_out.parent.mkdir(parents=True, exist_ok=True)
    dataset_config_out.write_text(yaml.safe_dump(dataset_config_payload, sort_keys=False), encoding="utf-8")

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
            "name": "replica_target_surface_exact_trained_clip",
            "source": "replica_surface_exact_trained",
            "manifest_path": to_repo_relative_path(manifest_out, root=ROOT),
            "default_objects": prior_default_objects,
        },
    }
    stage_shapesplat_assets(prep_config, root=ROOT, overwrite=True)
    library = build_prior_library(prep_config, root=ROOT)
    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    library.dump_manifest(manifest_out)
    config_out.parent.mkdir(parents=True, exist_ok=True)
    config_out.write_text(yaml.safe_dump(build_manifest_config(manifest_path=manifest_out), sort_keys=False), encoding="utf-8")

    inventory_payload = {
        "scene_dataset_root": str(scene_output_root),
        "scene_dataset_config": str(dataset_config_out),
        "scene_ids": scene_ids,
        "scene_records": scene_records,
        "object_records": object_records,
        "prior_manifest": str(manifest_out),
        "prior_config": str(config_out),
        "prior_stage_root": str(prior_stage_root),
    }
    inventory_out.parent.mkdir(parents=True, exist_ok=True)
    inventory_out.write_text(json.dumps(inventory_payload, indent=2), encoding="utf-8")

    report_lines = [
        "# Replica Phase 5 Surface Prep",
        "",
        "## Summary",
        "",
        f"- Scene dataset root: `{scene_output_root}`",
        f"- Scene dataset config: `{dataset_config_out}`",
        f"- Prior object dataset root: `{object_dataset_root}`",
        f"- Prior training root: `{prior_training_root}`",
        f"- Prior manifest: `{manifest_out}`",
        f"- Prior config: `{config_out}`",
        "",
        "## Scenes",
        "",
    ]
    for record in scene_records:
        report_lines.append(
            f"- `{Path(record['scene_root']).name}`: {record['frame_count']} frames, {record['target_count']} targets, renderer `pyrender_egl_vertex_color`"
        )
    report_lines.extend(["", "## Object Priors", ""])
    for record in object_records:
        report_lines.append(
            f"- `{record['object_scene_root']}`: object `{record['object_id']}` `{record['category']}`, views {record['view_count']}, trained prior `{record['prior_final_point_cloud']}`"
        )
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(json.dumps(inventory_payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
