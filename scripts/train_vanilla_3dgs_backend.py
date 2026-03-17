#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import sys
import types
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
from plyfile import PlyData, PlyElement
from torch import nn

train_module = importlib.import_module("train")
scene_module = importlib.import_module("scene")
dataset_readers = importlib.import_module("scene.dataset_readers")
arguments_module = importlib.import_module("arguments")

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


def parse_scale(scale_value: Any) -> tuple[np.ndarray, float]:
    if isinstance(scale_value, (int, float)):
        scalar = float(scale_value)
        return np.asarray([scalar, scalar, scalar], dtype=np.float32), scalar

    scale = np.asarray(scale_value, dtype=np.float32)
    if scale.shape != (3,):
        raise ValueError("scale must be a scalar or a 3-vector")
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


def prepare_prior_asset(prior_ply: Path, alignment_json: Path | None, output_path: Path) -> tuple[Path, str, dict[str, Any]]:
    alignment = load_alignment_spec(alignment_json)
    rotation_matrix = np.asarray(alignment["rotation_matrix"], dtype=np.float32)
    translation = np.asarray(alignment["translation"], dtype=np.float32)
    scale_vec, scale_scalar = parse_scale(alignment["scale"])

    ply = PlyData.read(prior_ply)
    vertex = np.array(ply["vertex"].data, copy=True)
    asset_format = detect_asset_format(vertex)

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
        if scale_scalar <= 0.0:
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
    source_prior: Path,
    aligned_prior: Path,
    asset_format: str,
    alignment: dict[str, Any],
    prior_object_id: str | None,
    prior_score: float | None,
) -> None:
    metadata = {
        "source_prior": str(source_prior),
        "aligned_prior": str(aligned_prior),
        "asset_format": asset_format,
        "alignment": alignment,
        "prior_object_id": prior_object_id,
        "prior_score": prior_score,
    }
    metadata_path = model_path / "prior_init" / "metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


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

            if os.path.exists(os.path.join(args.source_path, "sparse")):
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

            if not self.loaded_iter:
                input_ply = Path(getattr(args, "prepared_init_ply", scene_info.ply_path))
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

            prepared_init_ply = getattr(args, "prepared_init_ply", None)
            prepared_asset_format = getattr(args, "prepared_init_format", None)

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
            elif prepared_init_ply is not None:
                init_path = Path(prepared_init_ply)
                if prepared_asset_format == "gaussian":
                    self.gaussians.load_ply(str(init_path), args.train_test_exp)
                    initialize_loaded_prior(self.gaussians, train_cam_infos, self.cameras_extent)
                elif prepared_asset_format == "point_cloud":
                    pcd = dataset_readers.fetchPly(str(init_path))
                    self.gaussians.create_from_pcd(pcd, train_cam_infos, self.cameras_extent)
                else:
                    raise ValueError(f"Unsupported prepared asset format: {prepared_asset_format}")
            else:
                self.gaussians.create_from_pcd(scene_info.point_cloud, train_cam_infos, self.cameras_extent)

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
    parser.add_argument("--checkpoint_iterations", nargs="+", type=int, default=[])
    parser.add_argument("--start_checkpoint", type=str, default=None)
    parser.add_argument("--prior-ply", type=Path)
    parser.add_argument("--alignment-json", type=Path)
    parser.add_argument("--prior-object-id", type=str)
    parser.add_argument("--prior-score", type=float)
    return parser, lp, op, pp


def main() -> int:
    parser, lp, op, pp = build_parser()
    args = parser.parse_args()
    args.repo_path = args.repo_path.resolve()

    prepared_init_ply = None
    prepared_asset_format = None
    if args.prior_ply is not None:
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
        write_prior_metadata(
            model_path,
            source_prior=args.prior_ply,
            aligned_prior=prepared_init_ply,
            asset_format=prepared_asset_format,
            alignment=alignment,
            prior_object_id=args.prior_object_id,
            prior_score=args.prior_score,
        )

    args.save_iterations.append(args.iterations)

    dataset = lp.extract(args)
    opt = op.extract(args)
    pipe = pp.extract(args)

    if prepared_init_ply is not None:
        setattr(dataset, "prepared_init_ply", str(prepared_init_ply))
        setattr(dataset, "prepared_init_format", prepared_asset_format)

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
    print("\nTraining complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
