#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import os
import random
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
import torchvision
from plyfile import PlyData, PlyElement
from torch import nn
from utils.general_utils import build_rotation, inverse_sigmoid

from priorprobe.gaussian_affine import (
    detect_asset_format,
    parse_scale,
    transform_gaussian_vertex,
    transform_positions,
)
from priorprobe.gaussian_prior_diagnostics import (
    allocate_total_budget,
    expanded_aabb_from_positions,
    gaussian_positions,
    normalize_prior_sh_reset_mode,
    point_keep_mask_outside_aabbs,
    reset_gaussian_sh,
    stable_seed,
    subsample_structured_vertex,
)
from priorprobe.result_ply_naming import ensure_named_point_cloud, infer_experiment_name

train_module = importlib.import_module("train")
scene_module = importlib.import_module("scene")
dataset_readers = importlib.import_module("scene.dataset_readers")
arguments_module = importlib.import_module("arguments")
gaussian_renderer_module = importlib.import_module("gaussian_renderer")

ModelParams = arguments_module.ModelParams
OptimizationParams = arguments_module.OptimizationParams
PipelineParams = arguments_module.PipelineParams


PRIOR_TENSOR_GROUPS = ("xyz", "f_dc", "f_rest", "opacity", "scaling", "rotation")

GEOMETRY_VALIDATION_OUTSIDE_SCENE_PROXY_RATIO_THRESHOLD = 0.01
GEOMETRY_VALIDATION_MEAN_NN_THRESHOLD_M = 0.5
GEOMETRY_VALIDATION_MAX_PRIOR_POINTS = 2048
GEOMETRY_VALIDATION_MAX_SCENE_POINTS = 8192
GEOMETRY_VALIDATION_SCENE_BBOX_TOLERANCE_M = 0.01
GEOMETRY_VALIDATION_METADATA_ERROR_THRESHOLD_M = 0.05


