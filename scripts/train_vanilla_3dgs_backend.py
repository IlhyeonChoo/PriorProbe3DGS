#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import sys
import types
import zlib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def bootstrap_repo_path() -> Path:
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument("--repo-path", required=True, type=Path)
    args, _ = bootstrap.parse_known_args()
    repo_path = args.repo_path.resolve()
    if str(repo_path) not in sys.path:
        sys.path.insert(0, str(repo_path))
    return repo_path


REPO_PATH = bootstrap_repo_path()


def install_dummy_network_gui() -> None:
    module = types.ModuleType("gaussian_renderer.network_gui")
    module.conn = None
    module.addr = None
    module.listener = None
    module.init = lambda *args, **kwargs: None
    module.try_connect = lambda *args, **kwargs: None
    module.receive = lambda *args, **kwargs: (None, None, None, None, None, None)
    module.send = lambda *args, **kwargs: None
    sys.modules["gaussian_renderer.network_gui"] = module


if "--disable_viewer" in sys.argv:
    install_dummy_network_gui()

import numpy as np
import torch
import torchvision
from plyfile import PlyData, PlyElement
from torch import nn

train_module = importlib.import_module("train")
scene_module = importlib.import_module("scene")
dataset_readers = importlib.import_module("scene.dataset_readers")
arguments_module = importlib.import_module("arguments")
gaussian_renderer_module = importlib.import_module("gaussian_renderer")

ModelParams = arguments_module.ModelParams
OptimizationParams = arguments_module.OptimizationParams
PipelineParams = arguments_module.PipelineParams


