from __future__ import annotations

import importlib
import json
import math
import sys
import types
from argparse import Namespace
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image, ImageDraw
from plyfile import PlyData
from torch import nn

from priorprobe.replica_export import ReplicaHabitatRenderer, ReplicaPointRenderer
from priorprobe.replica_surface import ColmapCameraModel, load_colmap_text_frames

ROOT = Path(__file__).resolve().parents[3]


Decision = str


@dataclass(slots=True)
class ValidationThresholds:
    mask_iou: float = 0.50
    bbox_iou: float = 0.60
    centroid_px: float = 15.0
    edge_px: float = 12.0
    min_views: int = 3
    min_visible_pixel_ratio: float = 0.001
    depth_visibility_epsilon_m: float = 0.02
    sample_count: int = 1_000_000
    apply_binary_closing: bool = True
    severe_outlier_mask_iou: float = 0.10
    severe_outlier_centroid_px: float = 50.0
    severe_outlier_edge_px: float = 50.0
    ambiguous_iou_margin: float = 0.05
    ambiguous_bbox_iou_margin: float = 0.05
    ambiguous_centroid_margin_px: float = 3.0
    ambiguous_edge_margin_px: float = 3.0


@dataclass(slots=True)
class PriorRenderFrame:
    rgb: np.ndarray
    depth: np.ndarray


@dataclass(slots=True)
class CameraView:
    image_name: str
    position: np.ndarray
    rotation_cam2world: np.ndarray


@dataclass(slots=True)
class PositionValidationInputs:
    backend_run_dir: Path
    backend_run_json_path: Path | None
    prior_metadata_path: Path | None
    prior_specs_path: Path | None
    backend_run: dict[str, Any]
    prior_metadata: dict[str, Any] | None
    prior_specs: list[dict[str, Any]] | None
    scene_id: str
    dataset_family: str
    scene_root: Path
    semantic_scene_root: Path
    repo_path: Path
    cfg_args_path: Path
    cfg_args: Namespace
    camera_model: ColmapCameraModel
    test_views: list[CameraView]
    train_view_names: list[str]
    target_object_ids: list[int]
    selected_priors: list[dict[str, Any]]
    geometry_validation_context: dict[str, Any]
    renderer_capabilities: dict[str, Any]
    input_consistency: dict[str, Any]
    sfm_region_replacement_mode: str


@dataclass(slots=True)
class PositionValidationResult:
    decision: Decision
    summary: dict[str, Any]
    per_object_metrics: dict[str, Any]
    per_view_metrics: dict[str, Any]
    output_dir: Path | None = None


@dataclass(slots=True)
class _BackendModules:
    train_module: Any
    scene_module: Any
    dataset_readers: Any
    gaussian_renderer_module: Any