def geometry_bbox_summary(xyz: np.ndarray) -> dict[str, Any]:
    points = np.asarray(xyz, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or points.shape[0] == 0:
        raise ValueError("xyz must be a non-empty Nx3 array")
    bbox_min = points.min(axis=0)
    bbox_max = points.max(axis=0)
    center = (bbox_min + bbox_max) * 0.5
    size = bbox_max - bbox_min
    bottom_center = np.asarray([center[0], center[1], bbox_min[2]], dtype=np.float64)
    return {
        "min": bbox_min.tolist(),
        "max": bbox_max.tolist(),
        "center": center.tolist(),
        "size": size.tolist(),
        "bottom_center": bottom_center.tolist(),
    }


def _sample_xyz(points: np.ndarray, *, max_points: int, seed: int) -> np.ndarray:
    xyz = np.asarray(points, dtype=np.float32)
    if xyz.shape[0] <= max_points:
        return xyz
    rng = np.random.default_rng(int(seed))
    indices = np.sort(rng.choice(xyz.shape[0], size=int(max_points), replace=False))
    return xyz[indices]


def _nearest_scene_proxy_distances(
    prior_xyz: np.ndarray,
    scene_xyz: np.ndarray,
    *,
    max_prior_points: int,
    max_scene_points: int,
    seed: int,
) -> np.ndarray:
    sampled_prior = _sample_xyz(prior_xyz, max_points=max_prior_points, seed=seed)
    sampled_scene = _sample_xyz(scene_xyz, max_points=max_scene_points, seed=seed + 1)
    prior_tensor = torch.from_numpy(sampled_prior).to(dtype=torch.float32, device="cpu")
    scene_tensor = torch.from_numpy(sampled_scene).to(dtype=torch.float32, device="cpu")
    distances = torch.cdist(prior_tensor, scene_tensor).min(dim=1).values
    return distances.cpu().numpy().astype(np.float64)


def validate_prior_geometry_against_scene_proxy(
    prior_xyz: np.ndarray,
    scene_xyz: np.ndarray,
    metadata_item: dict[str, Any] | None = None,
    *,
    outside_ratio_threshold: float = GEOMETRY_VALIDATION_OUTSIDE_SCENE_PROXY_RATIO_THRESHOLD,
    mean_nn_threshold_m: float = GEOMETRY_VALIDATION_MEAN_NN_THRESHOLD_M,
    max_prior_points: int = GEOMETRY_VALIDATION_MAX_PRIOR_POINTS,
    max_scene_points: int = GEOMETRY_VALIDATION_MAX_SCENE_POINTS,
    seed: int = 0,
) -> dict[str, Any]:
    prior_xyz = np.asarray(prior_xyz, dtype=np.float64)
    scene_xyz = np.asarray(scene_xyz, dtype=np.float64)
    prior_bbox = geometry_bbox_summary(prior_xyz)
    scene_bbox = geometry_bbox_summary(scene_xyz)
    scene_min = np.asarray(scene_bbox["min"], dtype=np.float64)
    scene_max = np.asarray(scene_bbox["max"], dtype=np.float64)
    outside_mask = np.any(
        (prior_xyz < scene_min[None, :]) | (prior_xyz > scene_max[None, :]),
        axis=1,
    )
    outside_ratio = float(outside_mask.mean()) if prior_xyz.size else 0.0
    nn_distances = _nearest_scene_proxy_distances(
        prior_xyz,
        scene_xyz,
        max_prior_points=max_prior_points,
        max_scene_points=max_scene_points,
        seed=int(seed),
    )
    debug = dict((metadata_item or {}).get("alignment_debug") or {})
    aligned_center = np.asarray(prior_bbox["center"], dtype=np.float64)
    aligned_bottom = np.asarray(prior_bbox["bottom_center"], dtype=np.float64)
    aligned_size = np.asarray(prior_bbox["size"], dtype=np.float64)
    bbox_tolerance_m = float(GEOMETRY_VALIDATION_SCENE_BBOX_TOLERANCE_M)
    bbox_min_tolerant = scene_min - bbox_tolerance_m
    bbox_max_tolerant = scene_max + bbox_tolerance_m
    target_center = np.asarray(debug.get("target_center"), dtype=np.float64) if debug.get("target_center") is not None else None
    target_bottom = np.asarray(debug.get("target_bottom_anchor"), dtype=np.float64) if debug.get("target_bottom_anchor") is not None else None
    target_size = np.asarray(debug.get("target_sizes"), dtype=np.float64) if debug.get("target_sizes") is not None else None
    fail_reasons: list[str] = []
    if outside_ratio > float(outside_ratio_threshold):
        fail_reasons.append("outside_scene_proxy")
    if np.any(aligned_center < bbox_min_tolerant) or np.any(aligned_center > bbox_max_tolerant):
        fail_reasons.append("outside_scene_proxy_center")
    if np.any(aligned_bottom < bbox_min_tolerant) or np.any(aligned_bottom > bbox_max_tolerant):
        fail_reasons.append("outside_scene_proxy_bottom")
    nn_mean = float(nn_distances.mean()) if nn_distances.size else 0.0
    if nn_mean > float(mean_nn_threshold_m):
        fail_reasons.append("floating_from_scene_proxy")
    target_center_error_m: float | None = None
    target_bottom_error_m: float | None = None
    target_size_delta: list[float] | None = None
    metadata_threshold_m = float(GEOMETRY_VALIDATION_METADATA_ERROR_THRESHOLD_M)
    metadata_contradiction = False
    if target_center is not None:
        target_center_error_m = float(np.linalg.norm(aligned_center - target_center))
        metadata_contradiction = metadata_contradiction or target_center_error_m > metadata_threshold_m
    if target_bottom is not None:
        target_bottom_error_m = float(np.linalg.norm(aligned_bottom - target_bottom))
        metadata_contradiction = metadata_contradiction or target_bottom_error_m > metadata_threshold_m
    if target_size is not None:
        target_size_delta = (aligned_size - target_size).tolist()
        metadata_contradiction = metadata_contradiction or any(
            abs(float(delta)) > metadata_threshold_m for delta in target_size_delta
        )
    if metadata_contradiction:
        fail_reasons.append("metadata_contradiction")
    payload = {
        "scene_proxy_bbox": scene_bbox,
        "actual_aligned_bbox": prior_bbox,
        "outside_scene_proxy_ratio": outside_ratio,
        "scene_proxy_mean_nn_distance_m": nn_mean,
        "scene_proxy_median_nn_distance_m": float(np.median(nn_distances)) if nn_distances.size else 0.0,
        "scene_proxy_p95_nn_distance_m": float(np.quantile(nn_distances, 0.95)) if nn_distances.size else 0.0,
        "scene_proxy_p99_nn_distance_m": float(np.quantile(nn_distances, 0.99)) if nn_distances.size else 0.0,
        "scene_proxy_frac_lt_0_05m": float((nn_distances < 0.05).mean()) if nn_distances.size else 0.0,
        "scene_proxy_frac_lt_0_10m": float((nn_distances < 0.10).mean()) if nn_distances.size else 0.0,
        "scene_proxy_frac_lt_0_20m": float((nn_distances < 0.20).mean()) if nn_distances.size else 0.0,
        "thresholds": {
            "outside_scene_proxy_ratio_threshold": float(outside_ratio_threshold),
            "mean_nn_threshold_m": float(mean_nn_threshold_m),
            "max_prior_points": int(max_prior_points),
            "max_scene_points": int(max_scene_points),
            "scene_bbox_tolerance_m": bbox_tolerance_m,
            "metadata_error_threshold_m": metadata_threshold_m,
        },
        "passed": not fail_reasons,
        "fail_reasons": fail_reasons,
    }
    if target_center_error_m is not None:
        payload["target_center_error_m"] = target_center_error_m
    if target_bottom_error_m is not None:
        payload["target_bottom_error_m"] = target_bottom_error_m
    if target_size_delta is not None:
        payload["target_size_delta"] = target_size_delta
    return payload


def validate_resolved_prior_geometry(
    prepared_init_plys: list[str],
    prepared_init_formats: list[str],
    selected_priors_metadata: list[dict[str, Any]],
    scene_point_cloud,
    *,
    base_seed: int,
    outside_ratio_threshold: float = GEOMETRY_VALIDATION_OUTSIDE_SCENE_PROXY_RATIO_THRESHOLD,
    mean_nn_threshold_m: float = GEOMETRY_VALIDATION_MEAN_NN_THRESHOLD_M,
    max_prior_points: int = GEOMETRY_VALIDATION_MAX_PRIOR_POINTS,
    max_scene_points: int = GEOMETRY_VALIDATION_MAX_SCENE_POINTS,
) -> tuple[list[dict[str, Any]], list[str]]:
    scene_xyz = np.asarray(scene_point_cloud.points, dtype=np.float64)
    annotated: list[dict[str, Any]] = []
    failures: list[str] = []
    for init_path_value, init_format, metadata_item in zip(
        prepared_init_plys,
        prepared_init_formats,
        selected_priors_metadata,
    ):
        prior_pcd = prepared_asset_to_point_cloud(Path(init_path_value), init_format)
        prior_xyz = np.asarray(prior_pcd.points, dtype=np.float64)
        updated_item = dict(metadata_item)
        validation = validate_prior_geometry_against_scene_proxy(
            prior_xyz,
            scene_xyz,
            updated_item,
            outside_ratio_threshold=outside_ratio_threshold,
            mean_nn_threshold_m=mean_nn_threshold_m,
            max_prior_points=max_prior_points,
            max_scene_points=max_scene_points,
            seed=prior_sample_seed(updated_item, base_seed=base_seed),
        )
        updated_item["geometry_validation"] = validation
        annotated.append(updated_item)
        if not validation["passed"]:
            failures.append(
                f"{updated_item.get('prior_object_id')}->{updated_item.get('target_object_id')}: {', '.join(validation['fail_reasons'])}"
            )
    return annotated, failures


def normalize_prior_protection_mode(value: str | None) -> str:
    normalized = str(value or "none").strip().lower()
    if normalized not in {"none", "freeze", "weak"}:
        raise ValueError(f"Unsupported prior protection mode: {value!r}")
    return normalized


def normalize_sfm_region_replacement_mode(value: str | None) -> str:
    normalized = str(value or "none").strip().lower()
    if normalized not in {"none", "aligned_prior_aabb_union"}:
        raise ValueError(f"Unsupported SfM region replacement mode: {value!r}")
    return normalized


def resolve_determinism_settings(args: argparse.Namespace) -> dict[str, Any]:
    seed = int(getattr(args, "seed", 42))
    camera_order_seed = getattr(args, "camera_order_seed", None)
    if camera_order_seed is None:
        camera_order_seed = seed
    return {
        "seed": seed,
        "camera_order_seed": int(camera_order_seed),
        "camera_shuffle_enabled": bool(getattr(args, "camera_shuffle_enabled", True)),
        "deterministic": bool(getattr(args, "deterministic", False)),
    }


def apply_determinism_settings(*, seed: int, deterministic: bool) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    if deterministic and hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def shuffle_camera_infos(
    train_cam_infos: list[Any],
    test_cam_infos: list[Any],
    *,
    enabled: bool,
    camera_order_seed: int,
) -> tuple[list[Any], list[Any]]:
    train_ordered = list(train_cam_infos)
    test_ordered = list(test_cam_infos)
    if not enabled:
        return train_ordered, test_ordered

    random.Random(int(camera_order_seed)).shuffle(train_ordered)
    random.Random(int(camera_order_seed) + 1).shuffle(test_ordered)
    return train_ordered, test_ordered


def build_prior_protection_config(args: argparse.Namespace) -> dict[str, Any]:
    mode = normalize_prior_protection_mode(getattr(args, "prior_protection_mode", "none"))
    lr_scale = float(getattr(args, "prior_lr_scale", 0.05))
    return {
        "mode": mode,
        "lr_scale": float(np.clip(lr_scale, 0.0, 1.0)),
        "protect_from_prune": bool(getattr(args, "protect_prior_from_prune", True)),
        "protect_from_densify": bool(getattr(args, "protect_prior_from_densify", True)),
    }


def build_geometry_validation_policy(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "outside_scene_proxy_ratio_threshold": float(
            getattr(
                args,
                "geometry_validation_outside_scene_proxy_ratio_threshold",
                GEOMETRY_VALIDATION_OUTSIDE_SCENE_PROXY_RATIO_THRESHOLD,
            )
        ),
        "mean_nn_threshold_m": float(
            getattr(
                args,
                "geometry_validation_mean_nn_threshold_m",
                GEOMETRY_VALIDATION_MEAN_NN_THRESHOLD_M,
            )
        ),
        "max_prior_points": int(
            getattr(args, "geometry_validation_max_prior_points", GEOMETRY_VALIDATION_MAX_PRIOR_POINTS)
        ),
        "max_scene_points": int(
            getattr(args, "geometry_validation_max_scene_points", GEOMETRY_VALIDATION_MAX_SCENE_POINTS)
        ),
        "scene_proxy_mode": "base_scene_point_cloud",
    }


def prior_protection_enabled(gaussians) -> bool:
    config = getattr(gaussians, "_prior_protection_config", None)
    if not config:
        return False
    if normalize_prior_protection_mode(config.get("mode")) == "none":
        return False
    mask = getattr(gaussians, "_prior_point_mask", None)
    return mask is not None and int(mask.numel()) > 0 and bool(mask.any().item())


def prior_point_mask(gaussians) -> torch.Tensor | None:
    if not prior_protection_enabled(gaussians):
        return None
    return getattr(gaussians, "_prior_point_mask", None)


def prior_lr_scale_for_group(gaussians, group_name: str) -> float:
    config = getattr(gaussians, "_prior_protection_config", None) or {}
    mode = normalize_prior_protection_mode(config.get("mode"))
    if mode == "freeze":
        return 0.0
    if mode == "weak":
        return float(config.get("lr_scale", 0.05))
    return 1.0


def broadcast_prior_mask(mask: torch.Tensor, tensor: torch.Tensor) -> torch.Tensor:
    view_shape = (mask.shape[0],) + (1,) * max(tensor.dim() - 1, 0)
    return mask.view(*view_shape)


def extend_prior_mask(gaussians, extra_count: int) -> None:
    if extra_count <= 0:
        return
    mask = getattr(gaussians, "_prior_point_mask", None)
    if mask is None:
        return
    extension = torch.zeros((int(extra_count),), dtype=torch.bool, device=mask.device)
    gaussians._prior_point_mask = torch.cat((mask, extension), dim=0)
    group_ids = getattr(gaussians, "_prior_group_ids", None)
    if group_ids is not None:
        group_extension = torch.full((int(extra_count),), -1, dtype=group_ids.dtype, device=group_ids.device)
        gaussians._prior_group_ids = torch.cat((group_ids, group_extension), dim=0)


def prune_prior_mask(gaussians, valid_points_mask: torch.Tensor) -> None:
    mask = getattr(gaussians, "_prior_point_mask", None)
    if mask is None:
        return
    gaussians._prior_point_mask = mask[valid_points_mask]
    group_ids = getattr(gaussians, "_prior_group_ids", None)
    if group_ids is not None:
        gaussians._prior_group_ids = group_ids[valid_points_mask]


def build_prior_group_summaries(gaussians) -> list[dict[str, Any]]:
    mask = getattr(gaussians, "_prior_point_mask", None)
    group_ids = getattr(gaussians, "_prior_group_ids", None)
    group_metadata = list(getattr(gaussians, "_prior_group_metadata", []))
    if mask is None or group_ids is None or not group_metadata:
        return []

    summaries: list[dict[str, Any]] = []
    for group_index, metadata in enumerate(group_metadata):
        group_mask = torch.logical_and(mask, group_ids == int(group_index))
        survived_count = int(group_mask.sum().item())
        inserted_count = int(
            metadata.get(
                "inserted_point_count",
                metadata.get("protected_point_count", metadata.get("kept_point_count", 0)),
            )
            or 0
        )
        summary = dict(metadata)
        summary["group_index"] = int(group_index)
        summary["inserted_point_count"] = inserted_count
        summary["survived_point_count"] = survived_count
        summary["survival_ratio"] = float(survived_count / inserted_count) if inserted_count > 0 else None
        summaries.append(summary)
    return summaries


def configure_prior_protection(gaussians, *, args: argparse.Namespace, selected_priors: list[dict[str, Any]]) -> None:
    config = build_prior_protection_config(args)
    total_count = int(gaussians.get_xyz.shape[0])
    mask = torch.zeros((total_count,), dtype=torch.bool, device="cuda")
    group_ids = torch.full((total_count,), -1, dtype=torch.int32, device="cuda")
    protected_ranges: list[dict[str, Any]] = []
    group_metadata: list[dict[str, Any]] = []
    for group_index, item in enumerate(selected_priors):
        start = item.get("protected_index_start")
        end = item.get("protected_index_end")
        if start is None or end is None:
            continue
        start_index = int(start)
        end_index = int(end)
        if start_index < 0 or end_index <= start_index or end_index > total_count:
            continue
        mask[start_index:end_index] = True
        group_ids[start_index:end_index] = int(group_index)
        protected_ranges.append(
            {
                "prior_object_id": item.get("prior_object_id"),
                "target_object_id": item.get("target_object_id"),
                "target_category": item.get("target_category"),
                "asset_format": item.get("asset_format"),
                "start_index": start_index,
                "end_index": end_index,
                "point_count": end_index - start_index,
            }
        )
        group_metadata.append(
            {
                "prior_object_id": item.get("prior_object_id"),
                "target_object_id": item.get("target_object_id"),
                "target_category": item.get("target_category"),
                "asset_format": item.get("asset_format"),
                "original_point_count": int(item.get("original_point_count", 0) or 0),
                "kept_point_count": int(item.get("kept_point_count", 0) or 0),
                "inserted_point_count": int(
                    item.get("inserted_point_count", item.get("kept_point_count", 0)) or 0
                ),
                "start_index": start_index,
                "end_index": end_index,
            }
        )
    gaussians._prior_protection_config = config
    gaussians._prior_point_mask = mask
    gaussians._prior_group_ids = group_ids
    gaussians._prior_group_metadata = group_metadata
    gaussians._prior_protected_ranges = protected_ranges


def save_gaussian_subset_ply(gaussians, *, mask: torch.Tensor, path: Path) -> None:
    mask_cpu = mask.detach().cpu().numpy().astype(bool, copy=False)
    if mask_cpu.size == 0 or not bool(mask_cpu.any()):
        return
    xyz = gaussians._xyz.detach().cpu().numpy()[mask_cpu]
    normals = np.zeros_like(xyz)
    f_dc = gaussians._features_dc.detach().transpose(1, 2).flatten(start_dim=1).contiguous().cpu().numpy()[mask_cpu]
    f_rest = gaussians._features_rest.detach().transpose(1, 2).flatten(start_dim=1).contiguous().cpu().numpy()[mask_cpu]
    opacities = gaussians._opacity.detach().cpu().numpy()[mask_cpu]
    scale = gaussians._scaling.detach().cpu().numpy()[mask_cpu]
    rotation = gaussians._rotation.detach().cpu().numpy()[mask_cpu]

    dtype_full = [(attribute, "f4") for attribute in gaussians.construct_list_of_attributes()]
    elements = np.empty(xyz.shape[0], dtype=dtype_full)
    attributes = np.concatenate((xyz, normals, f_dc, f_rest, opacities, scale, rotation), axis=1)
    elements[:] = list(map(tuple, attributes))
    path.parent.mkdir(parents=True, exist_ok=True)
    PlyData([PlyElement.describe(elements, "vertex")]).write(path)


def write_prior_protection_checkpoint(model_path: Path, iteration: int, gaussians) -> None:
    mask = getattr(gaussians, "_prior_point_mask", None)
    config = getattr(gaussians, "_prior_protection_config", None)
    if mask is None or config is None:
        return
    point_cloud_path = model_path / "point_cloud" / f"iteration_{iteration}"
    point_cloud_path.mkdir(parents=True, exist_ok=True)
    payload = {
        "iteration": int(iteration),
        "mode": config.get("mode"),
        "lr_scale": config.get("lr_scale"),
        "protect_from_prune": bool(config.get("protect_from_prune", True)),
        "protect_from_densify": bool(config.get("protect_from_densify", True)),
        "protected_point_count": int(mask.sum().item()),
        "total_point_count": int(gaussians.get_xyz.shape[0]),
        "protected_ranges": list(getattr(gaussians, "_prior_protected_ranges", [])),
        "group_summaries": build_prior_group_summaries(gaussians),
    }
    (point_cloud_path / "prior_protection.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    save_gaussian_subset_ply(
        gaussians,
        mask=mask,
        path=point_cloud_path / "prior_points.ply",
    )


class PriorProtectedOptimizer:
    def __init__(self, optimizer, gaussians) -> None:
        self._optimizer = optimizer
        self._gaussians = gaussians

    def step(self, *args, **kwargs):
        mask = prior_point_mask(self._gaussians)
        if mask is not None:
            for group in self._optimizer.param_groups:
                if not group.get("params"):
                    continue
                parameter = group["params"][0]
                grad = parameter.grad
                if grad is None or int(grad.shape[0]) != int(mask.shape[0]):
                    continue
                lr_scale = prior_lr_scale_for_group(self._gaussians, str(group.get("name", "")))
                if lr_scale >= 0.9999:
                    continue
                grad_mask = broadcast_prior_mask(mask, grad)
                scale_tensor = (~grad_mask).to(dtype=grad.dtype) + grad_mask.to(dtype=grad.dtype) * float(lr_scale)
                grad.mul_(scale_tensor)
        return self._optimizer.step(*args, **kwargs)

    def zero_grad(self, *args, **kwargs):
        return self._optimizer.zero_grad(*args, **kwargs)

    def __getattr__(self, name: str):
        return getattr(self._optimizer, name)


def install_prior_protection_hooks() -> None:
    gaussian_model_cls = scene_module.GaussianModel
    if getattr(gaussian_model_cls, "_prior_protection_hooks_installed", False):
        return

    original_training_setup = gaussian_model_cls.training_setup
    original_reset_opacity = gaussian_model_cls.reset_opacity
    original_prune_points = gaussian_model_cls.prune_points
    original_densification_postfix = gaussian_model_cls.densification_postfix
    original_densify_and_split = gaussian_model_cls.densify_and_split
    original_densify_and_clone = gaussian_model_cls.densify_and_clone

    def patched_training_setup(self, training_args):
        original_training_setup(self, training_args)
        if prior_protection_enabled(self):
            self.optimizer = PriorProtectedOptimizer(self.optimizer, self)

    def patched_reset_opacity(self):
        mask = prior_point_mask(self)
        config = getattr(self, "_prior_protection_config", None) or {}
        if mask is None or not bool(config.get("protect_from_prune", True)):
            return original_reset_opacity(self)
        current_opacity = self._opacity.detach().clone()
        opacities_new = inverse_sigmoid(
            torch.min(self.get_opacity, torch.ones_like(self.get_opacity) * 0.01)
        )
        opacities_new[mask] = current_opacity[mask]
        optimizable_tensors = self.replace_tensor_to_optimizer(opacities_new, "opacity")
        self._opacity = optimizable_tensors["opacity"]

    def patched_prune_points(self, mask):
        prior_mask = prior_point_mask(self)
        config = getattr(self, "_prior_protection_config", None) or {}
        prune_mask = mask.clone()
        if prior_mask is not None and bool(config.get("protect_from_prune", True)):
            prune_mask = torch.logical_and(prune_mask, ~prior_mask)
        valid_points_mask = ~prune_mask
        original_prune_points(self, prune_mask)
        prune_prior_mask(self, valid_points_mask)

    def patched_densification_postfix(self, new_xyz, new_features_dc, new_features_rest, new_opacities, new_scaling, new_rotation, new_tmp_radii):
        original_densification_postfix(
            self,
            new_xyz,
            new_features_dc,
            new_features_rest,
            new_opacities,
            new_scaling,
            new_rotation,
            new_tmp_radii,
        )
        extend_prior_mask(self, int(new_xyz.shape[0]))

    def patched_densify_and_split(self, grads, grad_threshold, scene_extent, N=2):
        n_init_points = self.get_xyz.shape[0]
        padded_grad = torch.zeros((n_init_points), device="cuda")
        padded_grad[:grads.shape[0]] = grads.squeeze()
        selected_pts_mask = torch.where(padded_grad >= grad_threshold, True, False)
        selected_pts_mask = torch.logical_and(
            selected_pts_mask,
            torch.max(self.get_scaling, dim=1).values > self.percent_dense * scene_extent,
        )
        prior_mask = prior_point_mask(self)
        config = getattr(self, "_prior_protection_config", None) or {}
        if prior_mask is not None and bool(config.get("protect_from_densify", True)):
            selected_pts_mask = torch.logical_and(selected_pts_mask, ~prior_mask)

        stds = self.get_scaling[selected_pts_mask].repeat(N, 1)
        means = torch.zeros((stds.size(0), 3), device="cuda")
        samples = torch.normal(mean=means, std=stds)
        rots = build_rotation(self._rotation[selected_pts_mask]).repeat(N, 1, 1)
        new_xyz = torch.bmm(rots, samples.unsqueeze(-1)).squeeze(-1) + self.get_xyz[selected_pts_mask].repeat(N, 1)
        new_scaling = self.scaling_inverse_activation(self.get_scaling[selected_pts_mask].repeat(N, 1) / (0.8 * N))
        new_rotation = self._rotation[selected_pts_mask].repeat(N, 1)
        new_features_dc = self._features_dc[selected_pts_mask].repeat(N, 1, 1)
        new_features_rest = self._features_rest[selected_pts_mask].repeat(N, 1, 1)
        new_opacity = self._opacity[selected_pts_mask].repeat(N, 1)
        new_tmp_radii = self.tmp_radii[selected_pts_mask].repeat(N)

        self.densification_postfix(new_xyz, new_features_dc, new_features_rest, new_opacity, new_scaling, new_rotation, new_tmp_radii)
        prune_filter = torch.cat(
            (
                selected_pts_mask,
                torch.zeros(N * int(selected_pts_mask.sum().item()), device="cuda", dtype=bool),
            )
        )
        self.prune_points(prune_filter)

    def patched_densify_and_clone(self, grads, grad_threshold, scene_extent):
        selected_pts_mask = torch.where(torch.norm(grads, dim=-1) >= grad_threshold, True, False)
        selected_pts_mask = torch.logical_and(
            selected_pts_mask,
            torch.max(self.get_scaling, dim=1).values <= self.percent_dense * scene_extent,
        )
        prior_mask = prior_point_mask(self)
        config = getattr(self, "_prior_protection_config", None) or {}
        if prior_mask is not None and bool(config.get("protect_from_densify", True)):
            selected_pts_mask = torch.logical_and(selected_pts_mask, ~prior_mask)

        new_xyz = self._xyz[selected_pts_mask]
        new_features_dc = self._features_dc[selected_pts_mask]
        new_features_rest = self._features_rest[selected_pts_mask]
        new_opacities = self._opacity[selected_pts_mask]
        new_scaling = self._scaling[selected_pts_mask]
        new_rotation = self._rotation[selected_pts_mask]
        new_tmp_radii = self.tmp_radii[selected_pts_mask]
        self.densification_postfix(
            new_xyz,
            new_features_dc,
            new_features_rest,
            new_opacities,
            new_scaling,
            new_rotation,
            new_tmp_radii,
        )

    gaussian_model_cls.training_setup = patched_training_setup
    gaussian_model_cls.reset_opacity = patched_reset_opacity
    gaussian_model_cls.prune_points = patched_prune_points
    gaussian_model_cls.densification_postfix = patched_densification_postfix
    gaussian_model_cls.densify_and_split = patched_densify_and_split
    gaussian_model_cls.densify_and_clone = patched_densify_and_clone
    gaussian_model_cls._prior_protection_hooks_installed = True


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
    scale_vec = parse_scale(alignment["scale"]).astype(np.float32)

    if asset_format == "gaussian":
        output_vertex = transform_gaussian_vertex(
            vertex,
            rotation_matrix=rotation_matrix,
            scale=scale_vec,
            translation=translation,
        )
    else:
        xyz = np.stack([vertex["x"], vertex["y"], vertex["z"]], axis=1).astype(np.float32)
        xyz = transform_positions(
            xyz,
            affine_matrix=rotation_matrix.astype(np.float64) @ np.diag(scale_vec.astype(np.float64)),
            translation=translation.astype(np.float64),
        ).astype(np.float32)
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


def prior_sample_seed(prepared_item: dict[str, Any], *, base_seed: int) -> int:
    return stable_seed(
        int(base_seed),
        prepared_item.get("target_object_id", ""),
        prepared_item.get("prior_object_id", ""),
        prepared_item.get("aligned_prior", ""),
    )


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
        updated["inserted_point_count"] = 0
        updated["dropped"] = True
        return None, updated

    if init_mode == "weighted_merge":
        sampled_pcd, original_count, kept_count = subsample_point_cloud(
            prior_pcd,
            keep_ratio=requested_keep_ratio,
            seed=prior_sample_seed(updated, base_seed=0),
        )
        updated["applied_point_keep_ratio"] = float(kept_count / max(original_count, 1))
        updated["kept_point_count"] = kept_count
        updated["inserted_point_count"] = kept_count
        updated["dropped"] = False
        return sampled_pcd, updated

    updated["applied_point_keep_ratio"] = 1.0
    updated["kept_point_count"] = original_count
    updated["inserted_point_count"] = original_count
    updated["dropped"] = False
    return prior_pcd, updated


def subsample_basic_point_cloud(point_cloud, *, keep_count: int, seed: int):
    xyz = np.asarray(point_cloud.points)
    colors = np.asarray(point_cloud.colors)
    normals = np.asarray(point_cloud.normals)
    original_count = int(xyz.shape[0])
    if original_count == 0:
        return point_cloud, 0, 0
    if keep_count <= 0:
        sampled = dataset_readers.BasicPointCloud(
            points=xyz[:0],
            colors=colors[:0],
            normals=normals[:0],
        )
        return sampled, original_count, 0
    if keep_count >= original_count:
        return point_cloud, original_count, original_count

    rng = np.random.default_rng(seed)
    indices = np.sort(rng.choice(original_count, size=int(keep_count), replace=False))
    sampled = dataset_readers.BasicPointCloud(
        points=xyz[indices],
        colors=colors[indices],
        normals=normals[indices],
    )
    return sampled, original_count, int(keep_count)


def filter_basic_point_cloud_outside_aabbs(base_pcd, aabbs: list[tuple[np.ndarray, np.ndarray]]):
    xyz = np.asarray(base_pcd.points)
    colors = np.asarray(base_pcd.colors)
    normals = np.asarray(base_pcd.normals)
    keep_mask = point_keep_mask_outside_aabbs(xyz.astype(np.float32, copy=False), aabbs)
    filtered = dataset_readers.BasicPointCloud(
        points=xyz[keep_mask],
        colors=colors[keep_mask],
        normals=normals[keep_mask],
    )
    removed_count = int(xyz.shape[0] - keep_mask.sum())
    removed_ratio = float(removed_count / max(int(xyz.shape[0]), 1))
    return filtered, removed_count, removed_ratio


def apply_gaussian_insertion_policy(
    vertex: np.ndarray,
    prepared_item: dict[str, Any],
    *,
    init_mode: str,
    keep_count_override: int | None,
    sh_reset_mode: str,
    base_seed: int,
):
    updated = dict(prepared_item)
    raw_score = updated.get("prior_score")
    normalized_confidence = float(updated.get("normalized_confidence", 1.0) or 0.0)
    requested_keep_ratio = float(updated.get("point_keep_ratio", 1.0) or 0.0)
    dropped = bool(updated.get("dropped", False))
    original_count = int(vertex.shape[0])

    updated["prior_score"] = float(raw_score) if raw_score is not None else None
    updated["normalized_confidence"] = normalized_confidence
    updated["requested_point_keep_ratio"] = requested_keep_ratio
    updated["original_point_count"] = original_count
    updated["prior_sh_reset_mode"] = normalize_prior_sh_reset_mode(sh_reset_mode)

    if dropped:
        updated["applied_point_keep_ratio"] = 0.0
        updated["kept_point_count"] = 0
        updated["inserted_point_count"] = 0
        updated["dropped"] = True
        return None, updated

    if init_mode != "merge":
        raise ValueError("Gaussian priors currently support init_mode='merge' or init_mode='replace' only")

    processed = reset_gaussian_sh(vertex, mode=sh_reset_mode)
    keep_count = original_count if keep_count_override is None else int(np.clip(keep_count_override, 0, original_count))
    if keep_count < original_count:
        processed = subsample_structured_vertex(
            processed,
            keep_count=keep_count,
            seed=prior_sample_seed(updated, base_seed=base_seed),
        )
    updated["applied_point_keep_ratio"] = float(keep_count / max(original_count, 1))
    updated["kept_point_count"] = int(processed.shape[0])
    updated["inserted_point_count"] = int(processed.shape[0])
    updated["dropped"] = False
    return processed, updated


def resolve_selected_prior_metadata_items(
    prepared_init_plys: list[str],
    prepared_init_formats: list[str],
    selected_priors_metadata: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for index, (init_path_value, init_format) in enumerate(zip(prepared_init_plys, prepared_init_formats)):
        if index < len(selected_priors_metadata):
            resolved.append(dict(selected_priors_metadata[index]))
            continue
        resolved.append(
            {
                "aligned_prior": str(init_path_value),
                "asset_format": init_format,
            }
        )
    return resolved


def initialize_loaded_prior(gaussians, train_cam_infos, cameras_extent: float) -> None:
    gaussians.spatial_lr_scale = cameras_extent
    gaussians.max_radii2D = torch.zeros((gaussians.get_xyz.shape[0]), device="cuda")
    gaussians.exposure_mapping = {cam_info.image_name: idx for idx, cam_info in enumerate(train_cam_infos)}
    if not hasattr(gaussians, "pretrained_exposures"):
        gaussians.pretrained_exposures = None
    exposure = torch.eye(3, 4, device="cuda")[None].repeat(len(train_cam_infos), 1, 1)
    gaussians._exposure = nn.Parameter(exposure.requires_grad_(True))


def gaussian_vertex_to_model_tensors(vertex: np.ndarray, *, max_sh_degree: int) -> dict[str, torch.Tensor]:
    xyz = np.stack(
        [
            np.asarray(vertex["x"], dtype=np.float32),
            np.asarray(vertex["y"], dtype=np.float32),
            np.asarray(vertex["z"], dtype=np.float32),
        ],
        axis=1,
    )
    opacities = np.asarray(vertex["opacity"], dtype=np.float32)[..., np.newaxis]

    features_dc = np.zeros((xyz.shape[0], 3, 1), dtype=np.float32)
    features_dc[:, 0, 0] = np.asarray(vertex["f_dc_0"], dtype=np.float32)
    features_dc[:, 1, 0] = np.asarray(vertex["f_dc_1"], dtype=np.float32)
    features_dc[:, 2, 0] = np.asarray(vertex["f_dc_2"], dtype=np.float32)

    extra_f_names = sorted(
        [name for name in (vertex.dtype.names or ()) if name.startswith("f_rest_")],
        key=lambda name: int(name.split("_")[-1]),
    )
    expected_rest = 3 * ((max_sh_degree + 1) ** 2 - 1)
    if len(extra_f_names) != expected_rest:
        raise ValueError(
            f"Gaussian SH degree mismatch: expected {expected_rest} f_rest fields, found {len(extra_f_names)}"
        )

    features_extra = np.zeros((xyz.shape[0], len(extra_f_names)), dtype=np.float32)
    for index, field_name in enumerate(extra_f_names):
        features_extra[:, index] = np.asarray(vertex[field_name], dtype=np.float32)
    features_extra = features_extra.reshape((xyz.shape[0], 3, (max_sh_degree + 1) ** 2 - 1))

    scales = np.stack(
        [
            np.asarray(vertex["scale_0"], dtype=np.float32),
            np.asarray(vertex["scale_1"], dtype=np.float32),
            np.asarray(vertex["scale_2"], dtype=np.float32),
        ],
        axis=1,
    )
    rotations = np.stack(
        [
            np.asarray(vertex["rot_0"], dtype=np.float32),
            np.asarray(vertex["rot_1"], dtype=np.float32),
            np.asarray(vertex["rot_2"], dtype=np.float32),
            np.asarray(vertex["rot_3"], dtype=np.float32),
        ],
        axis=1,
    )

    return {
        "xyz": torch.tensor(xyz, dtype=torch.float, device="cuda"),
        "f_dc": torch.tensor(features_dc, dtype=torch.float, device="cuda").transpose(1, 2).contiguous(),
        "f_rest": torch.tensor(features_extra, dtype=torch.float, device="cuda").transpose(1, 2).contiguous(),
        "opacity": torch.tensor(opacities, dtype=torch.float, device="cuda"),
        "scaling": torch.tensor(scales, dtype=torch.float, device="cuda"),
        "rotation": torch.tensor(rotations, dtype=torch.float, device="cuda"),
    }


def append_gaussian_vertex_to_model(gaussians, vertex: np.ndarray) -> None:
    tensors = gaussian_vertex_to_model_tensors(vertex, max_sh_degree=gaussians.max_sh_degree)
    gaussians._xyz = nn.Parameter(torch.cat((gaussians._xyz, tensors["xyz"]), dim=0).requires_grad_(True))
    gaussians._features_dc = nn.Parameter(
        torch.cat((gaussians._features_dc, tensors["f_dc"]), dim=0).requires_grad_(True)
    )
    gaussians._features_rest = nn.Parameter(
        torch.cat((gaussians._features_rest, tensors["f_rest"]), dim=0).requires_grad_(True)
    )
    gaussians._opacity = nn.Parameter(
        torch.cat((gaussians._opacity, tensors["opacity"]), dim=0).requires_grad_(True)
    )
    gaussians._scaling = nn.Parameter(
        torch.cat((gaussians._scaling, tensors["scaling"]), dim=0).requires_grad_(True)
    )
    gaussians._rotation = nn.Parameter(
        torch.cat((gaussians._rotation, tensors["rotation"]), dim=0).requires_grad_(True)
    )
    gaussians.active_sh_degree = gaussians.max_sh_degree
    gaussians.max_radii2D = torch.zeros((gaussians.get_xyz.shape[0]), device="cuda")


def write_prior_metadata(
    model_path: Path,
    *,
    selected_priors: list[dict[str, Any]],
    init_mode: str,
    prior_protection: dict[str, Any] | None = None,
    prior_sh_reset_mode: str = "none",
    prior_target_total_gaussians: int = 0,
    sfm_region_replacement_mode: str = "none",
    sfm_removed_point_count: int | None = None,
    sfm_removed_point_ratio: float | None = None,
    geometry_validation_policy: dict[str, Any] | None = None,
) -> None:
    metadata = {
        "selected_priors": selected_priors,
        "init_mode": init_mode,
        "prior_sh_reset_mode": str(prior_sh_reset_mode),
        "prior_target_total_gaussians": int(prior_target_total_gaussians),
        "sfm_region_replacement_mode": str(sfm_region_replacement_mode),
        "sfm_removed_point_count": int(sfm_removed_point_count) if sfm_removed_point_count is not None else None,
        "sfm_removed_point_ratio": float(sfm_removed_point_ratio) if sfm_removed_point_ratio is not None else None,
    }
    if prior_protection is not None:
        metadata["prior_protection"] = prior_protection
    if geometry_validation_policy is not None:
        metadata["geometry_validation_policy"] = geometry_validation_policy
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
    setattr(dataset, "seed", int(getattr(args, "seed", 42)))
    setattr(dataset, "camera_order_seed", int(getattr(args, "camera_order_seed", getattr(args, "seed", 42))))
    setattr(dataset, "camera_shuffle_enabled", bool(getattr(args, "camera_shuffle_enabled", True)))
    setattr(dataset, "deterministic", bool(getattr(args, "deterministic", False)))
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
    setattr(dataset, "prior_protection_mode", str(getattr(args, "prior_protection_mode", "none")))
    setattr(dataset, "prior_lr_scale", float(getattr(args, "prior_lr_scale", 0.05)))
    setattr(dataset, "prior_sh_reset_mode", str(getattr(args, "prior_sh_reset_mode", "none")))
    setattr(dataset, "prior_target_total_gaussians", int(getattr(args, "prior_target_total_gaussians", 0)))
    setattr(dataset, "prior_subsample_seed", int(getattr(args, "prior_subsample_seed", 42)))
    setattr(
        dataset,
        "sfm_region_replacement_mode",
        str(getattr(args, "sfm_region_replacement_mode", "none")),
    )
    setattr(dataset, "sfm_region_margin_scale", float(getattr(args, "sfm_region_margin_scale", 1.05)))
    setattr(dataset, "sfm_region_margin_min_m", float(getattr(args, "sfm_region_margin_min_m", 0.02)))
    setattr(
        dataset,
        "geometry_validation_outside_scene_proxy_ratio_threshold",
        float(
            getattr(
                args,
                "geometry_validation_outside_scene_proxy_ratio_threshold",
                GEOMETRY_VALIDATION_OUTSIDE_SCENE_PROXY_RATIO_THRESHOLD,
            )
        ),
    )
    setattr(
        dataset,
        "geometry_validation_mean_nn_threshold_m",
        float(
            getattr(
                args,
                "geometry_validation_mean_nn_threshold_m",
                GEOMETRY_VALIDATION_MEAN_NN_THRESHOLD_M,
            )
        ),
    )
    setattr(
        dataset,
        "geometry_validation_max_prior_points",
        int(getattr(args, "geometry_validation_max_prior_points", GEOMETRY_VALIDATION_MAX_PRIOR_POINTS)),
    )
    setattr(
        dataset,
        "geometry_validation_max_scene_points",
        int(getattr(args, "geometry_validation_max_scene_points", GEOMETRY_VALIDATION_MAX_SCENE_POINTS)),
    )
    setattr(dataset, "protect_prior_from_prune", bool(getattr(args, "protect_prior_from_prune", True)))
    setattr(dataset, "protect_prior_from_densify", bool(getattr(args, "protect_prior_from_densify", True)))


def make_prior_init_scene():
    class PriorInitScene:
        gaussians: Any

        def __init__(self, args, gaussians, load_iteration=None, shuffle=True, resolution_scales=[1.0]):
            self.model_path = args.model_path
            self.loaded_iter = None
            self.gaussians = gaussians
            self._prior_protection_mode = str(getattr(args, "prior_protection_mode", "none"))
            self._protect_prior_from_prune = bool(getattr(args, "protect_prior_from_prune", False))
            self._protect_prior_from_densify = bool(getattr(args, "protect_prior_from_densify", False))
            self._determinism = resolve_determinism_settings(args)

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

            train_cam_infos, test_cam_infos = shuffle_camera_infos(
                train_cam_infos,
                test_cam_infos,
                enabled=bool(shuffle) and self._determinism["camera_shuffle_enabled"],
                camera_order_seed=int(self._determinism["camera_order_seed"]),
            )

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
                protection_config = build_prior_protection_config(args)
                prior_sh_reset_mode = normalize_prior_sh_reset_mode(getattr(args, "prior_sh_reset_mode", "none"))
                prior_target_total_gaussians = max(int(getattr(args, "prior_target_total_gaussians", 0)), 0)
                prior_subsample_seed = int(getattr(args, "prior_subsample_seed", 42))
                sfm_region_replacement_mode = normalize_sfm_region_replacement_mode(
                    getattr(args, "sfm_region_replacement_mode", "none")
                )
                sfm_region_margin_scale = float(getattr(args, "sfm_region_margin_scale", 1.05))
                sfm_region_margin_min_m = float(getattr(args, "sfm_region_margin_min_m", 0.02))
                geometry_validation_policy = build_geometry_validation_policy(args)
                resolved_metadata_items = resolve_selected_prior_metadata_items(
                    prepared_init_plys,
                    prepared_init_formats,
                    selected_priors_metadata,
                )
                validated_metadata_items, geometry_failures = validate_resolved_prior_geometry(
                    prepared_init_plys,
                    prepared_init_formats,
                    resolved_metadata_items,
                    scene_info.point_cloud,
                    base_seed=prior_subsample_seed,
                    outside_ratio_threshold=float(geometry_validation_policy["outside_scene_proxy_ratio_threshold"]),
                    mean_nn_threshold_m=float(geometry_validation_policy["mean_nn_threshold_m"]),
                    max_prior_points=int(geometry_validation_policy["max_prior_points"]),
                    max_scene_points=int(geometry_validation_policy["max_scene_points"]),
                )
                if geometry_failures:
                    write_prior_metadata(
                        Path(self.model_path),
                        selected_priors=validated_metadata_items,
                        init_mode=init_mode,
                        prior_protection=protection_config,
                        prior_sh_reset_mode=prior_sh_reset_mode,
                        prior_target_total_gaussians=prior_target_total_gaussians,
                        sfm_region_replacement_mode=sfm_region_replacement_mode,
                        geometry_validation_policy=geometry_validation_policy,
                    )
                    raise ValueError(
                        "Prior geometry validation failed against scene proxy: "
                        + "; ".join(geometry_failures)
                    )
                if init_mode == "replace":
                    if len(prepared_init_plys) != 1:
                        raise ValueError("replace init_mode supports exactly one prepared prior")
                    init_path = Path(prepared_init_plys[0])
                    prepared_asset_format = prepared_init_formats[0]
                    current_selected_priors = [dict(item) for item in validated_metadata_items]
                    if prepared_asset_format == "gaussian":
                        self.gaussians.load_ply(str(init_path), args.train_test_exp)
                        initialize_loaded_prior(self.gaussians, train_cam_infos, self.cameras_extent)
                    elif prepared_asset_format == "point_cloud":
                        pcd = dataset_readers.fetchPly(str(init_path))
                        self.gaussians.create_from_pcd(pcd, train_cam_infos, self.cameras_extent)
                    else:
                        raise ValueError(f"Unsupported prepared asset format: {prepared_asset_format}")
                    total_points = int(self.gaussians.get_xyz.shape[0])
                    if current_selected_priors:
                        current_selected_priors[0]["protected_index_start"] = 0
                        current_selected_priors[0]["protected_index_end"] = total_points
                        current_selected_priors[0]["protected_point_count"] = total_points
                        current_selected_priors[0]["inserted_point_count"] = total_points
                    configure_prior_protection(
                        self.gaussians,
                        args=args,
                        selected_priors=current_selected_priors,
                    )
                    write_prior_metadata(
                        Path(self.model_path),
                        selected_priors=current_selected_priors,
                        init_mode=init_mode,
                        prior_protection=protection_config,
                        prior_sh_reset_mode=prior_sh_reset_mode,
                        prior_target_total_gaussians=prior_target_total_gaussians,
                        sfm_region_replacement_mode=sfm_region_replacement_mode,
                        geometry_validation_policy=geometry_validation_policy,
                    )
                elif init_mode in {"merge", "weighted_merge", "filtered_merge"}:
                    merged_pcd = scene_info.point_cloud
                    base_point_count = int(np.asarray(scene_info.point_cloud.points).shape[0])
                    current_point_index = base_point_count
                    sfm_removed_point_count = 0
                    sfm_removed_point_ratio = 0.0
                    gaussian_vertices_to_append: list[tuple[np.ndarray, dict[str, Any]]] = []
                    gaussian_original_counts: list[int] = []
                    gaussian_raw_entries: list[tuple[np.ndarray, dict[str, Any]]] = []
                    updated_selected_priors: list[dict[str, Any]] = []
                    for (init_path_value, init_format), metadata_item in zip(
                        zip(prepared_init_plys, prepared_init_formats),
                        validated_metadata_items,
                    ):
                        if init_format == "gaussian":
                            gaussian_vertex = np.array(
                                PlyData.read(Path(init_path_value))["vertex"].data,
                                copy=True,
                            )
                            gaussian_original_counts.append(int(gaussian_vertex.shape[0]))
                            gaussian_raw_entries.append((gaussian_vertex, metadata_item))
                            continue

                        prior_pcd = prepared_asset_to_point_cloud(Path(init_path_value), init_format)
                        filtered_pcd, updated_item = apply_insertion_policy(
                            prior_pcd,
                            metadata_item,
                            init_mode=init_mode,
                        )
                        if filtered_pcd is None:
                            updated_item["protected_index_start"] = None
                            updated_item["protected_index_end"] = None
                            updated_item["protected_point_count"] = 0
                            updated_item["inserted_point_count"] = 0
                            updated_selected_priors.append(updated_item)
                            continue
                        kept_point_count = int(np.asarray(filtered_pcd.points).shape[0])
                        updated_item["protected_index_start"] = current_point_index
                        updated_item["protected_index_end"] = current_point_index + kept_point_count
                        updated_item["protected_point_count"] = kept_point_count
                        updated_item["inserted_point_count"] = kept_point_count
                        current_point_index += kept_point_count
                        updated_selected_priors.append(updated_item)
                        merged_pcd = merge_point_clouds(merged_pcd, filtered_pcd)
                    gaussian_keep_counts = allocate_total_budget(
                        gaussian_original_counts,
                        prior_target_total_gaussians,
                    )
                    if prior_target_total_gaussians <= 0:
                        gaussian_keep_counts = [None for _ in gaussian_original_counts]
                    for gaussian_index, (gaussian_vertex, metadata_item) in enumerate(gaussian_raw_entries):
                        keep_override = (
                            gaussian_keep_counts[gaussian_index]
                            if gaussian_index < len(gaussian_keep_counts)
                            else None
                        )
                        filtered_vertex, updated_item = apply_gaussian_insertion_policy(
                            gaussian_vertex,
                            metadata_item,
                            init_mode=init_mode,
                            keep_count_override=keep_override,
                            sh_reset_mode=prior_sh_reset_mode,
                            base_seed=prior_subsample_seed,
                        )
                        if filtered_vertex is None:
                            updated_item["protected_index_start"] = None
                            updated_item["protected_index_end"] = None
                            updated_item["protected_point_count"] = 0
                            updated_item["inserted_point_count"] = 0
                            updated_selected_priors.append(updated_item)
                            continue
                        updated_item["protected_point_count"] = int(filtered_vertex.shape[0])
                        updated_item["inserted_point_count"] = int(filtered_vertex.shape[0])
                        gaussian_vertices_to_append.append((filtered_vertex, updated_item))
                        updated_selected_priors.append(updated_item)
                    if gaussian_vertices_to_append and sfm_region_replacement_mode == "aligned_prior_aabb_union":
                        aabbs = [
                            expanded_aabb_from_positions(
                                gaussian_positions(vertex),
                                margin_scale=sfm_region_margin_scale,
                                margin_min_m=sfm_region_margin_min_m,
                            )
                            for vertex, _ in gaussian_vertices_to_append
                            if int(vertex.shape[0]) > 0
                        ]
                        if aabbs:
                            merged_pcd, sfm_removed_point_count, sfm_removed_point_ratio = filter_basic_point_cloud_outside_aabbs(
                                merged_pcd,
                                aabbs,
                            )
                    self.gaussians.create_from_pcd(merged_pcd, train_cam_infos, self.cameras_extent)
                    current_gaussian_index = int(self.gaussians.get_xyz.shape[0])
                    for gaussian_vertex, updated_item in gaussian_vertices_to_append:
                        point_count = int(gaussian_vertex.shape[0])
                        updated_item["protected_index_start"] = current_gaussian_index
                        updated_item["protected_index_end"] = current_gaussian_index + point_count
                        updated_item["protected_point_count"] = point_count
                        updated_item["inserted_point_count"] = point_count
                        append_gaussian_vertex_to_model(self.gaussians, gaussian_vertex)
                        current_gaussian_index += point_count
                    configure_prior_protection(
                        self.gaussians,
                        args=args,
                        selected_priors=updated_selected_priors,
                    )
                    if updated_selected_priors:
                        write_prior_metadata(
                            Path(self.model_path),
                            selected_priors=updated_selected_priors,
                            init_mode=init_mode,
                            prior_protection=protection_config,
                            prior_sh_reset_mode=prior_sh_reset_mode,
                            prior_target_total_gaussians=prior_target_total_gaussians,
                            sfm_region_replacement_mode=sfm_region_replacement_mode,
                            sfm_removed_point_count=sfm_removed_point_count,
                            sfm_removed_point_ratio=sfm_removed_point_ratio,
                            geometry_validation_policy=geometry_validation_policy,
                        )
                else:
                    raise ValueError(f"Unsupported init_mode: {init_mode}")
            else:
                self.gaussians.create_from_pcd(scene_info.point_cloud, train_cam_infos, self.cameras_extent)

            save_initial_snapshot(self, args)

        def save(self, iteration):
            point_cloud_path = Path(self.model_path) / "point_cloud" / f"iteration_{iteration}"
            self.gaussians.save_ply(str(point_cloud_path / "point_cloud.ply"))
            ensure_named_point_cloud(
                iteration_dir=point_cloud_path,
                experiment_name=infer_experiment_name(Path(self.model_path)),
                iteration=int(iteration),
                protection_mode=self._prior_protection_mode,
                protect_from_prune=self._protect_prior_from_prune,
                protect_from_densify=self._protect_prior_from_densify,
            )
            write_prior_protection_checkpoint(Path(self.model_path), int(iteration), self.gaussians)
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
        "seed",
        "camera_order_seed",
        "camera_shuffle_enabled",
        "deterministic",
        "geometry_validation_outside_scene_proxy_ratio_threshold",
        "geometry_validation_mean_nn_threshold_m",
        "geometry_validation_max_prior_points",
        "geometry_validation_max_scene_points",
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
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--camera-order-seed", type=int, default=None)
    parser.add_argument("--camera-shuffle", dest="camera_shuffle_enabled", action="store_true", default=True)
    parser.add_argument("--no-camera-shuffle", dest="camera_shuffle_enabled", action="store_false")
    parser.add_argument("--deterministic", action="store_true", default=False)
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
    parser.add_argument(
        "--prior-protection-mode",
        type=str,
        default="none",
        choices=["none", "freeze", "weak"],
    )
    parser.add_argument("--prior-lr-scale", type=float, default=0.05)
    parser.add_argument("--prior-sh-reset-mode", type=str, default="none", choices=["none", "zero_all"])
    parser.add_argument("--prior-target-total-gaussians", type=int, default=0)
    parser.add_argument("--prior-subsample-seed", type=int, default=42)
    parser.add_argument(
        "--sfm-region-replacement-mode",
        type=str,
        default="none",
        choices=["none", "aligned_prior_aabb_union"],
    )
    parser.add_argument("--sfm-region-margin-scale", type=float, default=1.05)
    parser.add_argument("--sfm-region-margin-min-m", type=float, default=0.02)
    parser.add_argument(
        "--geometry-validation-outside-scene-proxy-ratio-threshold",
        type=float,
        default=GEOMETRY_VALIDATION_OUTSIDE_SCENE_PROXY_RATIO_THRESHOLD,
    )
    parser.add_argument(
        "--geometry-validation-mean-nn-threshold-m",
        type=float,
        default=GEOMETRY_VALIDATION_MEAN_NN_THRESHOLD_M,
    )
    parser.add_argument(
        "--geometry-validation-max-prior-points",
        type=int,
        default=GEOMETRY_VALIDATION_MAX_PRIOR_POINTS,
    )
    parser.add_argument(
        "--geometry-validation-max-scene-points",
        type=int,
        default=GEOMETRY_VALIDATION_MAX_SCENE_POINTS,
    )
    parser.add_argument("--protect-prior-from-prune", action="store_true", default=True)
    parser.add_argument("--no-protect-prior-from-prune", dest="protect_prior_from_prune", action="store_false")
    parser.add_argument("--protect-prior-from-densify", action="store_true", default=True)
    parser.add_argument("--no-protect-prior-from-densify", dest="protect_prior_from_densify", action="store_false")
    return parser, lp, op, pp


def main() -> int:
    parser, lp, op, pp = build_parser()
    args = parser.parse_args()
    args.repo_path = args.repo_path.resolve()
    determinism = resolve_determinism_settings(args)
    args.seed = determinism["seed"]
    args.camera_order_seed = determinism["camera_order_seed"]
    args.camera_shuffle_enabled = determinism["camera_shuffle_enabled"]
    args.deterministic = determinism["deterministic"]
    apply_determinism_settings(seed=args.seed, deterministic=args.deterministic)
    geometry_validation_policy = build_geometry_validation_policy(args)

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
            prior_sh_reset_mode=args.prior_sh_reset_mode,
            prior_target_total_gaussians=args.prior_target_total_gaussians,
            sfm_region_replacement_mode=args.sfm_region_replacement_mode,
            geometry_validation_policy=geometry_validation_policy,
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
            prior_sh_reset_mode=args.prior_sh_reset_mode,
            prior_target_total_gaussians=args.prior_target_total_gaussians,
            sfm_region_replacement_mode=args.sfm_region_replacement_mode,
            geometry_validation_policy=geometry_validation_policy,
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
    install_prior_protection_hooks()

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