def load_alignment_spec(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {
            "scale": 1.0,
            "rotation_matrix": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            "translation": [0.0, 0.0, 0.0],
        }

    payload = json.loads(path.read_text(encoding="utf-8"))
    if "matrix4x4" in payload:
        matrix = np.asarray(payload["matrix4x4"], dtype=np.float64)
        if matrix.shape != (4, 4):
            raise ValueError("matrix4x4 must be a 4x4 matrix")
        return {
            "scale": 1.0,
            "rotation_matrix": matrix[:3, :3].tolist(),
            "translation": matrix[:3, 3].tolist(),
        }

    return {
        "scale": payload.get("scale", 1.0),
        "rotation_matrix": payload.get(
            "rotation_matrix",
            [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        ),
        "translation": payload.get("translation", [0.0, 0.0, 0.0]),
    }


def quaternion_from_matrix(rotation_matrix: np.ndarray) -> np.ndarray:
    m = rotation_matrix
    trace = float(np.trace(m))
    if trace > 0.0:
        s = np.sqrt(trace + 1.0) * 2.0
        w = 0.25 * s
        x = (m[2, 1] - m[1, 2]) / s
        y = (m[0, 2] - m[2, 0]) / s
        z = (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2.0
        w = (m[2, 1] - m[1, 2]) / s
        x = 0.25 * s
        y = (m[0, 1] + m[1, 0]) / s
        z = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2.0
        w = (m[0, 2] - m[2, 0]) / s
        x = (m[0, 1] + m[1, 0]) / s
        y = 0.25 * s
        z = (m[1, 2] + m[2, 1]) / s
    else:
        s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2.0
        w = (m[1, 0] - m[0, 1]) / s
        x = (m[0, 2] + m[2, 0]) / s
        y = (m[1, 2] + m[2, 1]) / s
        z = 0.25 * s
    quat = np.asarray([w, x, y, z], dtype=np.float32)
    return quat / np.linalg.norm(quat)


def quaternion_multiply(q_left: np.ndarray, q_right: np.ndarray) -> np.ndarray:
    w1, x1, y1, z1 = q_left
    w2, x2, y2, z2 = q_right
    quat = np.asarray(
        [
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        ],
        dtype=np.float32,
    )
    return quat / np.linalg.norm(quat)


def parse_scale(scale_value: Any, *, allow_anisotropic: bool = False) -> tuple[np.ndarray, float | None]:
    if isinstance(scale_value, (int, float)):
        scalar = float(scale_value)
        return np.asarray([scalar, scalar, scalar], dtype=np.float32), scalar

    scale = np.asarray(scale_value, dtype=np.float32)
    if scale.shape != (3,):
        raise ValueError("scale must be a scalar or a 3-vector")
    if allow_anisotropic:
        return scale, None
    if not np.allclose(scale, scale[0]):
        raise ValueError("Gaussian prior alignment currently supports isotropic scale only")
    return scale, float(scale[0])


def detect_asset_format(vertex: np.ndarray) -> str:
    names = vertex.dtype.names or ()
    if {"opacity", "f_dc_0", "scale_0", "rot_0"}.issubset(set(names)):
        return "gaussian"
    if {"red", "green", "blue"}.issubset(set(names)):
        return "point_cloud"
    raise ValueError(f"Unsupported PLY schema: {names}")


def transform_positions(
    xyz: np.ndarray,
    *,
    scale: np.ndarray,
    rotation_matrix: np.ndarray,
    translation: np.ndarray,
) -> np.ndarray:
    return (xyz * scale) @ rotation_matrix.T + translation


def write_structured_ply(path: Path, data: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    element = PlyElement.describe(data, "vertex")
    PlyData([element]).write(path)


def build_point_cloud_vertex(
    xyz: np.ndarray,
    vertex: np.ndarray,
) -> np.ndarray:
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
    output["nx"] = vertex["nx"] if "nx" in (vertex.dtype.names or ()) else 0.0
    output["ny"] = vertex["ny"] if "ny" in (vertex.dtype.names or ()) else 0.0
    output["nz"] = vertex["nz"] if "nz" in (vertex.dtype.names or ()) else 0.0
    output["red"] = vertex["red"]
    output["green"] = vertex["green"]
    output["blue"] = vertex["blue"]
    return output


def build_point_cloud_from_gaussian_vertex(vertex: np.ndarray) -> np.ndarray:
    xyz = np.stack([vertex["x"], vertex["y"], vertex["z"]], axis=1).astype(np.float32)
    colors = np.stack([vertex["f_dc_0"], vertex["f_dc_1"], vertex["f_dc_2"]], axis=1).astype(np.float32)
    colors = np.clip(dataset_readers.SH2RGB(colors), 0.0, 1.0)
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
    output["nx"] = 0.0
    output["ny"] = 0.0
    output["nz"] = 0.0
    output["red"] = np.round(colors[:, 0] * 255.0).astype(np.uint8)
    output["green"] = np.round(colors[:, 1] * 255.0).astype(np.uint8)
    output["blue"] = np.round(colors[:, 2] * 255.0).astype(np.uint8)
    return output


def prepare_prior_asset(prior_ply: Path, alignment_json: Path | None, output_path: Path) -> tuple[Path, str, dict[str, Any]]:
    alignment = load_alignment_spec(alignment_json)
    rotation_matrix = np.asarray(alignment["rotation_matrix"], dtype=np.float32)
    translation = np.asarray(alignment["translation"], dtype=np.float32)

    ply = PlyData.read(prior_ply)
    vertex = np.array(ply["vertex"].data, copy=True)
    asset_format = detect_asset_format(vertex)
    scale_vec, scale_scalar = parse_scale(
        alignment["scale"],
        allow_anisotropic=asset_format == "point_cloud",
    )

    xyz = np.stack([vertex["x"], vertex["y"], vertex["z"]], axis=1).astype(np.float32)
    xyz = transform_positions(
        xyz,
        scale=scale_vec,
        rotation_matrix=rotation_matrix,
        translation=translation,
    )
    vertex["x"] = xyz[:, 0]
    vertex["y"] = xyz[:, 1]
    vertex["z"] = xyz[:, 2]

    if asset_format == "gaussian":
        if scale_scalar is None or scale_scalar <= 0.0:
            raise ValueError("scale must be positive for gaussian priors")
        for field_name in ("scale_0", "scale_1", "scale_2"):
            vertex[field_name] = vertex[field_name] + np.float32(np.log(scale_scalar))

        align_quat = quaternion_from_matrix(rotation_matrix)
        quats = np.stack([vertex["rot_0"], vertex["rot_1"], vertex["rot_2"], vertex["rot_3"]], axis=1).astype(np.float32)
        rotated = np.stack([quaternion_multiply(align_quat, quat) for quat in quats], axis=0)
        vertex["rot_0"] = rotated[:, 0]
        vertex["rot_1"] = rotated[:, 1]
        vertex["rot_2"] = rotated[:, 2]
        vertex["rot_3"] = rotated[:, 3]
        output_vertex = vertex
    else:
        output_vertex = build_point_cloud_vertex(xyz, vertex)

    write_structured_ply(output_path, output_vertex)
    return output_path, asset_format, alignment


def load_prior_specs(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"prior spec json must contain a list: {path}")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"prior spec entry {index} is not an object")
        if item.get("prior_ply") is None:
            raise ValueError(f"prior spec entry {index} is missing prior_ply")
        normalized.append(
            {
                "prior_ply": str(item["prior_ply"]),
                "alignment_json": item.get("alignment_json"),
                "prior_object_id": item.get("prior_object_id"),
                "prior_score": item.get("prior_score"),
                "normalized_confidence": item.get("normalized_confidence"),
                "point_keep_ratio": item.get("point_keep_ratio"),
                "dropped": item.get("dropped"),
                "drop_reason": item.get("drop_reason"),
                "target_object_id": item.get("target_object_id"),
                "target_category": item.get("target_category"),
                "alignment_debug": item.get("alignment_debug"),
                "source_prior_path": item.get("source_prior_path"),
                "canonical_seed_path": item.get("canonical_seed_path"),
            }
        )
    return normalized


def prepare_prior_assets(prior_specs: list[dict[str, Any]], model_path: Path) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for index, spec in enumerate(prior_specs):
        prior_ply = Path(str(spec["prior_ply"])).resolve()
        alignment_json = (
            Path(str(spec["alignment_json"])).resolve()
            if spec.get("alignment_json") is not None
            else None
        )
        prepared_init_ply, prepared_asset_format, alignment = prepare_prior_asset(
            prior_ply,
            alignment_json,
            model_path / "prior_init" / f"aligned_prior_{index:02d}.ply",
        )
        prepared.append(
            {
                "source_prior": str(prior_ply),
                "aligned_prior": str(prepared_init_ply),
                "asset_format": prepared_asset_format,
                "alignment": alignment,
                "prior_object_id": spec.get("prior_object_id"),
                "prior_score": spec.get("prior_score"),
                "normalized_confidence": spec.get("normalized_confidence"),
                "point_keep_ratio": spec.get("point_keep_ratio"),
                "dropped": spec.get("dropped"),
                "drop_reason": spec.get("drop_reason"),
                "target_object_id": spec.get("target_object_id"),
                "target_category": spec.get("target_category"),
                "alignment_debug": spec.get("alignment_debug"),
                "source_prior_path": spec.get("source_prior_path"),
                "canonical_seed_path": spec.get("canonical_seed_path"),
            }
        )
    return prepared


def prepared_asset_to_point_cloud(path: Path, asset_format: str):
    if asset_format == "point_cloud":
        return dataset_readers.fetchPly(str(path))
    if asset_format != "gaussian":
        raise ValueError(f"Unsupported prepared asset format: {asset_format}")

    ply = PlyData.read(path)
    vertex = np.array(ply["vertex"].data, copy=False)
    point_cloud_vertex = build_point_cloud_from_gaussian_vertex(vertex)
    xyz = np.stack([point_cloud_vertex["x"], point_cloud_vertex["y"], point_cloud_vertex["z"]], axis=1)
    rgb = np.stack(
        [point_cloud_vertex["red"], point_cloud_vertex["green"], point_cloud_vertex["blue"]],
        axis=1,
    ).astype(np.float32) / 255.0
    normals = np.zeros_like(xyz)
    return dataset_readers.BasicPointCloud(points=xyz, colors=rgb, normals=normals)


def merge_point_clouds(base_pcd, prior_pcd):
    xyz = np.concatenate([np.asarray(base_pcd.points), np.asarray(prior_pcd.points)], axis=0)
    colors = np.concatenate([np.asarray(base_pcd.colors), np.asarray(prior_pcd.colors)], axis=0)
    normals = np.concatenate([np.asarray(base_pcd.normals), np.asarray(prior_pcd.normals)], axis=0)
    return dataset_readers.BasicPointCloud(points=xyz, colors=colors, normals=normals)


def _stable_seed(prepared_item: dict[str, Any]) -> int:
    payload = "::".join(
        [
            str(prepared_item.get("target_object_id", "")),
            str(prepared_item.get("prior_object_id", "")),
            str(prepared_item.get("aligned_prior", "")),
        ]
    )
    return int(zlib.crc32(payload.encode("utf-8")) & 0xFFFFFFFF)


def subsample_point_cloud(point_cloud, *, keep_ratio: float, seed: int):
    xyz = np.asarray(point_cloud.points)
    colors = np.asarray(point_cloud.colors)
    normals = np.asarray(point_cloud.normals)
    original_count = int(xyz.shape[0])
    if original_count == 0:
        return point_cloud, 0, 0

    clipped_ratio = float(np.clip(keep_ratio, 0.0, 1.0))
    keep_count = min(original_count, max(1, int(round(original_count * clipped_ratio))))
    if keep_count >= original_count:
        return point_cloud, original_count, original_count

    rng = np.random.default_rng(seed)
    indices = np.sort(rng.choice(original_count, size=keep_count, replace=False))
    sampled = dataset_readers.BasicPointCloud(
        points=xyz[indices],
        colors=colors[indices],
        normals=normals[indices],
    )
    return sampled, original_count, keep_count


def apply_insertion_policy(prior_pcd, prepared_item: dict[str, Any], *, init_mode: str):
    updated = dict(prepared_item)
    raw_score = updated.get("prior_score")
    normalized_confidence = float(updated.get("normalized_confidence", 1.0) or 0.0)
    requested_keep_ratio = float(updated.get("point_keep_ratio", 1.0) or 0.0)
    dropped = bool(updated.get("dropped", False))
    original_count = int(np.asarray(prior_pcd.points).shape[0])

    updated["prior_score"] = float(raw_score) if raw_score is not None else None
    updated["normalized_confidence"] = normalized_confidence
    updated["requested_point_keep_ratio"] = requested_keep_ratio
    updated["original_point_count"] = original_count

    if dropped:
        updated["applied_point_keep_ratio"] = 0.0
        updated["kept_point_count"] = 0
        updated["dropped"] = True
        return None, updated

    if init_mode == "weighted_merge":
        sampled_pcd, original_count, kept_count = subsample_point_cloud(
            prior_pcd,
            keep_ratio=requested_keep_ratio,
            seed=_stable_seed(updated),
        )
        updated["applied_point_keep_ratio"] = float(kept_count / max(original_count, 1))
        updated["kept_point_count"] = kept_count
        updated["dropped"] = False
        return sampled_pcd, updated

    updated["applied_point_keep_ratio"] = 1.0
    updated["kept_point_count"] = original_count
    updated["dropped"] = False
    return prior_pcd, updated


def initialize_loaded_prior(gaussians, train_cam_infos, cameras_extent: float) -> None:
    gaussians.spatial_lr_scale = cameras_extent
    gaussians.max_radii2D = torch.zeros((gaussians.get_xyz.shape[0]), device="cuda")
    gaussians.exposure_mapping = {cam_info.image_name: idx for idx, cam_info in enumerate(train_cam_infos)}
    if not hasattr(gaussians, "pretrained_exposures"):
        gaussians.pretrained_exposures = None
    exposure = torch.eye(3, 4, device="cuda")[None].repeat(len(train_cam_infos), 1, 1)
    gaussians._exposure = nn.Parameter(exposure.requires_grad_(True))


def write_prior_metadata(
    model_path: Path,
    *,
    selected_priors: list[dict[str, Any]],
    init_mode: str,
) -> None:
    metadata = {
        "selected_priors": selected_priors,
        "init_mode": init_mode,
    }
    if len(selected_priors) == 1:
        item = selected_priors[0]
        metadata["source_prior"] = item.get("source_prior")
        metadata["aligned_prior"] = item.get("aligned_prior")
        metadata["asset_format"] = item.get("asset_format")
        metadata["alignment"] = item.get("alignment")
        metadata["prior_object_id"] = item.get("prior_object_id")
        metadata["prior_score"] = item.get("prior_score")
    metadata_path = model_path / "prior_init" / "metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def render_snapshot_set(
    *,
    model_path: Path,
    name: str,
    views,
    gaussians,
    pipeline,
    background: torch.Tensor,
    train_test_exp: bool,
    separate_sh: bool,
) -> None:
    render_path = model_path / name / "ours_0" / "renders"
    gt_path = model_path / name / "ours_0" / "gt"
    render_path.mkdir(parents=True, exist_ok=True)
    gt_path.mkdir(parents=True, exist_ok=True)

    for index, view in enumerate(views):
        rendering = gaussian_renderer_module.render(
            view,
            gaussians,
            pipeline,
            background,
            use_trained_exp=train_test_exp,
            separate_sh=separate_sh,
        )["render"]
        gt = view.original_image[0:3, :, :]

        if train_test_exp:
            rendering = rendering[..., rendering.shape[-1] // 2 :]
            gt = gt[..., gt.shape[-1] // 2 :]

        torchvision.utils.save_image(rendering, render_path / f"{index:05d}.png")
        torchvision.utils.save_image(gt, gt_path / f"{index:05d}.png")


def save_initial_snapshot(scene, args) -> None:
    if not bool(getattr(args, "save_initial_snapshot", False)):
        return
    if scene.loaded_iter:
        return

    model_path = Path(scene.model_path)
    scene.save(0)

    pipeline = types.SimpleNamespace(
        convert_SHs_python=bool(getattr(args, "initial_snapshot_convert_shs_python", False)),
        compute_cov3D_python=bool(getattr(args, "initial_snapshot_compute_cov3d_python", False)),
        debug=bool(getattr(args, "initial_snapshot_debug", False)),
        antialiasing=bool(getattr(args, "initial_snapshot_antialiasing", False)),
    )

    bg_color = [1, 1, 1] if args.white_background else [0, 0, 0]
    background = torch.tensor(bg_color, dtype=torch.float32, device="cuda")
    requested_sets = tuple(getattr(args, "initial_render_sets", ("train", "test")))
    separate_sh = bool(getattr(train_module, "SPARSE_ADAM_AVAILABLE", False))

    if "train" in requested_sets:
        render_snapshot_set(
            model_path=model_path,
            name="train",
            views=scene.getTrainCameras(),
            gaussians=scene.gaussians,
            pipeline=pipeline,
            background=background,
            train_test_exp=args.train_test_exp,
            separate_sh=separate_sh,
        )
    if "test" in requested_sets:
        render_snapshot_set(
            model_path=model_path,
            name="test",
            views=scene.getTestCameras(),
            gaussians=scene.gaussians,
            pipeline=pipeline,
            background=background,
            train_test_exp=args.train_test_exp,
            separate_sh=separate_sh,
        )


def propagate_prior_runtime_args(dataset: Any, args: argparse.Namespace) -> None:
    setattr(dataset, "init_mode", args.init_mode)
    setattr(dataset, "save_initial_snapshot", bool(getattr(args, "save_initial_snapshot", False)))
    setattr(dataset, "initial_render_sets", tuple(getattr(args, "initial_render_sets", ("train", "test"))))
    setattr(
        dataset,
        "initial_snapshot_convert_shs_python",
        bool(getattr(args, "initial_snapshot_convert_shs_python", False)),
    )
    setattr(
        dataset,
        "initial_snapshot_compute_cov3d_python",
        bool(getattr(args, "initial_snapshot_compute_cov3d_python", False)),
    )
    setattr(dataset, "initial_snapshot_debug", bool(getattr(args, "initial_snapshot_debug", False)))
    setattr(dataset, "initial_snapshot_antialiasing", bool(getattr(args, "initial_snapshot_antialiasing", False)))
    if getattr(args, "prepared_init_ply", None) is not None:
        setattr(dataset, "prepared_init_ply", str(args.prepared_init_ply))
        setattr(dataset, "prepared_init_format", args.prepared_init_format)
    if getattr(args, "prepared_init_plys", None):
        setattr(dataset, "prepared_init_plys", list(getattr(args, "prepared_init_plys")))
        setattr(dataset, "prepared_init_formats", list(getattr(args, "prepared_init_formats")))
    if getattr(args, "selected_priors_metadata", None):
        setattr(dataset, "selected_priors_metadata", list(getattr(args, "selected_priors_metadata")))


def make_prior_init_scene():
    class PriorInitScene:
        gaussians: Any

        def __init__(self, args, gaussians, load_iteration=None, shuffle=True, resolution_scales=[1.0]):
            self.model_path = args.model_path
            self.loaded_iter = None
            self.gaussians = gaussians

            if load_iteration:
                if load_iteration == -1:
                    self.loaded_iter = scene_module.searchForMaxIteration(os.path.join(self.model_path, "point_cloud"))
                else:
                    self.loaded_iter = load_iteration
                print("Loading trained model at iteration {}".format(self.loaded_iter))

            self.train_cameras = {}
            self.test_cameras = {}

            test_list_path = os.path.join(args.source_path, "sparse/0", "test.txt")
            if os.path.exists(os.path.join(args.source_path, "sparse")):
                if os.path.exists(test_list_path):
                    scene_info = dataset_readers.readColmapSceneInfo(
                        args.source_path,
                        args.images,
                        args.depths,
                        True,
                        args.train_test_exp,
                        llffhold=0,
                    )
                else:
                    scene_info = scene_module.sceneLoadTypeCallbacks["Colmap"](
                        args.source_path,
                        args.images,
                        args.depths,
                        args.eval,
                        args.train_test_exp,
                    )
            elif os.path.exists(os.path.join(args.source_path, "transforms_train.json")):
                print("Found transforms_train.json file, assuming Blender data set!")
                scene_info = scene_module.sceneLoadTypeCallbacks["Blender"](
                    args.source_path,
                    args.white_background,
                    args.depths,
                    args.eval,
                )
            else:
                raise AssertionError("Could not recognize scene type!")

            train_cam_infos = scene_info.train_cameras
            test_cam_infos = scene_info.test_cameras

            max_train_cameras = getattr(args, "max_train_cameras", 0)
            if max_train_cameras > 0 and len(train_cam_infos) > max_train_cameras:
                before = len(train_cam_infos)
                quality_scores = scene_module.load_colmap_camera_quality(args.source_path)
                train_cam_infos = scene_module.subsample_cameras_quality_random(
                    train_cam_infos,
                    max_train_cameras,
                    quality_scores,
                    getattr(args, "camera_quality_ratio", 0.7),
                    getattr(args, "camera_selection_seed", 42),
                )
                print(
                    "Limiting training cameras: "
                    f"{before} -> {len(train_cam_infos)} "
                    f"(max_train_cameras={max_train_cameras}, "
                    f"camera_quality_ratio={getattr(args, 'camera_quality_ratio', 0.7)}, "
                    f"seed={getattr(args, 'camera_selection_seed', 42)})"
                )

            prepared_init_plys = list(getattr(args, "prepared_init_plys", []))
            prepared_init_formats = list(getattr(args, "prepared_init_formats", []))
            selected_priors_metadata = [dict(item) for item in getattr(args, "selected_priors_metadata", [])]
            prepared_init_ply = getattr(args, "prepared_init_ply", None)
            prepared_asset_format = getattr(args, "prepared_init_format", None)
            if not prepared_init_plys and prepared_init_ply is not None:
                prepared_init_plys = [str(prepared_init_ply)]
                if prepared_asset_format is None:
                    raise ValueError("prepared_init_format is required when prepared_init_ply is set")
                prepared_init_formats = [str(prepared_asset_format)]

            if not self.loaded_iter:
                if prepared_init_plys and getattr(args, "init_mode", "merge") == "replace":
                    if len(prepared_init_plys) != 1:
                        raise ValueError("replace init_mode supports exactly one prepared prior")
                    input_ply = Path(prepared_init_plys[0])
                else:
                    input_ply = Path(scene_info.ply_path)
                input_ply = input_ply.resolve()
                Path(self.model_path).mkdir(parents=True, exist_ok=True)
                shutil.copyfile(input_ply, Path(self.model_path) / "input.ply")
                json_cams = []
                camlist = []
                if test_cam_infos:
                    camlist.extend(test_cam_infos)
                if train_cam_infos:
                    camlist.extend(train_cam_infos)
                for idx, cam in enumerate(camlist):
                    json_cams.append(scene_module.camera_to_JSON(idx, cam))
                with open(os.path.join(self.model_path, "cameras.json"), "w", encoding="utf-8") as file:
                    json.dump(json_cams, file)

            if shuffle:
                import random

                random.shuffle(train_cam_infos)
                random.shuffle(test_cam_infos)

            self.cameras_extent = scene_info.nerf_normalization["radius"]

            for resolution_scale in resolution_scales:
                print("Loading Training Cameras")
                self.train_cameras[resolution_scale] = scene_module.cameraList_from_camInfos(
                    train_cam_infos,
                    resolution_scale,
                    args,
                    scene_info.is_nerf_synthetic,
                    False,
                )
                print("Loading Test Cameras")
                self.test_cameras[resolution_scale] = scene_module.cameraList_from_camInfos(
                    test_cam_infos,
                    resolution_scale,
                    args,
                    scene_info.is_nerf_synthetic,
                    True,
                )

            if self.loaded_iter:
                self.gaussians.load_ply(
                    os.path.join(
                        self.model_path,
                        "point_cloud",
                        "iteration_" + str(self.loaded_iter),
                        "point_cloud.ply",
                    ),
                    args.train_test_exp,
                )
            elif prepared_init_plys:
                init_mode = getattr(args, "init_mode", "merge")
                if init_mode == "replace":
                    if len(prepared_init_plys) != 1:
                        raise ValueError("replace init_mode supports exactly one prepared prior")
                    init_path = Path(prepared_init_plys[0])
                    prepared_asset_format = prepared_init_formats[0]
                    if prepared_asset_format == "gaussian":
                        self.gaussians.load_ply(str(init_path), args.train_test_exp)
                        initialize_loaded_prior(self.gaussians, train_cam_infos, self.cameras_extent)
                    elif prepared_asset_format == "point_cloud":
                        pcd = dataset_readers.fetchPly(str(init_path))
                        self.gaussians.create_from_pcd(pcd, train_cam_infos, self.cameras_extent)
                    else:
                        raise ValueError(f"Unsupported prepared asset format: {prepared_asset_format}")
                elif init_mode in {"merge", "weighted_merge", "filtered_merge"}:
                    merged_pcd = scene_info.point_cloud
                    updated_selected_priors: list[dict[str, Any]] = []
                    for init_path_value, init_format in zip(prepared_init_plys, prepared_init_formats):
                        index = len(updated_selected_priors)
                        prior_pcd = prepared_asset_to_point_cloud(Path(init_path_value), init_format)
                        metadata_item = (
                            dict(selected_priors_metadata[index])
                            if index < len(selected_priors_metadata)
                            else {
                                "aligned_prior": str(init_path_value),
                                "asset_format": init_format,
                            }
                        )
                        filtered_pcd, updated_item = apply_insertion_policy(
                            prior_pcd,
                            metadata_item,
                            init_mode=init_mode,
                        )
                        updated_selected_priors.append(updated_item)
                        if filtered_pcd is None:
                            continue
                        merged_pcd = merge_point_clouds(merged_pcd, filtered_pcd)
                    self.gaussians.create_from_pcd(merged_pcd, train_cam_infos, self.cameras_extent)
                    if updated_selected_priors:
                        write_prior_metadata(
                            Path(self.model_path),
                            selected_priors=updated_selected_priors,
                            init_mode=init_mode,
                        )
                else:
                    raise ValueError(f"Unsupported init_mode: {init_mode}")
            else:
                self.gaussians.create_from_pcd(scene_info.point_cloud, train_cam_infos, self.cameras_extent)

            save_initial_snapshot(self, args)

        def save(self, iteration):
            point_cloud_path = os.path.join(self.model_path, "point_cloud/iteration_{}".format(iteration))
            self.gaussians.save_ply(os.path.join(point_cloud_path, "point_cloud.ply"))
            exposure_dict = {
                image_name: self.gaussians.get_exposure_from_name(image_name).detach().cpu().numpy().tolist()
                for image_name in self.gaussians.exposure_mapping
            }
            with open(os.path.join(self.model_path, "exposure.json"), "w", encoding="utf-8") as file:
                json.dump(exposure_dict, file, indent=2)

        def getTrainCameras(self, scale=1.0):
            return self.train_cameras[scale]

        def getTestCameras(self, scale=1.0):
            return self.test_cameras[scale]

    return PriorInitScene


def write_render_compatible_cfg_args(model_path: Path, args: argparse.Namespace) -> None:
    allowed_keys = (
        "sh_degree",
        "source_path",
        "model_path",
        "images",
        "depths",
        "resolution",
        "white_background",
        "train_test_exp",
        "data_device",
        "max_train_cameras",
        "camera_quality_ratio",
        "camera_selection_seed",
        "eval",
        "convert_SHs_python",
        "compute_cov3D_python",
        "debug",
        "antialiasing",
    )
    payload = {
        key: getattr(args, key)
        for key in allowed_keys
        if hasattr(args, key)
    }
    cfg_args_path = model_path / "cfg_args"
    cfg_args_path.write_text(repr(argparse.Namespace(**payload)), encoding="utf-8")


def build_parser() -> tuple[argparse.ArgumentParser, Any, Any, Any]:
    parser = argparse.ArgumentParser(description="Train vanilla 3DGS with optional prior initialization.")
    parser.add_argument("--repo-path", required=True, type=Path)
    lp = ModelParams(parser)
    op = OptimizationParams(parser)
    pp = PipelineParams(parser)
    parser.add_argument("--ip", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6009)
    parser.add_argument("--debug_from", type=int, default=-1)
    parser.add_argument("--detect_anomaly", action="store_true", default=False)
    parser.add_argument("--test_iterations", nargs="+", type=int, default=[7_000, 30_000])
    parser.add_argument("--save_iterations", nargs="+", type=int, default=[7_000, 30_000])
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--disable_viewer", action="store_true", default=False)
    parser.add_argument("--save-initial-snapshot", action="store_true", default=False)
    parser.add_argument(
        "--initial-render-sets",
        nargs="+",
        choices=["train", "test"],
        default=("train", "test"),
    )
    parser.add_argument("--checkpoint_iterations", nargs="+", type=int, default=[])
    parser.add_argument("--start_checkpoint", type=str, default=None)
    parser.add_argument("--prior-ply", type=Path)
    parser.add_argument("--alignment-json", type=Path)
    parser.add_argument("--prior-object-id", type=str)
    parser.add_argument("--prior-score", type=float)
    parser.add_argument("--prior-spec-json", type=Path)
    parser.add_argument(
        "--init-mode",
        type=str,
        default="merge",
        choices=["merge", "replace", "weighted_merge", "filtered_merge"],
    )
    return parser, lp, op, pp


def main() -> int:
    parser, lp, op, pp = build_parser()
    args = parser.parse_args()
    args.repo_path = args.repo_path.resolve()

    prepared_init_ply = None
    prepared_asset_format = None
    if args.prior_ply is not None and args.prior_spec_json is not None:
        raise ValueError("--prior-ply and --prior-spec-json are mutually exclusive")

    if args.prior_spec_json is not None:
        args.prior_spec_json = args.prior_spec_json.resolve()
        model_path = Path(args.model_path).resolve()
        prior_specs = load_prior_specs(args.prior_spec_json)
        prepared = prepare_prior_assets(prior_specs, model_path)
        args.prepared_init_plys = [item["aligned_prior"] for item in prepared]
        args.prepared_init_formats = [item["asset_format"] for item in prepared]
        args.selected_priors_metadata = prepared
        write_prior_metadata(
            model_path,
            selected_priors=prepared,
            init_mode=args.init_mode,
        )
    elif args.prior_ply is not None:
        args.prior_ply = args.prior_ply.resolve()
        if args.alignment_json is not None:
            args.alignment_json = args.alignment_json.resolve()
        model_path = Path(args.model_path).resolve()
        prepared_init_ply, prepared_asset_format, alignment = prepare_prior_asset(
            args.prior_ply,
            args.alignment_json,
            model_path / "prior_init" / "aligned_prior.ply",
        )
        args.prepared_init_ply = str(prepared_init_ply)
        args.prepared_init_format = prepared_asset_format
        args.selected_priors_metadata = [
            {
                "source_prior": str(args.prior_ply),
                "aligned_prior": str(prepared_init_ply),
                "asset_format": prepared_asset_format,
                "alignment": alignment,
                "prior_object_id": args.prior_object_id,
                "prior_score": args.prior_score,
                "normalized_confidence": 1.0,
                "point_keep_ratio": 1.0,
                "dropped": False,
            }
        ]
        write_prior_metadata(
            model_path,
            selected_priors=list(args.selected_priors_metadata),
            init_mode=args.init_mode,
        )

    args.save_iterations.append(args.iterations)

    dataset = lp.extract(args)
    opt = op.extract(args)
    pipe = pp.extract(args)
    args.initial_snapshot_convert_shs_python = pipe.convert_SHs_python
    args.initial_snapshot_compute_cov3d_python = pipe.compute_cov3D_python
    args.initial_snapshot_debug = pipe.debug
    args.initial_snapshot_antialiasing = pipe.antialiasing

    if prepared_init_ply is not None:
        args.prepared_init_ply = str(prepared_init_ply)
        args.prepared_init_format = prepared_asset_format
    propagate_prior_runtime_args(dataset, args)

    scene_class = make_prior_init_scene()
    train_module.Scene = scene_class
    if not args.disable_viewer:
        train_module.network_gui.init(args.ip, args.port)
    torch.autograd.set_detect_anomaly(args.detect_anomaly)
    train_module.training(
        dataset,
        opt,
        pipe,
        args.test_iterations,
        args.save_iterations,
        args.checkpoint_iterations,
        args.start_checkpoint,
        args.debug_from,
    )
    write_render_compatible_cfg_args(Path(args.model_path).resolve(), args)
    print("\nTraining complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