def _load_json(path: Path) -> dict[str, Any] | list[Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_cfg_args(path: Path) -> Namespace:
    namespace = eval(path.read_text(encoding="utf-8").strip(), {"Namespace": Namespace}, {})
    if not isinstance(namespace, Namespace):
        raise ValueError(f"Expected Namespace in cfg_args, got {type(namespace)!r}")
    return namespace


def _fallback_cfg_args(backend_run_dir: Path, scene_root: Path) -> Namespace:
    return Namespace(
        source_path=str(scene_root),
        model_path=str(backend_run_dir),
        images="images",
        depths="",
        train_test_exp=False,
        eval=True,
        sh_degree=3,
    )


def _placeholder_camera_model() -> ColmapCameraModel:
    return ColmapCameraModel(width=0, height=0, fx=0.0, fy=0.0, cx=0.0, cy=0.0)


def resolve_aligned_prior_path(path_value: str | Path, backend_run_dir: Path) -> Path:
    aligned_path = Path(path_value)
    if aligned_path.exists():
        return aligned_path
    fallback = backend_run_dir / "prior_init" / aligned_path.name
    if fallback.exists():
        return fallback
    return aligned_path


def _derive_backend_run_json_path(backend_run_dir: Path) -> Path | None:
    backend_root = ROOT / "outputs" / "gaussian_direct" / "backend_runs"
    experiments_root = ROOT / "outputs" / "gaussian_direct" / "experiments"
    try:
        relative = backend_run_dir.resolve().relative_to(backend_root.resolve())
    except ValueError:
        return None
    candidate = experiments_root / relative / "backend_run.json"
    if candidate.exists():
        return candidate
    return None


def _normalize_selected_priors(prior_entries: list[dict[str, Any]], backend_run_dir: Path) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for entry in prior_entries:
        item = dict(entry)
        if item.get("aligned_prior") is not None:
            item["aligned_prior"] = str(resolve_aligned_prior_path(item["aligned_prior"], backend_run_dir).resolve())
        normalized.append(item)
    return normalized


def _input_mismatch_payload(reasons: list[str], extras: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"status": "INPUT_MISMATCH", "reasons": list(reasons)}
    if extras:
        payload.update(extras)
    return payload


def _ok_payload(extras: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"status": "OK", "reasons": []}
    if extras:
        payload.update(extras)
    return payload


def _dataset_family_from_backend_run(backend_run: dict[str, Any], scene_root: Path) -> str:
    source_path = str(scene_root)
    if "replica_colmap_multi_roomwide_v2_384_surface_rgb_roomcontained" in source_path:
        return "replica_multi_roomwide_v2_384_surface_rgb_roomcontained"
    if "replica_colmap_multi_roomwide_v2_384_surface_rgb" in source_path:
        return "replica_multi_roomwide_v2_384_surface_rgb"
    dataset_scene = backend_run.get("dataset_scene") or {}
    return str(dataset_scene.get("format") or backend_run.get("dataset_name") or "unknown")


def _resolve_semantic_scene_root(scene_root: Path) -> Path:
    direct_mesh = scene_root / "habitat" / "mesh_semantic.ply"
    if direct_mesh.exists():
        return scene_root
    scene_meta_path = scene_root / "scene_meta.json"
    if scene_meta_path.exists():
        scene_meta = _load_json(scene_meta_path)
        if isinstance(scene_meta, dict):
            for key in ("raw_scene_root", "reference_scene_root"):
                candidate_root = scene_meta.get(key)
                if not candidate_root:
                    continue
                candidate_path = Path(str(candidate_root)).resolve()
                if (candidate_path / "habitat" / "mesh_semantic.ply").exists():
                    return candidate_path
    return scene_root


def _compute_hfov_deg(camera_model: ColmapCameraModel) -> float:
    return math.degrees(2.0 * math.atan(float(camera_model.width) / (2.0 * float(camera_model.fx))))


def _install_dummy_network_gui() -> None:
    if "gaussian_renderer.network_gui" in sys.modules:
        return
    module = types.ModuleType("gaussian_renderer.network_gui")
    module.conn = None
    module.addr = None
    module.listener = None
    module.init = lambda *args, **kwargs: None
    module.try_connect = lambda *args, **kwargs: None
    module.receive = lambda *args, **kwargs: (None, None, None, None, None, None)
    module.send = lambda *args, **kwargs: None
    sys.modules["gaussian_renderer.network_gui"] = module


def _load_backend_modules(repo_path: Path) -> _BackendModules:
    _install_dummy_network_gui()
    repo_path = repo_path.resolve()
    if str(repo_path) not in sys.path:
        sys.path.insert(0, str(repo_path))
    train_module = importlib.import_module("train")
    scene_module = importlib.import_module("scene")
    dataset_readers = importlib.import_module("scene.dataset_readers")
    gaussian_renderer_module = importlib.import_module("gaussian_renderer")
    return _BackendModules(
        train_module=train_module,
        scene_module=scene_module,
        dataset_readers=dataset_readers,
        gaussian_renderer_module=gaussian_renderer_module,
    )


def _load_scene_info(modules: _BackendModules, cfg_args: Namespace):
    source_path = str(getattr(cfg_args, "source_path"))
    images = str(getattr(cfg_args, "images", "images"))
    depths = str(getattr(cfg_args, "depths", ""))
    train_test_exp = bool(getattr(cfg_args, "train_test_exp", False))
    if (Path(source_path) / "sparse" / "0" / "test.txt").exists():
        return modules.dataset_readers.readColmapSceneInfo(
            source_path,
            images,
            depths,
            True,
            train_test_exp,
            llffhold=0,
        )
    return modules.scene_module.sceneLoadTypeCallbacks["Colmap"](
        source_path,
        images,
        depths,
        bool(getattr(cfg_args, "eval", True)),
        train_test_exp,
    )


def _build_camera_views(scene_root: Path) -> tuple[ColmapCameraModel, list[CameraView], list[str]]:
    camera_model, frames = load_colmap_text_frames(scene_root)
    test_views = [
        CameraView(
            image_name=frame.image_name,
            position=np.asarray(frame.position, dtype=np.float32),
            rotation_cam2world=np.asarray(frame.rotation_cam2world, dtype=np.float32),
        )
        for frame in frames
        if frame.split == "test"
    ]
    train_names = [frame.image_name for frame in frames if frame.split == "train"]
    return camera_model, test_views, train_names


def _validate_selected_prior_mapping(
    selected_priors: list[dict[str, Any]],
    prior_specs: list[dict[str, Any]] | None,
) -> list[str]:
    reasons: list[str] = []
    if prior_specs is None:
        return reasons
    if len(selected_priors) != len(prior_specs):
        reasons.append(
            f"selected_priors/prior_specs length mismatch: {len(selected_priors)} vs {len(prior_specs)}"
        )
        return reasons
    for index, (selected, spec) in enumerate(zip(selected_priors, prior_specs, strict=False)):
        selected_target = selected.get("target_object_id")
        spec_target = spec.get("target_object_id")
        if selected_target is not None and spec_target is not None and int(selected_target) != int(spec_target):
            reasons.append(
                f"target_object_id mismatch at index {index}: {selected_target} vs {spec_target}"
            )
        selected_category = selected.get("target_category")
        spec_category = spec.get("target_category")
        if (
            selected_category is not None
            and spec_category is not None
            and str(selected_category) != str(spec_category)
        ):
            reasons.append(
                f"target_category mismatch at index {index}: {selected_category} vs {spec_category}"
            )
    return reasons


def resolve_position_validation_inputs(backend_run_dir: Path) -> PositionValidationInputs:
    backend_run_dir = backend_run_dir.resolve()
    cfg_args_path = backend_run_dir / "cfg_args"
    backend_run_json_path = _derive_backend_run_json_path(backend_run_dir)
    backend_run = _load_json(backend_run_json_path) if backend_run_json_path and backend_run_json_path.exists() else {}
    assert isinstance(backend_run, dict)
    cfg_args_parse_error: Exception | None = None
    cfg_args_loaded = False
    cfg_args: Namespace
    if cfg_args_path.exists():
        try:
            cfg_args = _parse_cfg_args(cfg_args_path)
            cfg_args_loaded = True
        except Exception as exc:  # pragma: no cover - exercised through mismatch payloads
            cfg_args_parse_error = exc
            cfg_args = Namespace()
    else:
        cfg_args = Namespace()
    prior_metadata_path = backend_run_dir / "prior_init" / "metadata.json"
    prior_metadata = _load_json(prior_metadata_path) if prior_metadata_path.exists() else None
    if prior_metadata is not None and not isinstance(prior_metadata, dict):
        raise ValueError(f"Expected dict prior metadata in {prior_metadata_path}")
    prior_specs_path: Path | None = None
    if isinstance(backend_run.get("prior_spec_json"), str):
        prior_specs_path = Path(str(backend_run["prior_spec_json"]))
    elif backend_run_json_path is not None:
        candidate = backend_run_json_path.parent / "prior_specs.json"
        if candidate.exists():
            prior_specs_path = candidate
    prior_specs = None
    if prior_specs_path is not None and prior_specs_path.exists():
        loaded = _load_json(prior_specs_path)
        if not isinstance(loaded, list):
            raise ValueError(f"Expected list prior specs in {prior_specs_path}")
        prior_specs = loaded

    scene_root_value = (
        backend_run.get("dataset_scene", {}).get("source_path")
        or backend_run.get("source_path")
        or getattr(cfg_args, "source_path", None)
    )
    scene_root = Path(str(scene_root_value)).resolve() if scene_root_value else backend_run_dir
    if not cfg_args_loaded:
        cfg_args = _fallback_cfg_args(backend_run_dir, scene_root)
    semantic_scene_root = _resolve_semantic_scene_root(scene_root)
    repo_path = Path(str(backend_run.get("repo_path") or ROOT.parent / "3DGS" / "gaussian-splatting")).resolve()
    scene_id = str(backend_run.get("dataset_scene", {}).get("scene_id") or backend_run_dir.name)

    selected_priors_source = []
    if prior_metadata and isinstance(prior_metadata.get("selected_priors"), list):
        selected_priors_source = list(prior_metadata["selected_priors"])
    elif isinstance(backend_run.get("selected_priors"), list):
        selected_priors_source = list(backend_run["selected_priors"])
    selected_priors = _normalize_selected_priors(selected_priors_source, backend_run_dir)
    target_object_ids = [int(item["target_object_id"]) for item in selected_priors if item.get("target_object_id") is not None]

    mismatch_reasons: list[str] = []
    if not cfg_args_path.exists():
        mismatch_reasons.append(f"cfg_args missing: {cfg_args_path}")
    elif cfg_args_parse_error is not None:
        mismatch_reasons.append(f"cfg_args parse failed: {cfg_args_path} ({cfg_args_parse_error})")
    if scene_root_value is None:
        mismatch_reasons.append("scene_root unresolved from backend_run/cfg_args")
    if backend_run and Path(str(backend_run.get("model_path"))).resolve() != backend_run_dir:
        mismatch_reasons.append(
            f"backend_run model_path mismatch: {backend_run.get('model_path')} != {backend_run_dir}"
        )
    if cfg_args_loaded and Path(str(getattr(cfg_args, "source_path"))).resolve() != scene_root:
        mismatch_reasons.append(
            f"cfg_args source_path mismatch: {getattr(cfg_args, 'source_path')} != {scene_root}"
        )
    if str(scene_id) != str(backend_run.get("dataset_scene", {}).get("scene_id", scene_id)):
        mismatch_reasons.append(
            f"scene id mismatch: {scene_id} vs {backend_run.get('dataset_scene', {}).get('scene_id')}"
        )
    if selected_priors and prior_specs_path is None:
        mismatch_reasons.append("prior_specs.json missing for prior run")
    if selected_priors and prior_metadata is None:
        mismatch_reasons.append("prior_init/metadata.json missing for prior run")
    mismatch_reasons.extend(_validate_selected_prior_mapping(selected_priors, prior_specs))
    for index, item in enumerate(selected_priors):
        aligned = item.get("aligned_prior")
        if aligned is None:
            mismatch_reasons.append(f"selected_prior[{index}] aligned_prior missing")
            continue
        if not Path(str(aligned)).exists():
            mismatch_reasons.append(f"aligned prior missing: {aligned}")

    camera_model = _placeholder_camera_model()
    test_views: list[CameraView] = []
    train_view_names: list[str] = []
    if scene_root_value is not None:
        try:
            camera_model, test_views, train_view_names = _build_camera_views(scene_root)
        except Exception as exc:
            mismatch_reasons.append(f"failed to parse COLMAP views from {scene_root}: {exc}")
    if scene_root_value is not None and not test_views:
        mismatch_reasons.append(f"No test views parsed from {scene_root / 'sparse/0/images.txt'}")

    input_consistency = (
        _ok_payload(
            {
                "backend_run_json_path": str(backend_run_json_path) if backend_run_json_path else None,
                "prior_metadata_path": str(prior_metadata_path) if prior_metadata_path.exists() else None,
                "prior_specs_path": str(prior_specs_path) if prior_specs_path else None,
            }
        )
        if not mismatch_reasons
        else _input_mismatch_payload(
            mismatch_reasons,
            {
                "backend_run_json_path": str(backend_run_json_path) if backend_run_json_path else None,
                "prior_metadata_path": str(prior_metadata_path) if prior_metadata_path.exists() else None,
                "prior_specs_path": str(prior_specs_path) if prior_specs_path else None,
            },
        )
    )

    geometry_validation_context = {}
    if prior_metadata:
        geometry_validation_context = {
            "sfm_region_replacement_mode": prior_metadata.get("sfm_region_replacement_mode"),
            "geometry_validation_policy": prior_metadata.get("geometry_validation_policy"),
        }
    elif backend_run:
        geometry_validation_context = {
            "sfm_region_replacement_mode": backend_run.get("prior_insertion", {}).get("sfm_region_replacement_mode")
        }

    return PositionValidationInputs(
        backend_run_dir=backend_run_dir,
        backend_run_json_path=backend_run_json_path,
        prior_metadata_path=prior_metadata_path if prior_metadata_path.exists() else None,
        prior_specs_path=prior_specs_path,
        backend_run=backend_run,
        prior_metadata=prior_metadata,
        prior_specs=prior_specs,
        scene_id=scene_id,
        dataset_family=_dataset_family_from_backend_run(backend_run, scene_root),
        scene_root=scene_root,
        semantic_scene_root=semantic_scene_root,
        repo_path=repo_path,
        cfg_args_path=cfg_args_path,
        cfg_args=cfg_args,
        camera_model=camera_model,
        test_views=test_views,
        train_view_names=train_view_names,
        target_object_ids=target_object_ids,
        selected_priors=selected_priors,
        geometry_validation_context=geometry_validation_context,
        renderer_capabilities={"depth_available": True},
        input_consistency=input_consistency,
        sfm_region_replacement_mode=str(
            geometry_validation_context.get("sfm_region_replacement_mode")
            or backend_run.get("prior_insertion", {}).get("sfm_region_replacement_mode")
            or "none"
        ),
    )


class _SemanticRenderBundle:
    def __init__(self, masks: dict[int, dict[str, np.ndarray]], rgbs: dict[str, np.ndarray], backend_name: str):
        self.masks = masks
        self.rgbs = rgbs
        self.backend_name = backend_name


def _binary_dilate(mask: np.ndarray) -> np.ndarray:
    padded = np.pad(mask.astype(bool), 1, mode="constant", constant_values=False)
    out = np.zeros_like(mask, dtype=bool)
    for dy in range(3):
        for dx in range(3):
            out |= padded[dy : dy + mask.shape[0], dx : dx + mask.shape[1]]
    return out


def _binary_erode(mask: np.ndarray) -> np.ndarray:
    padded = np.pad(mask.astype(bool), 1, mode="constant", constant_values=False)
    out = np.ones_like(mask, dtype=bool)
    for dy in range(3):
        for dx in range(3):
            out &= padded[dy : dy + mask.shape[0], dx : dx + mask.shape[1]]
    return out


def _binary_closing(mask: np.ndarray) -> np.ndarray:
    return _binary_erode(_binary_dilate(mask))


def _render_gt_semantic_bundle(
    inputs: PositionValidationInputs,
    *,
    sample_count: int,
    apply_binary_closing: bool,
) -> _SemanticRenderBundle:
    hfov_deg = _compute_hfov_deg(inputs.camera_model)
    backend_name = "habitat_sim"
    try:
        renderer = ReplicaHabitatRenderer(
            inputs.semantic_scene_root,
            width=inputs.camera_model.width,
            height=inputs.camera_model.height,
            hfov_deg=hfov_deg,
        )
    except RuntimeError:
        renderer = ReplicaPointRenderer(
            inputs.semantic_scene_root,
            width=inputs.camera_model.width,
            height=inputs.camera_model.height,
            hfov_deg=hfov_deg,
            sample_count=sample_count,
            seed=0,
        )
        backend_name = "semantic_point_renderer"

    masks: dict[int, dict[str, np.ndarray]] = {int(obj_id): {} for obj_id in inputs.target_object_ids}
    rgbs: dict[str, np.ndarray] = {}
    try:
        for view in inputs.test_views:
            rgb, semantic = renderer.render(position=view.position, rotation_cam2world=view.rotation_cam2world)
            rgbs[view.image_name] = np.asarray(rgb).copy()
            for obj_id in inputs.target_object_ids:
                mask = np.asarray(semantic == int(obj_id), dtype=bool)
                if apply_binary_closing:
                    mask = _binary_closing(mask)
                masks[int(obj_id)][view.image_name] = mask
    finally:
        renderer.close()
    return _SemanticRenderBundle(masks=masks, rgbs=rgbs, backend_name=backend_name)


def generate_gt_semantic_masks(
    inputs: PositionValidationInputs,
    *,
    sample_count: int = 1_000_000,
    apply_binary_closing: bool = True,
) -> dict[int, dict[str, np.ndarray]]:
    bundle = _render_gt_semantic_bundle(
        inputs,
        sample_count=sample_count,
        apply_binary_closing=apply_binary_closing,
    )
    return bundle.masks


def _gaussian_vertex_to_model_tensors(vertex: np.ndarray, *, max_sh_degree: int) -> dict[str, torch.Tensor]:
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
    device = "cuda"
    return {
        "xyz": torch.tensor(xyz, dtype=torch.float32, device=device),
        "f_dc": torch.tensor(features_dc, dtype=torch.float32, device=device).transpose(1, 2).contiguous(),
        "f_rest": torch.tensor(features_extra, dtype=torch.float32, device=device).transpose(1, 2).contiguous(),
        "opacity": torch.tensor(opacities, dtype=torch.float32, device=device),
        "scaling": torch.tensor(scales, dtype=torch.float32, device=device),
        "rotation": torch.tensor(rotations, dtype=torch.float32, device=device),
    }


def _append_gaussian_vertex_to_model(gaussians, vertex: np.ndarray) -> None:
    tensors = _gaussian_vertex_to_model_tensors(vertex, max_sh_degree=gaussians.max_sh_degree)
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


def _initialize_loaded_prior(gaussians, train_view_names: list[str], cameras_extent: float) -> None:
    gaussians.spatial_lr_scale = float(cameras_extent)
    gaussians.max_radii2D = torch.zeros((gaussians.get_xyz.shape[0]), device="cuda")
    gaussians.exposure_mapping = {name: idx for idx, name in enumerate(train_view_names)}
    if not hasattr(gaussians, "pretrained_exposures"):
        gaussians.pretrained_exposures = None
    exposure = torch.eye(3, 4, device="cuda")[None].repeat(max(len(train_view_names), 1), 1, 1)
    gaussians._exposure = nn.Parameter(exposure.requires_grad_(True))


def _build_render_context(inputs: PositionValidationInputs) -> tuple[_BackendModules, Any, list[Any], float, bool]:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for prior position rendering")
    modules = _load_backend_modules(inputs.repo_path)
    scene_info = _load_scene_info(modules, inputs.cfg_args)
    test_cameras = modules.scene_module.cameraList_from_camInfos(
        scene_info.test_cameras,
        1.0,
        inputs.cfg_args,
        scene_info.is_nerf_synthetic,
        True,
    )
    train_view_names = [cam.image_name for cam in scene_info.train_cameras]
    cameras_extent = float(scene_info.nerf_normalization["radius"])
    separate_sh = bool(getattr(modules.train_module, "SPARSE_ADAM_AVAILABLE", False))
    return modules, train_view_names, test_cameras, cameras_extent, separate_sh


def _render_gaussian_model_views(
    gaussians,
    *,
    modules: _BackendModules,
    test_cameras: list[Any],
    cfg_args: Namespace,
    separate_sh: bool,
) -> dict[str, PriorRenderFrame]:
    pipeline = types.SimpleNamespace(
        convert_SHs_python=bool(getattr(cfg_args, "initial_snapshot_convert_shs_python", False)),
        compute_cov3D_python=bool(getattr(cfg_args, "initial_snapshot_compute_cov3d_python", False)),
        debug=bool(getattr(cfg_args, "initial_snapshot_debug", False)),
        antialiasing=False,
    )
    background = torch.tensor([0.0, 0.0, 0.0], dtype=torch.float32, device="cuda")
    renders: dict[str, PriorRenderFrame] = {}
    for camera in test_cameras:
        render_pkg = modules.gaussian_renderer_module.render(
            camera,
            gaussians,
            pipeline,
            background,
            use_trained_exp=bool(getattr(cfg_args, "train_test_exp", False)),
            separate_sh=separate_sh,
        )
        if "depth" not in render_pkg:
            raise RuntimeError("gaussian renderer does not expose depth")
        rgb_tensor = render_pkg["render"].detach().clamp(0.0, 1.0).permute(1, 2, 0).cpu().numpy()
        rgb = (rgb_tensor * 255.0).round().astype(np.uint8)
        depth = np.asarray(render_pkg["depth"].detach().cpu().numpy(), dtype=np.float32)
        depth = np.squeeze(depth)
        if depth.ndim != 2:
            raise RuntimeError(f"Unexpected depth shape for view {camera.image_name}: {depth.shape}")
        renders[str(camera.image_name)] = PriorRenderFrame(rgb=rgb, depth=depth)
    return renders


def _load_gaussian_from_aligned_paths(
    aligned_paths: list[Path],
    *,
    modules: _BackendModules,
    sh_degree: int,
    train_view_names: list[str],
    cameras_extent: float,
    train_test_exp: bool,
):
    gaussians = modules.scene_module.GaussianModel(int(sh_degree))
    if not aligned_paths:
        raise ValueError("No aligned prior paths provided")
    gaussians.load_ply(str(aligned_paths[0]), train_test_exp)
    for path in aligned_paths[1:]:
        vertex = np.array(PlyData.read(path)["vertex"].data, copy=True)
        _append_gaussian_vertex_to_model(gaussians, vertex)
    _initialize_loaded_prior(gaussians, train_view_names, cameras_extent)
    return gaussians


def render_full_prior_views(inputs: PositionValidationInputs) -> dict[str, PriorRenderFrame]:
    aligned_paths = [Path(str(item["aligned_prior"])) for item in inputs.selected_priors]
    modules, train_view_names, test_cameras, cameras_extent, separate_sh = _build_render_context(inputs)
    gaussians = _load_gaussian_from_aligned_paths(
        aligned_paths,
        modules=modules,
        sh_degree=int(getattr(inputs.cfg_args, "sh_degree", 3)),
        train_view_names=train_view_names,
        cameras_extent=cameras_extent,
        train_test_exp=bool(getattr(inputs.cfg_args, "train_test_exp", False)),
    )
    return _render_gaussian_model_views(
        gaussians,
        modules=modules,
        test_cameras=test_cameras,
        cfg_args=inputs.cfg_args,
        separate_sh=separate_sh,
    )


def render_isolated_prior_views(inputs: PositionValidationInputs) -> dict[int, dict[str, PriorRenderFrame]]:
    modules, train_view_names, test_cameras, cameras_extent, separate_sh = _build_render_context(inputs)
    renders: dict[int, dict[str, PriorRenderFrame]] = {}
    for item in inputs.selected_priors:
        object_id = int(item["target_object_id"])
        gaussians = _load_gaussian_from_aligned_paths(
            [Path(str(item["aligned_prior"]))],
            modules=modules,
            sh_degree=int(getattr(inputs.cfg_args, "sh_degree", 3)),
            train_view_names=train_view_names,
            cameras_extent=cameras_extent,
            train_test_exp=bool(getattr(inputs.cfg_args, "train_test_exp", False)),
        )
        renders[object_id] = _render_gaussian_model_views(
            gaussians,
            modules=modules,
            test_cameras=test_cameras,
            cfg_args=inputs.cfg_args,
            separate_sh=separate_sh,
        )
    return renders


def build_visible_prior_masks(
    full_renders: dict[str, PriorRenderFrame],
    isolated_renders: dict[int, dict[str, PriorRenderFrame]],
    *,
    depth_visibility_epsilon_m: float = 0.02,
) -> dict[int, dict[str, np.ndarray]]:
    masks: dict[int, dict[str, np.ndarray]] = {}
    for object_id, view_map in isolated_renders.items():
        object_masks: dict[str, np.ndarray] = {}
        for view_name, isolated_frame in view_map.items():
            if view_name not in full_renders:
                raise ValueError(f"Missing full prior render for view {view_name}")
            full_depth = np.asarray(full_renders[view_name].depth, dtype=np.float32)
            isolated_depth = np.asarray(isolated_frame.depth, dtype=np.float32)
            isolated_candidate = isolated_depth > 0.0
            visible = isolated_candidate & (np.abs(isolated_depth - full_depth) <= float(depth_visibility_epsilon_m))
            object_masks[view_name] = visible.astype(bool)
        masks[int(object_id)] = object_masks
    return masks


def _bbox_from_mask(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.nonzero(mask)
    if ys.size == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def _mask_iou(left: np.ndarray, right: np.ndarray) -> float:
    union = np.logical_or(left, right).sum()
    if union == 0:
        return 1.0
    return float(np.logical_and(left, right).sum() / union)


def _bbox_iou(left_bbox: tuple[int, int, int, int] | None, right_bbox: tuple[int, int, int, int] | None) -> float:
    if left_bbox is None and right_bbox is None:
        return 1.0
    if left_bbox is None or right_bbox is None:
        return 0.0
    lx0, ly0, lx1, ly1 = left_bbox
    rx0, ry0, rx1, ry1 = right_bbox
    ix0 = max(lx0, rx0)
    iy0 = max(ly0, ry0)
    ix1 = min(lx1, rx1)
    iy1 = min(ly1, ry1)
    iw = max(ix1 - ix0 + 1, 0)
    ih = max(iy1 - iy0 + 1, 0)
    intersection = iw * ih
    left_area = max(lx1 - lx0 + 1, 0) * max(ly1 - ly0 + 1, 0)
    right_area = max(rx1 - rx0 + 1, 0) * max(ry1 - ry0 + 1, 0)
    union = left_area + right_area - intersection
    if union <= 0:
        return 1.0
    return float(intersection / union)


def _centroid(mask: np.ndarray) -> np.ndarray | None:
    ys, xs = np.nonzero(mask)
    if ys.size == 0:
        return None
    return np.asarray([xs.mean(), ys.mean()], dtype=np.float64)


def _centroid_distance(mask_left: np.ndarray, mask_right: np.ndarray) -> float:
    left = _centroid(mask_left)
    right = _centroid(mask_right)
    if left is None and right is None:
        return 0.0
    if left is None or right is None:
        return float("inf")
    return float(np.linalg.norm(left - right))


def _boundary_points(mask: np.ndarray, *, max_points: int = 1024) -> np.ndarray:
    eroded = _binary_erode(mask)
    boundary = mask & ~eroded
    coords = np.argwhere(boundary)
    if coords.size == 0:
        return np.zeros((0, 2), dtype=np.float32)
    coords = coords[:, [1, 0]].astype(np.float32)
    if coords.shape[0] > max_points:
        indices = np.linspace(0, coords.shape[0] - 1, num=max_points, dtype=int)
        coords = coords[indices]
    return coords


def _symmetric_contour_chamfer(mask_left: np.ndarray, mask_right: np.ndarray) -> float:
    left = _boundary_points(mask_left)
    right = _boundary_points(mask_right)
    if left.shape[0] == 0 and right.shape[0] == 0:
        return 0.0
    if left.shape[0] == 0 or right.shape[0] == 0:
        return float("inf")
    left_tensor = torch.from_numpy(left)
    right_tensor = torch.from_numpy(right)
    distances = torch.cdist(left_tensor, right_tensor)
    left_min = distances.min(dim=1).values.mean().item()
    right_min = distances.min(dim=0).values.mean().item()
    return float((left_min + right_min) * 0.5)


def _float_or_none(value: float) -> float | None:
    if math.isfinite(value):
        return float(value)
    return None


def _load_overlay_rgb(scene_root: Path, fallback_rgbs: dict[str, np.ndarray], image_name: str) -> np.ndarray:
    candidate = scene_root / "images" / image_name
    if candidate.exists():
        return np.asarray(Image.open(candidate).convert("RGB"))
    return np.asarray(fallback_rgbs[image_name]).copy()


def compute_position_metrics(
    gt_masks: dict[int, dict[str, np.ndarray]],
    prior_masks: dict[int, dict[str, np.ndarray]],
    *,
    min_visible_pixel_ratio: float = 0.001,
) -> dict[int, dict[str, Any]]:
    object_results: dict[int, dict[str, Any]] = {}
    for object_id, gt_view_map in gt_masks.items():
        prior_view_map = prior_masks.get(int(object_id), {})
        views: dict[str, Any] = {}
        valid_entries: list[dict[str, Any]] = []
        gt_low_confidence_count = 0
        for view_name, gt_mask in gt_view_map.items():
            prior_mask = np.asarray(prior_view_map.get(view_name, np.zeros_like(gt_mask, dtype=bool)), dtype=bool)
            gt_mask = np.asarray(gt_mask, dtype=bool)
            gt_visible_pixels = int(gt_mask.sum())
            prior_visible_pixels = int(prior_mask.sum())
            total_pixels = int(gt_mask.size)
            gt_visible_ratio = float(gt_visible_pixels / total_pixels) if total_pixels else 0.0
            prior_visible_ratio = float(prior_visible_pixels / total_pixels) if total_pixels else 0.0
            record: dict[str, Any] = {
                "status": "valid",
                "gt_visible_pixels": gt_visible_pixels,
                "gt_visible_ratio": gt_visible_ratio,
                "prior_visible_pixels": prior_visible_pixels,
                "prior_visible_ratio": prior_visible_ratio,
                "gt_mask_low_confidence": False,
                "reasons": [],
            }
            if gt_visible_ratio < float(min_visible_pixel_ratio):
                record["status"] = "ignored_occluded"
                record["reasons"].append("gt_visible_ratio_below_min")
                views[view_name] = record
                continue

            gt_components = _connected_component_count(gt_mask)
            if gt_components > 8:
                record["gt_mask_low_confidence"] = True
                record["reasons"].append("gt_mask_low_confidence")
                gt_low_confidence_count += 1

            gt_bbox = _bbox_from_mask(gt_mask)
            prior_bbox = _bbox_from_mask(prior_mask)
            mask_iou = _mask_iou(gt_mask, prior_mask)
            bbox_iou = _bbox_iou(gt_bbox, prior_bbox)
            centroid_distance = _centroid_distance(gt_mask, prior_mask)
            edge_distance = _symmetric_contour_chamfer(gt_mask, prior_mask)
            coverage_ratio = float(np.logical_and(gt_mask, prior_mask).sum() / max(gt_visible_pixels, 1))
            record.update(
                {
                    "mask_iou": mask_iou,
                    "bbox_iou": bbox_iou,
                    "centroid_distance_px": _float_or_none(centroid_distance),
                    "edge_distance_px": _float_or_none(edge_distance),
                    "coverage_ratio": coverage_ratio,
                    "gt_bbox": list(gt_bbox) if gt_bbox is not None else None,
                    "prior_bbox": list(prior_bbox) if prior_bbox is not None else None,
                }
            )
            if prior_visible_pixels == 0:
                record["reasons"].append("prior_mask_empty")
            views[view_name] = record
            valid_entries.append(record)

        object_results[int(object_id)] = {
            "views": views,
            "valid_view_count": len(valid_entries),
            "ignored_view_count": sum(1 for item in views.values() if item["status"] == "ignored_occluded"),
            "invalid_view_count": sum(1 for item in views.values() if item["status"] == "invalid_input"),
            "gt_low_confidence_view_count": gt_low_confidence_count,
            "median_mask_iou": _median_metric(valid_entries, "mask_iou"),
            "median_bbox_iou": _median_metric(valid_entries, "bbox_iou"),
            "median_centroid_distance_px": _median_metric(valid_entries, "centroid_distance_px"),
            "median_edge_distance_px": _median_metric(valid_entries, "edge_distance_px"),
            "median_coverage_ratio": _median_metric(valid_entries, "coverage_ratio"),
        }
    return object_results


def _connected_component_count(mask: np.ndarray) -> int:
    mask = np.asarray(mask, dtype=bool)
    visited = np.zeros_like(mask, dtype=bool)
    count = 0
    height, width = mask.shape
    for y in range(height):
        for x in range(width):
            if not mask[y, x] or visited[y, x]:
                continue
            count += 1
            stack = [(y, x)]
            visited[y, x] = True
            while stack:
                cy, cx = stack.pop()
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        stack.append((ny, nx))
    return count


def _median_metric(records: list[dict[str, Any]], key: str) -> float | None:
    values = [float(item[key]) for item in records if item.get(key) is not None and math.isfinite(float(item[key]))]
    if not values:
        return None
    return float(np.median(np.asarray(values, dtype=np.float64)))


def _object_decision(metrics: dict[str, Any], thresholds: ValidationThresholds) -> tuple[Decision, list[str], int, float]:
    reasons: list[str] = []
    valid_view_count = int(metrics.get("valid_view_count", 0))
    severe_outliers = 0
    valid_views = [view for view in metrics.get("views", {}).values() if view.get("status") == "valid"]
    for view in valid_views:
        mask_iou = float(view.get("mask_iou", 0.0))
        centroid = float(view.get("centroid_distance_px")) if view.get("centroid_distance_px") is not None else float("inf")
        edge = float(view.get("edge_distance_px")) if view.get("edge_distance_px") is not None else float("inf")
        if (
            mask_iou < float(thresholds.severe_outlier_mask_iou)
            or centroid > float(thresholds.severe_outlier_centroid_px)
            or edge > float(thresholds.severe_outlier_edge_px)
        ):
            severe_outliers += 1
    severe_ratio = float(severe_outliers / max(valid_view_count, 1)) if valid_view_count else 1.0

    if valid_view_count < int(thresholds.min_views):
        reasons.append(f"valid_view_count<{thresholds.min_views}")
        return "FAIL", reasons, severe_outliers, severe_ratio

    median_mask_iou = metrics.get("median_mask_iou")
    median_bbox_iou = metrics.get("median_bbox_iou")
    median_centroid = metrics.get("median_centroid_distance_px")
    median_edge = metrics.get("median_edge_distance_px")

    if median_mask_iou is None or median_bbox_iou is None or median_centroid is None or median_edge is None:
        reasons.append("missing_median_metrics")
        return "FAIL", reasons, severe_outliers, severe_ratio

    pass_checks = [
        float(median_mask_iou) >= float(thresholds.mask_iou),
        float(median_bbox_iou) >= float(thresholds.bbox_iou),
        float(median_centroid) <= float(thresholds.centroid_px),
        float(median_edge) <= float(thresholds.edge_px),
        severe_ratio <= 0.35,
    ]
    if all(pass_checks):
        return "PASS", reasons, severe_outliers, severe_ratio

    fail_checks = [
        float(median_mask_iou) < max(float(thresholds.mask_iou) - 0.15, 0.0),
        float(median_bbox_iou) < max(float(thresholds.bbox_iou) - 0.15, 0.0),
        float(median_centroid) > float(thresholds.centroid_px) + 10.0,
        float(median_edge) > float(thresholds.edge_px) + 10.0,
        severe_ratio > 0.6,
    ]
    if any(fail_checks):
        if float(median_mask_iou) < max(float(thresholds.mask_iou) - 0.15, 0.0):
            reasons.append("median_mask_iou_below_fail_band")
        if float(median_bbox_iou) < max(float(thresholds.bbox_iou) - 0.15, 0.0):
            reasons.append("median_bbox_iou_below_fail_band")
        if float(median_centroid) > float(thresholds.centroid_px) + 10.0:
            reasons.append("median_centroid_distance_above_fail_band")
        if float(median_edge) > float(thresholds.edge_px) + 10.0:
            reasons.append("median_edge_distance_above_fail_band")
        if severe_ratio > 0.6:
            reasons.append("severe_outlier_ratio_above_limit")
        return "FAIL", reasons, severe_outliers, severe_ratio

    near_boundary = [
        float(median_mask_iou) >= float(thresholds.mask_iou) - float(thresholds.ambiguous_iou_margin),
        float(median_bbox_iou) >= float(thresholds.bbox_iou) - float(thresholds.ambiguous_bbox_iou_margin),
        float(median_centroid) <= float(thresholds.centroid_px) + float(thresholds.ambiguous_centroid_margin_px),
        float(median_edge) <= float(thresholds.edge_px) + float(thresholds.ambiguous_edge_margin_px),
    ]
    if any(near_boundary):
        reasons.append("borderline_threshold_region")
        return "AMBIGUOUS", reasons, severe_outliers, severe_ratio
    reasons.append("mixed_metrics")
    return "FAIL", reasons, severe_outliers, severe_ratio


def _save_overlay(
    image: np.ndarray,
    gt_mask: np.ndarray,
    prior_mask: np.ndarray,
    output_path: Path,
    title: str,
    metrics: dict[str, Any],
) -> None:
    canvas = Image.fromarray(image.astype(np.uint8), mode="RGB")
    draw = ImageDraw.Draw(canvas)
    _draw_mask_outline(draw, gt_mask, color=(0, 255, 0))
    _draw_mask_outline(draw, prior_mask, color=(255, 64, 64))
    draw.rectangle((0, 0, canvas.width - 1, 42), fill=(0, 0, 0))
    mask_iou = metrics.get("mask_iou")
    bbox_iou = metrics.get("bbox_iou")
    centroid = metrics.get("centroid_distance_px")
    edge = metrics.get("edge_distance_px")
    draw.text((8, 6), title, fill=(255, 255, 255))
    draw.text(
        (8, 22),
        f"IoU={mask_iou:.3f} bbox={bbox_iou:.3f} centroid={centroid if centroid is not None else 'NA'} edge={edge if edge is not None else 'NA'}",
        fill=(255, 255, 255),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)


def _draw_mask_outline(draw: ImageDraw.ImageDraw, mask: np.ndarray, *, color: tuple[int, int, int]) -> None:
    boundary = _boundary_points(mask, max_points=4096)
    for x, y in boundary:
        draw.point((float(x), float(y)), fill=color)


def _make_contact_sheet(
    overlay_paths: list[Path],
    output_path: Path,
    *,
    title: str,
    columns: int = 2,
) -> None:
    if not overlay_paths:
        return
    images = [Image.open(path).convert("RGB") for path in overlay_paths]
    tile_w = max(image.width for image in images)
    tile_h = max(image.height for image in images)
    rows = math.ceil(len(images) / columns)
    header_h = 40
    gap = 10
    canvas = Image.new(
        "RGB",
        (gap + columns * (tile_w + gap), header_h + gap + rows * (tile_h + gap)),
        color=(255, 255, 255),
    )
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 10), title, fill=(0, 0, 0))
    for index, image in enumerate(images):
        row = index // columns
        col = index % columns
        x = gap + col * (tile_w + gap)
        y = header_h + gap + row * (tile_h + gap)
        canvas.paste(image, (x, y))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)


def _save_reports(
    inputs: PositionValidationInputs,
    result: PositionValidationResult,
    *,
    output_dir: Path,
    gt_masks: dict[int, dict[str, np.ndarray]] | None = None,
    prior_masks: dict[int, dict[str, np.ndarray]] | None = None,
    view_rgbs: dict[str, np.ndarray] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    per_object_path = output_dir / "per_object_metrics.json"
    per_view_path = output_dir / "per_view_metrics.json"
    summary_path.write_text(json.dumps(result.summary, indent=2), encoding="utf-8")
    per_object_path.write_text(json.dumps(result.per_object_metrics, indent=2), encoding="utf-8")
    per_view_path.write_text(json.dumps(result.per_view_metrics, indent=2), encoding="utf-8")

    if gt_masks is None or prior_masks is None or view_rgbs is None:
        return
    overlay_paths: list[Path] = []
    for object_id_str, object_metrics in result.summary.get("objects", {}).items():
        object_id = int(object_id_str)
        view_metrics = result.per_view_metrics.get(str(object_id), {})
        sorted_views = sorted(
            view_metrics.items(),
            key=lambda item: (0 if item[1].get("status") == "valid" else 1, item[0]),
        )
        selected_views = [name for name, payload in sorted_views if payload.get("status") == "valid"][:4]
        if not selected_views:
            selected_views = [name for name, _ in sorted_views[:4]]
        for view_name in selected_views:
            overlay_path = output_dir / "overlays" / str(object_id) / f"{Path(view_name).stem}.png"
            _save_overlay(
                _load_overlay_rgb(inputs.scene_root, view_rgbs, view_name),
                gt_masks[object_id][view_name],
                prior_masks[object_id][view_name],
                overlay_path,
                title=f"obj {object_id} view {view_name}",
                metrics=view_metrics[view_name],
            )
            overlay_paths.append(overlay_path)
    _make_contact_sheet(overlay_paths, output_dir / "contact_sheet.png", title="Prior position validation overlays")


def validate_prior_positions(
    backend_run_dir: Path,
    *,
    mask_iou_threshold: float = 0.50,
    bbox_iou_threshold: float = 0.60,
    centroid_threshold_px: float = 15.0,
    edge_threshold_px: float = 12.0,
    min_views: int = 3,
    output_dir: Path | None = None,
) -> PositionValidationResult:
    thresholds = ValidationThresholds(
        mask_iou=mask_iou_threshold,
        bbox_iou=bbox_iou_threshold,
        centroid_px=centroid_threshold_px,
        edge_px=edge_threshold_px,
        min_views=min_views,
    )
    inputs = resolve_position_validation_inputs(backend_run_dir)
    summary: dict[str, Any] = {
        "scene_id": inputs.scene_id,
        "dataset_family": inputs.dataset_family,
        "backend_run_dir": str(inputs.backend_run_dir),
        "validator_version": "v1",
        "decision": "INPUT_MISMATCH",
        "decision_reasons": [],
        "renderer_capabilities": dict(inputs.renderer_capabilities),
        "view_policy": {"full_test_set_used": True},
        "thresholds": {
            "mask_iou": float(thresholds.mask_iou),
            "bbox_iou": float(thresholds.bbox_iou),
            "centroid_px": float(thresholds.centroid_px),
            "edge_px": float(thresholds.edge_px),
            "min_views": int(thresholds.min_views),
        },
        "input_consistency": dict(inputs.input_consistency),
        "gt_mask_quality": {
            "sample_count": int(thresholds.sample_count),
            "binary_closing": bool(thresholds.apply_binary_closing),
        },
        "render_cost_summary": {
            "test_view_count": len(inputs.test_views),
            "target_object_count": len(inputs.target_object_ids),
        },
        "geometry_validation_context": {
            "sfm_region_replacement_mode": inputs.sfm_region_replacement_mode,
        },
        "objects": {},
    }

    if inputs.input_consistency.get("status") != "OK":
        summary["decision"] = "INPUT_MISMATCH"
        summary["decision_reasons"] = list(inputs.input_consistency.get("reasons", []))
        result = PositionValidationResult(
            decision="INPUT_MISMATCH",
            summary=summary,
            per_object_metrics={},
            per_view_metrics={},
            output_dir=output_dir,
        )
        if output_dir is not None:
            _save_reports(inputs, result, output_dir=output_dir)
        return result

    if not inputs.selected_priors:
        summary["decision"] = "PASS"
        summary["decision_reasons"] = ["no_priors_to_validate"]
        result = PositionValidationResult(
            decision="PASS",
            summary=summary,
            per_object_metrics={},
            per_view_metrics={},
            output_dir=output_dir,
        )
        if output_dir is not None:
            _save_reports(inputs, result, output_dir=output_dir)
        return result

    try:
        gt_bundle = _render_gt_semantic_bundle(
            inputs,
            sample_count=int(thresholds.sample_count),
            apply_binary_closing=bool(thresholds.apply_binary_closing),
        )
        summary["gt_mask_quality"]["render_backend"] = gt_bundle.backend_name
        full_renders = render_full_prior_views(inputs)
        isolated_renders = render_isolated_prior_views(inputs)
        prior_masks = build_visible_prior_masks(
            full_renders,
            isolated_renders,
            depth_visibility_epsilon_m=float(thresholds.depth_visibility_epsilon_m),
        )
        object_metrics = compute_position_metrics(
            gt_bundle.masks,
            prior_masks,
            min_visible_pixel_ratio=float(thresholds.min_visible_pixel_ratio),
        )
    except RuntimeError as exc:
        summary["decision"] = "INPUT_MISMATCH"
        summary["decision_reasons"] = [str(exc)]
        result = PositionValidationResult(
            decision="INPUT_MISMATCH",
            summary=summary,
            per_object_metrics={},
            per_view_metrics={},
            output_dir=output_dir,
        )
        if output_dir is not None:
            _save_reports(inputs, result, output_dir=output_dir)
        return result

    run_decisions: list[Decision] = []
    per_object_summary: dict[str, Any] = {}
    per_view_summary: dict[str, Any] = {}
    for object_id, metrics in object_metrics.items():
        decision, reasons, severe_outliers, severe_ratio = _object_decision(metrics, thresholds)
        run_decisions.append(decision)
        per_object_summary[str(object_id)] = {
            "decision": decision,
            "decision_reasons": reasons,
            "median_mask_iou": metrics.get("median_mask_iou"),
            "median_bbox_iou": metrics.get("median_bbox_iou"),
            "median_centroid_distance_px": metrics.get("median_centroid_distance_px"),
            "median_edge_distance_px": metrics.get("median_edge_distance_px"),
            "median_coverage_ratio": metrics.get("median_coverage_ratio"),
            "valid_view_count": metrics.get("valid_view_count"),
            "ignored_view_count": metrics.get("ignored_view_count"),
            "invalid_view_count": metrics.get("invalid_view_count"),
            "gt_low_confidence_view_count": metrics.get("gt_low_confidence_view_count"),
            "severe_outlier_view_count": severe_outliers,
            "severe_outlier_ratio": severe_ratio,
        }
        per_view_summary[str(object_id)] = metrics["views"]

    if run_decisions and all(decision == "PASS" for decision in run_decisions):
        final_decision = "PASS"
    elif any(decision == "FAIL" for decision in run_decisions):
        final_decision = "FAIL"
    elif any(decision == "AMBIGUOUS" for decision in run_decisions):
        final_decision = "AMBIGUOUS"
    else:
        final_decision = "PASS"

    summary["decision"] = final_decision
    summary["decision_reasons"] = [
        f"{object_id}:{payload['decision']}" for object_id, payload in per_object_summary.items() if payload["decision"] != "PASS"
    ]
    summary["objects"] = per_object_summary
    result = PositionValidationResult(
        decision=final_decision,
        summary=summary,
        per_object_metrics=per_object_summary,
        per_view_metrics=per_view_summary,
        output_dir=output_dir,
    )
    if output_dir is not None:
        _save_reports(
            inputs,
            result,
            output_dir=output_dir,
            gt_masks=gt_bundle.masks,
            prior_masks=prior_masks,
            view_rgbs=gt_bundle.rgbs,
        )
    return result
