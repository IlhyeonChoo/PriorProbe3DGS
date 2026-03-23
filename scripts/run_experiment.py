#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import yaml

from priorprobe.datasets import load_dataset_spec, resolve_dataset_scene, validate_scene_layout
from priorprobe.evaluation.metrics import summarize_backend_run, summarize_run
from priorprobe.experiment_storage import experiment_storage_dir, storage_experiment_name
from priorprobe.insertion.alignment_search import (
    TargetBox,
    aabb_from_obb,
    build_scene_points_in_any_target_mask,
    choose_alignment_candidate,
    default_anchor_mode,
    load_ply_xyz,
    support_type_for_category,
)
from priorprobe.insertion.aligner import PriorAligner
from priorprobe.optimization.trainer import PriorProbeTrainer
from priorprobe.optimization.vanilla_3dgs import (
    Vanilla3DGSBackendConfig,
    build_train_command,
    command_to_string,
    run_command,
    resolve_backend_python,
    write_json,
)
from priorprobe.prior_library.library import PriorLibrary
from priorprobe.replica_export import quaternion_xyzw_to_rotation_matrix
from priorprobe.retrieval.retriever import PriorRetriever, RetrievalResult
from priorprobe.runtime_paths import resolve_runtime_path


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(path_str: str | None) -> Path | None:
    if path_str is None:
        return None
    path = Path(path_str)
    return path if path.is_absolute() else ROOT / path


def resolve_override(path_value: Path | None) -> Path | None:
    if path_value is None:
        return None
    return path_value if path_value.is_absolute() else ROOT / path_value


def default_outputs_root() -> Path:
    return resolve_runtime_path(ROOT, "outputs_dir", fallback="outputs")


def resolve_outputs_root(path_value: Path | None) -> Path:
    override = resolve_override(path_value)
    return override if override is not None else default_outputs_root()


def is_placeholder_path(path_value: str | None) -> bool:
    if path_value is None:
        return True
    normalized = str(path_value).strip()
    if not normalized:
        return True
    return normalized.startswith("/path/to/") or normalized.startswith("CHANGE_ME")


def load_dataset_scene(
    config: dict[str, Any],
    *,
    scene_id_override: str | None,
    root_override: Path | None,
) -> Any | None:
    dataset_config_path = resolve_path(config["experiment"].get("dataset_config"))
    if dataset_config_path is None or not dataset_config_path.exists():
        return None

    spec = load_dataset_spec(dataset_config_path, root=ROOT)
    return resolve_dataset_scene(spec, scene_id=scene_id_override, root_override=root_override)


def experiment_output_dir(
    experiment_name: str,
    scene_id: str | None = None,
    *,
    outputs_root: Path | None = None,
) -> Path:
    output_path = experiment_storage_dir((outputs_root or default_outputs_root()), "experiments", experiment_name)
    if scene_id is not None:
        output_path = output_path / scene_id
    return output_path


def archive_existing_path(path: Path) -> Path | None:
    if not path.exists():
        return None
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    candidate = path.with_name(f"{path.name}_backup_{timestamp}")
    suffix = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.name}_backup_{timestamp}_{suffix}")
        suffix += 1
    path.rename(candidate)
    return candidate


def write_evaluation(
    experiment_name: str,
    payload: dict[str, Any],
    *,
    scene_id: str | None = None,
    outputs_root: Path | None = None,
) -> Path:
    output_path = experiment_output_dir(experiment_name, scene_id=scene_id, outputs_root=outputs_root) / "evaluation.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def load_prior_init_metadata(model_path: Path) -> dict[str, Any] | None:
    metadata_path = model_path / "prior_init" / "metadata.json"
    if not metadata_path.exists():
        return None
    return load_json(metadata_path)


def load_scene_oracle_target(scene_root: Path) -> dict[str, Any] | None:
    target_path = scene_root / "oracle" / "target.json"
    if not target_path.exists():
        return None
    return load_json(target_path)


def load_scene_oracle_targets(scene_root: Path) -> list[dict[str, Any]]:
    targets_path = scene_root / "oracle" / "targets.json"
    if not targets_path.exists():
        return []
    payload = load_json(targets_path)
    if not isinstance(payload, list):
        raise ValueError(f"oracle/targets.json must contain a list: {targets_path}")
    return [dict(item) for item in payload]


def load_query_feature(
    scene_root: Path,
    target_payload: dict[str, Any] | None,
    *,
    feature_backend: str,
) -> np.ndarray | None:
    if target_payload is None:
        return None

    query_feature_paths = target_payload.get("query_feature_paths", {})
    feature_path_value = query_feature_paths.get(feature_backend)
    if feature_path_value is None:
        feature_path_value = target_payload.get("query_feature_path", "oracle/query_feature.npy")
    feature_path = Path(str(feature_path_value))
    if not feature_path.is_absolute():
        feature_path = scene_root / feature_path
    if not feature_path.exists():
        return None

    payload = np.load(feature_path)
    return payload.reshape(-1).astype(np.float32)


def normalize_oracle_targets(
    scene_root: Path,
    *,
    categories: list[str] | tuple[str, ...],
    max_objects: int,
) -> list[dict[str, Any]]:
    targets_payload = load_scene_oracle_targets(scene_root)
    if not targets_payload:
        single_target = load_scene_oracle_target(scene_root)
        if single_target is None:
            return []
        targets_payload = [single_target]

    allowed_categories = {str(category) for category in categories if str(category).strip()}
    if allowed_categories:
        targets_payload = [
            item for item in targets_payload if str(item.get("category")) in allowed_categories
        ]
    targets_payload.sort(key=lambda item: float(item.get("volume", 0.0)), reverse=True)
    if max_objects > 0:
        targets_payload = targets_payload[:max_objects]
    return targets_payload


def _resolve_extra_path(path_value: str | None) -> Path | None:
    return resolve_path(path_value)


def _alignment_settings(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    yaw_candidates = payload.get("yaw_search_degrees", [0.0, 90.0, 180.0, 270.0])
    return {
        "anchor_mode": str(payload.get("anchor_mode", "auto")),
        "yaw_search_degrees": [float(value) for value in yaw_candidates],
        "scene_bbox_margin": float(payload.get("scene_bbox_margin", 0.02)),
        "target_obb_margin": float(payload.get("target_obb_margin", 1.05)),
        "overlap_iou_threshold": float(payload.get("overlap_iou_threshold", 0.15)),
        "prior_overlap_iou_threshold": float(payload.get("prior_overlap_iou_threshold", 0.15)),
        "outside_scene_ratio_threshold": float(payload.get("outside_scene_ratio_threshold", 0.01)),
        "non_target_penetration_ratio_threshold": float(
            payload.get("non_target_penetration_ratio_threshold", 0.35)
        ),
        "skip_on_bad_alignment": bool(payload.get("skip_on_bad_alignment", False)),
        "max_scene_points": int(payload.get("max_scene_points", 60_000)),
        "max_prior_points": int(payload.get("max_prior_points", 16_000)),
    }


def _load_scene_sparse_points(scene_root: Path, *, max_points: int) -> np.ndarray:
    sparse_path = scene_root / "sparse" / "0" / "points3D.ply"
    if not sparse_path.exists():
        raise SystemExit(f"Missing sparse point cloud for alignment search: {sparse_path}")
    points = load_ply_xyz(sparse_path, max_points=max_points)
    if points.size == 0:
        raise SystemExit(f"Sparse point cloud is empty: {sparse_path}")
    return points


def _resolve_prior_entry_assets(
    library: PriorLibrary,
    selected_prior: RetrievalResult,
    *,
    anchor_mode: str,
) -> tuple[Path, dict[str, Any], str]:
    prior_entry = library.get(selected_prior.object_id)
    metadata_extras = dict(prior_entry.metadata.extras) if prior_entry.metadata is not None else {}
    support_type = support_type_for_category(
        selected_prior.category,
        explicit=metadata_extras.get("support_type"),
    )
    canonical_metadata_path = _resolve_extra_path(metadata_extras.get("canonical_metadata_path"))
    canonical_metadata: dict[str, Any] | None = None
    if canonical_metadata_path is not None and canonical_metadata_path.exists():
        canonical_metadata = load_json(canonical_metadata_path)
    if canonical_metadata is None:
        canonical_bbox_size = metadata_extras.get("canonical_bbox_size")
        if canonical_bbox_size is None:
            raise SystemExit(
                f"Prior {selected_prior.object_id} is missing canonical metadata. "
                "Rebuild the staged ShapeSplat bundle first."
            )
        canonical_metadata = {
            "bbox_size": list(canonical_bbox_size),
            "support_type": support_type,
            "default_anchor_mode": metadata_extras.get("canonical_anchor_mode", "center"),
        }

    requested_anchor_mode = anchor_mode
    if requested_anchor_mode == "auto":
        requested_anchor_mode = default_anchor_mode(selected_prior.category, support_type)
    if requested_anchor_mode not in {"center", "floor"}:
        raise SystemExit(f"Unsupported anchor mode: {requested_anchor_mode}")

    if requested_anchor_mode == "floor":
        seed_path = _resolve_extra_path(metadata_extras.get("canonical_seed_floor_path"))
    else:
        seed_path = _resolve_extra_path(metadata_extras.get("canonical_seed_center_path"))

    if seed_path is None or not seed_path.exists():
        raise SystemExit(
            f"Prior {selected_prior.object_id} is missing canonical seed path for anchor={requested_anchor_mode}: "
            f"{seed_path}"
        )
    return seed_path, canonical_metadata, requested_anchor_mode


def _build_alignment_payload(
    *,
    target_payload: dict[str, Any],
    selected_prior: RetrievalResult,
    canonical_seed_path: Path,
    source_prior_path: Path,
    anchor_mode: str,
    support_type: str,
    chosen_candidate: Any,
    candidate_path: Path,
    candidate_count: int,
    fallback_used: bool,
    feature_backend: str,
) -> dict[str, Any]:
    target_box = TargetBox.from_payload(target_payload)
    center_error = chosen_candidate.candidate_center_world - target_box.center
    target_bottom = target_box.anchor_point("floor")
    if chosen_candidate.anchor_mode == "floor":
        candidate_bottom = chosen_candidate.target_anchor_world
    else:
        candidate_bottom = chosen_candidate.candidate_center_world - chosen_candidate.rotation_matrix @ np.asarray(
            [0.0, 0.0, float(chosen_candidate.candidate_sizes_world[2]) * 0.5],
            dtype=np.float32,
        )
    bottom_error = candidate_bottom - target_bottom

    return {
        "scale": chosen_candidate.scale_vec.tolist(),
        "rotation_matrix": chosen_candidate.rotation_matrix.tolist(),
        "translation": chosen_candidate.translation.tolist(),
        "metadata": {
            "target_category": target_payload.get("category"),
            "target_object_id": target_payload.get("object_id"),
            "target_center": target_box.center.tolist(),
            "target_sizes": target_box.sizes.tolist(),
            "target_rotation_matrix": target_box.rotation_matrix.tolist(),
            "target_bottom_anchor": target_bottom.tolist(),
            "source_prior_path": str(source_prior_path),
            "canonical_seed_path": str(canonical_seed_path),
            "prior_object_id": selected_prior.object_id,
            "prior_category": selected_prior.category,
            "support_type": support_type,
            "anchor_mode": anchor_mode,
            "scale_mode": "anisotropic",
            "yaw_deg": float(chosen_candidate.yaw_deg),
            "scale_vec": chosen_candidate.scale_vec.tolist(),
            "candidate_center_world": chosen_candidate.candidate_center_world.tolist(),
            "candidate_sizes_world": chosen_candidate.candidate_sizes_world.tolist(),
            "candidate_aabb_min": chosen_candidate.candidate_aabb_min.tolist(),
            "candidate_aabb_max": chosen_candidate.candidate_aabb_max.tolist(),
            "outside_scene_ratio": float(chosen_candidate.outside_scene_ratio),
            "non_target_penetration_ratio": float(chosen_candidate.non_target_penetration_ratio),
            "other_target_max_iou": float(chosen_candidate.other_target_max_iou),
            "prior_target_max_iou": float(chosen_candidate.prior_target_max_iou),
            "accepted": bool(chosen_candidate.accepted),
            "rejected_reasons": list(chosen_candidate.rejected_reasons),
            "dropped": bool(chosen_candidate.dropped),
            "drop_reason": chosen_candidate.drop_reason,
            "candidate_count": int(candidate_count),
            "fallback_used": bool(fallback_used),
            "feature_backend": feature_backend,
            "center_error": center_error.tolist(),
            "bottom_error": bottom_error.tolist(),
            "alignment_candidates_json": str(candidate_path),
        },
    }


def _exact_match_key_from_target(target_payload: dict[str, Any]) -> str:
    return f"{target_payload.get('scene_id')}:{target_payload.get('object_id')}"


def _build_oracle_target_box_alignment_payload(
    *,
    target_payload: dict[str, Any],
    selected_prior: RetrievalResult,
    canonical_seed_path: Path,
    source_prior_path: Path,
    prior_bbox_size: np.ndarray,
    anchor_mode: str,
    support_type: str,
    feature_backend: str,
) -> dict[str, Any]:
    target_box = TargetBox.from_payload(target_payload)
    scale_vec = target_box.sizes / np.maximum(np.asarray(prior_bbox_size, dtype=np.float32), 1e-6)
    if not np.all(np.isfinite(scale_vec)) or np.any(scale_vec <= 0.0):
        raise SystemExit(f"Invalid oracle_target_box scale vector for prior {selected_prior.object_id}: {scale_vec}")

    rotation_matrix = target_box.rotation_matrix.astype(np.float32)
    translation = target_box.anchor_point(anchor_mode).astype(np.float32)
    target_bottom = target_box.anchor_point("floor").astype(np.float32)
    candidate_aabb_min, candidate_aabb_max = aabb_from_obb(
        center=target_box.center,
        sizes=target_box.sizes,
        rotation_matrix=target_box.rotation_matrix,
    )

    return {
        "scale": scale_vec.tolist(),
        "rotation_matrix": rotation_matrix.tolist(),
        "translation": translation.tolist(),
        "metadata": {
            "target_category": target_payload.get("category"),
            "target_object_id": target_payload.get("object_id"),
            "target_center": target_box.center.tolist(),
            "target_sizes": target_box.sizes.tolist(),
            "target_rotation_matrix": target_box.rotation_matrix.tolist(),
            "target_bottom_anchor": target_bottom.tolist(),
            "source_prior_path": str(source_prior_path),
            "canonical_seed_path": str(canonical_seed_path),
            "prior_object_id": selected_prior.object_id,
            "prior_category": selected_prior.category,
            "support_type": support_type,
            "anchor_mode": anchor_mode,
            "scale_mode": "anisotropic",
            "yaw_deg": 0.0,
            "scale_vec": scale_vec.tolist(),
            "candidate_center_world": target_box.center.tolist(),
            "candidate_sizes_world": target_box.sizes.tolist(),
            "candidate_aabb_min": candidate_aabb_min.tolist(),
            "candidate_aabb_max": candidate_aabb_max.tolist(),
            "outside_scene_ratio": 0.0,
            "non_target_penetration_ratio": 0.0,
            "other_target_max_iou": 0.0,
            "prior_target_max_iou": 0.0,
            "accepted": True,
            "rejected_reasons": [],
            "dropped": False,
            "drop_reason": None,
            "candidate_count": 1,
            "fallback_used": False,
            "feature_backend": feature_backend,
            "center_error": [0.0, 0.0, 0.0],
            "bottom_error": [0.0, 0.0, 0.0],
            "alignment_candidates_json": None,
            "alignment_mode": "oracle_target_box",
        },
    }


def _select_exact_target_prior(
    library: PriorLibrary,
    *,
    target_payload: dict[str, Any],
) -> RetrievalResult:
    expected_key = _exact_match_key_from_target(target_payload)
    expected_scene = str(target_payload.get("scene_id"))
    expected_object = str(target_payload.get("object_id"))

    for entry in library.list_entries():
        extras = dict(entry.metadata.extras) if entry.metadata is not None else {}
        candidate_key = extras.get("exact_match_key")
        candidate_scene = str(extras.get("replica_scene_id")) if extras.get("replica_scene_id") is not None else None
        candidate_object = str(extras.get("replica_object_id")) if extras.get("replica_object_id") is not None else None
        if candidate_key == expected_key or (
            candidate_scene == expected_scene and candidate_object == expected_object
        ):
            return RetrievalResult(
                object_id=entry.object_id,
                score=1.0,
                mode="oracle_target_object",
                gaussian_path=entry.gaussian_path,
                category=entry.category,
                candidate_count=1,
                fallback_used=False,
                feature_path=entry.feature_path,
            )

    raise SystemExit(
        "oracle_target_object retrieval could not find an exact prior for "
        f"scene_id={expected_scene}, object_id={expected_object}"
    )


def build_insertion_controls(selected_priors: list[RetrievalResult], *, init_mode: str) -> list[dict[str, Any]]:
    if not selected_priors:
        return []

    scores = np.asarray([float(item.score) for item in selected_priors], dtype=np.float32)
    if scores.size == 1 or float(scores.max() - scores.min()) <= 1e-6:
        normalized = np.ones_like(scores, dtype=np.float32)
    else:
        normalized = (scores - scores.min()) / max(float(scores.max() - scores.min()), 1e-6)

    controls: list[dict[str, Any]] = []
    for score_value, normalized_value in zip(scores.tolist(), normalized.tolist()):
        keep_ratio = 1.0
        dropped = False
        if init_mode == "weighted_merge":
            keep_ratio = float(np.clip(0.25 + 0.75 * normalized_value, 0.25, 1.0))
        elif init_mode == "filtered_merge":
            dropped = bool(normalized_value < 0.5)
            keep_ratio = 0.0 if dropped else 1.0

        controls.append(
            {
                "prior_score": float(score_value),
                "normalized_confidence": float(normalized_value),
                "point_keep_ratio": float(keep_ratio),
                "dropped": dropped,
            }
        )

    if init_mode == "filtered_merge" and all(item["dropped"] for item in controls):
        best_index = int(np.argmax(scores))
        controls[best_index]["dropped"] = False
        controls[best_index]["point_keep_ratio"] = 1.0
    return controls


def build_render_command(config: Vanilla3DGSBackendConfig, *, iteration: int) -> list[str]:
    command = [
        str(resolve_backend_python(config)),
        str(config.repo_path / "render.py"),
        "--source_path",
        str(config.source_path),
        "--model_path",
        str(config.model_path),
        "--images",
        config.images,
        "--iteration",
        str(iteration),
        "--skip_train",
    ]
    if config.depths:
        command.extend(["--depths", config.depths])
    if config.white_background:
        command.append("--white_background")
    if config.eval:
        command.append("--eval")
    if config.quiet:
        command.append("--quiet")
    return command


def build_metrics_command(config: Vanilla3DGSBackendConfig) -> list[str]:
    return [
        str(resolve_backend_python(config)),
        str(config.repo_path / "metrics.py"),
        "--model_paths",
        str(config.model_path),
    ]


def run_placeholder_experiment(config: dict[str, Any], *, outputs_root: Path) -> int:
    experiment = config["experiment"]
    trainer_config = config["trainer"]
    target_quality = trainer_config.get("target_quality", {})

    trainer = PriorProbeTrainer(output_root=outputs_root)
    retrieval_score = None
    alignment_score = None

    if experiment["initialization"] == "from_scratch":
        run = trainer.run_from_scratch(
            experiment_name=experiment["name"],
            steps=trainer_config["max_steps"],
            target_metric=target_quality.get("metric"),
            target_value=target_quality.get("value"),
        )
    else:
        prior_config = load_yaml(resolve_path(experiment["prior_config"]))
        manifest_path = resolve_path(prior_config["library"]["manifest_path"])
        if manifest_path is None or not manifest_path.exists():
            raise SystemExit("Prior manifest is missing. Run scripts/prepare_prior_library.py first.")

        library = PriorLibrary.load_manifest(manifest_path)
        oracle_object_id = experiment.get("prior_object_id") if experiment["retrieval_mode"] == "oracle" else None
        if oracle_object_id:
            entry = library.get(str(oracle_object_id))
            selected = RetrievalResult(
                object_id=entry.object_id,
                score=1.0,
                mode="oracle_object_id",
                gaussian_path=entry.gaussian_path,
                category=entry.category,
                candidate_count=1,
                fallback_used=False,
                feature_path=entry.feature_path,
            )
        else:
            retriever = PriorRetriever(library)
            retrieval_results = retriever.retrieve(top_k=1)
            if not retrieval_results:
                raise SystemExit("No prior candidates were found.")
            selected = retrieval_results[0]
        aligner = PriorAligner()
        alignment = aligner.align(
            selected.object_id,
            oracle=experiment["alignment_mode"] == "oracle",
        )
        retrieval_score = selected.score
        alignment_score = alignment.score
        run = trainer.run_with_prior(
            experiment_name=experiment["name"],
            prior_object_id=selected.object_id,
            steps=trainer_config["max_steps"],
            alignment_mode=alignment.mode,
            adaptation=experiment["adaptation"],
            target_metric=target_quality.get("metric"),
            target_value=target_quality.get("value"),
        )

    run_path = trainer.save_run(run)
    evaluation = summarize_run(
        run,
        retrieval_score=retrieval_score,
        alignment_score=alignment_score,
    )
    evaluation_path = write_evaluation(
        experiment["name"],
        evaluation.to_dict(),
        outputs_root=outputs_root,
    )
    print(f"Saved run summary to {run_path}")
    print(f"Saved evaluation to {evaluation_path}")
    return 0


def select_priors(
    config: dict[str, Any],
    *,
    dataset_scene: Any | None = None,
    target_payloads: list[dict[str, Any]] | None = None,
) -> tuple[list[RetrievalResult], PriorLibrary]:
    experiment = config["experiment"]
    prior_config_path = resolve_path(experiment["prior_config"])
    if prior_config_path is None:
        raise SystemExit("experiment.prior_config is required for prior-initialized runs.")

    prior_config = load_yaml(prior_config_path)
    manifest_path = resolve_path(prior_config["library"]["manifest_path"])
    if manifest_path is None or not manifest_path.exists():
        raise SystemExit("Prior manifest is missing. Run scripts/prepare_prior_library.py first.")

    library = PriorLibrary.load_manifest(manifest_path)
    retriever = PriorRetriever(library)
    retrieval_mode = str(experiment.get("retrieval_mode", "automatic"))
    feature_backend = str(experiment.get("feature_backend", "mean_rgb"))
    if retrieval_mode in {"oracle", "oracle_category", "oracle_target_object"}:
        if dataset_scene is None or not target_payloads:
            raise SystemExit("oracle retrieval requires a dataset scene with oracle target metadata.")
    results: list[RetrievalResult] = []
    for target_payload in target_payloads or []:
        if retrieval_mode == "oracle_target_object":
            results.append(_select_exact_target_prior(library, target_payload=target_payload))
            continue
        oracle_category = None
        query_feature = None
        if retrieval_mode in {"oracle", "oracle_category"}:
            oracle_category = str(target_payload["category"])
            query_feature = load_query_feature(
                dataset_scene.source_path,
                target_payload,
                feature_backend=feature_backend,
            )
            if query_feature is None:
                raise SystemExit(
                    f"Missing query feature for backend={feature_backend} and target object_id={target_payload.get('object_id')}"
                )
        retrieval_results = retriever.retrieve(
            query_features=query_feature,
            top_k=1,
            oracle_category=oracle_category,
            fallback_to_all=True,
        )
        if not retrieval_results:
            raise SystemExit("No prior candidates were found.")
        results.append(retrieval_results[0])
    return results, library


def run_vanilla_3dgs_experiment(config: dict[str, Any], args: argparse.Namespace) -> int:
    experiment = config["experiment"]
    trainer_config = config.get("trainer", {})
    alignment_mode = str(experiment.get("alignment_mode", "automatic"))
    insertion_representation = str(experiment.get("insertion_representation", "pointcloud_proxy"))
    if insertion_representation not in {"pointcloud_proxy", "gaussian_direct"}:
        raise SystemExit(f"Unsupported insertion_representation: {insertion_representation}")
    outputs_root = resolve_outputs_root(args.outputs_dir)
    dataset_scene = load_dataset_scene(
        config,
        scene_id_override=args.dataset_scene_id,
        root_override=resolve_override(args.dataset_root),
    )
    backend_payload = dict(config.get("backend", {}))
    if dataset_scene is not None:
        if is_placeholder_path(backend_payload.get("source_path")) and args.backend_source_path is None:
            backend_payload["source_path"] = str(dataset_scene.source_path)
        backend_payload["images"] = dataset_scene.images
        backend_payload["depths"] = dataset_scene.depths
        backend_payload["eval"] = dataset_scene.eval
        backend_payload["white_background"] = dataset_scene.white_background
        if is_placeholder_path(backend_payload.get("model_path")) and args.backend_model_path is None:
            backend_payload["model_path"] = str(
                experiment_storage_dir(outputs_root, "backend_runs", str(experiment["name"])) / dataset_scene.scene_id
            )

    backend_config = Vanilla3DGSBackendConfig.from_payload(
        backend_payload,
        root=ROOT,
        trainer_payload=trainer_config,
        artifacts_payload=config.get("artifacts", {}),
        source_override=resolve_override(args.backend_source_path),
        model_override=resolve_override(args.backend_model_path),
        dry_run_override=True if args.dry_run else None,
    )
    if (
        experiment["initialization"] != "from_scratch"
        and insertion_representation == "gaussian_direct"
        and backend_config.init_mode not in {"merge", "replace"}
    ):
        raise SystemExit(
            "gaussian_direct prior insertion currently supports backend.init_mode in {'merge', 'replace'} only."
        )

    output_dir = experiment_output_dir(
        experiment["name"],
        scene_id=dataset_scene.scene_id if dataset_scene is not None else None,
        outputs_root=outputs_root,
    )
    archived_output_dir: Path | None = None
    archived_model_path: Path | None = None
    if not backend_config.dry_run:
        archived_output_dir = archive_existing_path(output_dir)
        archived_model_path = archive_existing_path(backend_config.model_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    prior_alignment = config.get("prior_alignment", {})
    alignment_settings = _alignment_settings(prior_alignment)
    alignment_path = resolve_override(args.alignment_transform_path) or resolve_path(prior_alignment.get("transform_path"))
    oracle_config = config.get("oracle", {})
    oracle_categories = [str(value) for value in oracle_config.get("categories", [])]
    oracle_max_objects = int(oracle_config.get("max_objects", 1))
    selected_prior: RetrievalResult | None = None
    selected_priors: list[RetrievalResult] = []
    library: PriorLibrary | None = None
    target_payload: dict[str, Any] | None = None
    target_payloads: list[dict[str, Any]] = []
    generated_alignment_payload: dict[str, Any] | None = None
    generated_alignment_payloads: list[dict[str, Any]] = []
    generated_alignment_candidates: list[dict[str, Any]] = []
    prior_ply: Path | None = None
    prior_spec_json: Path | None = None
    insertion_controls: list[dict[str, Any]] = []
    selected_prior_metadata_payloads: list[dict[str, Any]] = []

    if experiment["initialization"] != "from_scratch":
        if dataset_scene is None:
            raise SystemExit("prior-initialized vanilla_3dgs runs require a dataset scene.")
        target_payloads = normalize_oracle_targets(
            dataset_scene.source_path,
            categories=oracle_categories,
            max_objects=oracle_max_objects,
        )
        if not target_payloads:
            raise SystemExit(
                f"Missing oracle target metadata at {dataset_scene.source_path / 'oracle/target.json'} "
                f"or {dataset_scene.source_path / 'oracle/targets.json'}. "
                "Run the Replica oracle export first."
            )
        target_payload = target_payloads[0]

        selected_priors, library = select_priors(
            config,
            dataset_scene=dataset_scene,
            target_payloads=target_payloads,
        )
        selected_prior = selected_priors[0]
        insertion_controls = build_insertion_controls(selected_priors, init_mode=backend_config.init_mode)
        if len(selected_priors) != len(target_payloads):
            raise SystemExit(
                f"retrieved prior count ({len(selected_priors)}) does not match oracle target count ({len(target_payloads)})"
            )

        prior_specs_payload: list[dict[str, Any]] = []
        if alignment_path is not None and len(selected_priors) > 1:
            raise SystemExit("explicit alignment_transform_path only supports single-prior experiments")

        target_boxes = [TargetBox.from_payload(item) for item in target_payloads]
        scene_points: np.ndarray | None = None
        scene_points_in_any_target: np.ndarray | None = None
        if alignment_path is None and alignment_mode != "oracle_target_box":
            scene_points = _load_scene_sparse_points(
                dataset_scene.source_path,
                max_points=alignment_settings["max_scene_points"],
            )
            scene_points_in_any_target = build_scene_points_in_any_target_mask(
                scene_points,
                target_boxes,
                margin_factor=alignment_settings["target_obb_margin"],
            )
        previous_candidate_aabbs: list[tuple[np.ndarray, np.ndarray]] = []
        feature_backend = str(experiment.get("feature_backend", "mean_rgb"))

        for index, (selected_item, target_item, target_box) in enumerate(
            zip(selected_priors, target_payloads, target_boxes)
        ):
            source_prior_path = resolve_path(str(selected_item.gaussian_path))
            if source_prior_path is None or not source_prior_path.exists():
                raise SystemExit(f"Selected prior asset is missing: {selected_item.gaussian_path}")

            canonical_seed_path, canonical_metadata, resolved_anchor_mode = _resolve_prior_entry_assets(
                library,
                selected_item,
                anchor_mode=alignment_settings["anchor_mode"],
            )
            prior_entry = library.get(selected_item.object_id)
            prior_metadata_extras = (
                dict(prior_entry.metadata.extras) if prior_entry.metadata is not None else {}
            )
            support_type = support_type_for_category(
                selected_item.category,
                explicit=canonical_metadata.get("support_type"),
            )

            if alignment_path is not None:
                chosen_alignment_path = alignment_path
                alignment_payload = load_json(alignment_path)
                generated_alignment_payloads.append(alignment_payload)
                generated_alignment_candidates.append(
                    {
                        "target_object_id": target_item.get("object_id"),
                        "target_category": target_item.get("category"),
                        "prior_object_id": selected_item.object_id,
                        "path": str(alignment_path),
                        "mode": "explicit",
                    }
                )
                effective_dropped = bool(insertion_controls[index]["dropped"])
                effective_drop_reason = "filtered_confidence" if effective_dropped else None
                alignment_debug = {
                    "mode": "explicit",
                    "anchor_mode": resolved_anchor_mode,
                    "source_prior_path": str(source_prior_path),
                    "canonical_seed_path": str(canonical_seed_path),
                    "alignment_json": str(alignment_path),
                    "support_type": support_type,
                }
            elif alignment_mode == "oracle_target_box":
                alignment_payload = _build_oracle_target_box_alignment_payload(
                    target_payload=target_item,
                    selected_prior=selected_item,
                    canonical_seed_path=canonical_seed_path,
                    source_prior_path=source_prior_path,
                    prior_bbox_size=np.asarray(canonical_metadata["bbox_size"], dtype=np.float32),
                    anchor_mode=resolved_anchor_mode,
                    support_type=support_type,
                    feature_backend=feature_backend,
                )
                chosen_alignment_path = output_dir / (
                    f"generated_alignment_{target_item['object_id']}_{index:02d}.json"
                )
                chosen_alignment_path.write_text(json.dumps(alignment_payload, indent=2), encoding="utf-8")
                generated_alignment_payloads.append(alignment_payload)
                generated_alignment_candidates.append(
                    {
                        "target_object_id": target_item.get("object_id"),
                        "target_category": target_item.get("category"),
                        "prior_object_id": selected_item.object_id,
                        "path": str(chosen_alignment_path),
                        "mode": "oracle_target_box",
                    }
                )
                alignment_debug = dict(alignment_payload.get("metadata", {}))
                alignment_debug["alignment_json"] = str(chosen_alignment_path)
                effective_dropped = bool(insertion_controls[index]["dropped"])
                effective_drop_reason = "filtered_confidence" if effective_dropped else None
            else:
                if scene_points is None or scene_points_in_any_target is None:
                    raise SystemExit("alignment search requires scene sparse points.")
                candidates_output = output_dir / (
                    f"alignment_candidates_{target_item['object_id']}_{index:02d}.json"
                )
                search_result = choose_alignment_candidate(
                    prior_seed_path=canonical_seed_path,
                    prior_bbox_size=np.asarray(canonical_metadata["bbox_size"], dtype=np.float32),
                    target=target_box,
                    all_targets=target_boxes,
                    scene_points=scene_points,
                    scene_points_in_any_target=scene_points_in_any_target,
                    previous_candidate_aabbs=previous_candidate_aabbs,
                    anchor_mode=resolved_anchor_mode,
                    yaw_candidates=alignment_settings["yaw_search_degrees"],
                    max_prior_points=alignment_settings["max_prior_points"],
                    scene_bbox_margin=alignment_settings["scene_bbox_margin"],
                    target_obb_margin=alignment_settings["target_obb_margin"],
                    overlap_iou_threshold=alignment_settings["overlap_iou_threshold"],
                    prior_overlap_iou_threshold=alignment_settings["prior_overlap_iou_threshold"],
                    outside_scene_ratio_threshold=alignment_settings["outside_scene_ratio_threshold"],
                    non_target_penetration_ratio_threshold=alignment_settings[
                        "non_target_penetration_ratio_threshold"
                    ],
                    skip_on_bad_alignment=alignment_settings["skip_on_bad_alignment"],
                )
                candidate_payload = {
                    "target_object_id": target_item.get("object_id"),
                    "target_category": target_item.get("category"),
                    "prior_object_id": selected_item.object_id,
                    "prior_category": selected_item.category,
                    "canonical_seed_path": str(canonical_seed_path),
                    "support_type": support_type,
                    "chosen_yaw_deg": float(search_result.chosen.yaw_deg),
                    "chosen_index": next(
                        candidate_index
                        for candidate_index, candidate in enumerate(search_result.candidates)
                        if candidate.yaw_deg == search_result.chosen.yaw_deg
                    ),
                    "candidates": [candidate.to_payload() for candidate in search_result.candidates],
                }
                candidates_output.write_text(json.dumps(candidate_payload, indent=2), encoding="utf-8")
                generated_alignment_candidates.append(
                    {
                        "target_object_id": target_item.get("object_id"),
                        "target_category": target_item.get("category"),
                        "prior_object_id": selected_item.object_id,
                        "path": str(candidates_output),
                    }
                )

                alignment_payload = _build_alignment_payload(
                    target_payload=target_item,
                    selected_prior=selected_item,
                    canonical_seed_path=canonical_seed_path,
                    source_prior_path=source_prior_path,
                    anchor_mode=resolved_anchor_mode,
                    support_type=support_type,
                    chosen_candidate=search_result.chosen,
                    candidate_path=candidates_output,
                    candidate_count=selected_item.candidate_count,
                    fallback_used=selected_item.fallback_used,
                    feature_backend=feature_backend,
                )
                chosen_alignment_path = output_dir / (
                    f"generated_alignment_{target_item['object_id']}_{index:02d}.json"
                )
                chosen_alignment_path.write_text(json.dumps(alignment_payload, indent=2), encoding="utf-8")
                generated_alignment_payloads.append(alignment_payload)

                alignment_debug = dict(alignment_payload.get("metadata", {}))
                alignment_debug["alignment_json"] = str(chosen_alignment_path)
                alignment_debug["alignment_candidates_json"] = str(candidates_output)

                effective_dropped = bool(insertion_controls[index]["dropped"] or search_result.chosen.dropped)
                if insertion_controls[index]["dropped"]:
                    effective_drop_reason = "filtered_confidence"
                else:
                    effective_drop_reason = search_result.chosen.drop_reason

                if not effective_dropped:
                    previous_candidate_aabbs.append(
                        (
                            search_result.chosen.candidate_aabb_min.copy(),
                            search_result.chosen.candidate_aabb_max.copy(),
                        )
                    )

            requested_keep_ratio = float(insertion_controls[index]["point_keep_ratio"])
            if effective_dropped:
                requested_keep_ratio = 0.0

            insertion_source_path = source_prior_path if insertion_representation == "gaussian_direct" else canonical_seed_path

            prior_spec = {
                "prior_ply": str(insertion_source_path),
                "alignment_json": str(chosen_alignment_path),
                "prior_object_id": selected_item.object_id,
                "prior_score": insertion_controls[index]["prior_score"],
                "normalized_confidence": insertion_controls[index]["normalized_confidence"],
                "point_keep_ratio": requested_keep_ratio,
                "dropped": effective_dropped,
                "drop_reason": effective_drop_reason,
                "target_object_id": target_item.get("object_id"),
                "target_category": target_item.get("category"),
                "alignment_debug": alignment_debug,
                "source_prior_path": str(source_prior_path),
                "canonical_seed_path": str(canonical_seed_path),
                "insertion_source_path": str(insertion_source_path),
                "insertion_representation": insertion_representation,
                "metadata_extras": prior_metadata_extras,
            }
            prior_specs_payload.append(prior_spec)
            selected_prior_metadata_payloads.append(
                {
                    "object_id": selected_item.object_id,
                    "score": selected_item.score,
                    "mode": selected_item.mode,
                    "asset_format": "gaussian" if insertion_representation == "gaussian_direct" else "point_cloud",
                    "gaussian_path": str(source_prior_path),
                    "category": selected_item.category,
                    "feature_path": str(selected_item.feature_path) if selected_item.feature_path else None,
                    "candidate_count": selected_item.candidate_count,
                    "fallback_used": selected_item.fallback_used,
                    "target_object_id": target_item.get("object_id"),
                    "target_category": target_item.get("category"),
                    "normalized_confidence": insertion_controls[index]["normalized_confidence"],
                    "point_keep_ratio": requested_keep_ratio,
                    "dropped": effective_dropped,
                    "drop_reason": effective_drop_reason,
                    "source_prior_path": str(source_prior_path),
                    "canonical_seed_path": str(canonical_seed_path),
                    "insertion_source_path": str(insertion_source_path),
                    "insertion_representation": insertion_representation,
                    "metadata_extras": prior_metadata_extras,
                    "alignment_json": str(chosen_alignment_path),
                    "alignment_debug": alignment_debug,
                }
            )

        prior_spec_json = output_dir / "prior_specs.json"
        prior_spec_json.write_text(json.dumps(prior_specs_payload, indent=2), encoding="utf-8")
        if len(generated_alignment_payloads) == 1:
            generated_alignment_payload = generated_alignment_payloads[0]
            alignment_path = Path(str(prior_specs_payload[0]["alignment_json"]))

    if not backend_config.dry_run:
        if dataset_scene is not None:
            valid, messages = validate_scene_layout(dataset_scene)
            if not valid:
                formatted = "\n".join(f"- {message}" for message in messages)
                raise SystemExit(f"Dataset scene is not ready for vanilla_3dgs training:\n{formatted}")
        elif not backend_config.source_path.exists():
            raise SystemExit(f"Backend source_path does not exist: {backend_config.source_path}")

    command = build_train_command(
        backend_config,
        prior_ply=prior_ply,
        alignment_json=alignment_path,
        prior_object_id=selected_prior.object_id if selected_prior else None,
        prior_score=selected_prior.score if selected_prior else None,
        prior_spec_json=prior_spec_json,
    )

    metadata_path = output_dir / "backend_run.json"
    metadata = {
        "experiment_name": experiment["name"],
        "storage_experiment_name": storage_experiment_name(str(experiment["name"]), outputs_root=outputs_root),
        "backend": "vanilla_3dgs",
        "initialization": experiment["initialization"],
        "alignment_mode": alignment_mode,
        "insertion_representation": insertion_representation,
        "prior_protection": {
            "mode": backend_config.prior_protection_mode,
            "lr_scale": backend_config.prior_lr_scale,
            "protect_from_prune": backend_config.protect_prior_from_prune,
            "protect_from_densify": backend_config.protect_prior_from_densify,
        },
        "prior_insertion": {
            "sh_reset_mode": backend_config.prior_sh_reset_mode,
            "target_total_gaussians": backend_config.prior_target_total_gaussians,
            "subsample_seed": backend_config.prior_subsample_seed,
            "sfm_region_replacement_mode": backend_config.sfm_region_replacement_mode,
            "sfm_region_margin_scale": backend_config.sfm_region_margin_scale,
            "sfm_region_margin_min_m": backend_config.sfm_region_margin_min_m,
        },
        "status": "dry_run" if backend_config.dry_run else "pending",
        "repo_path": str(backend_config.repo_path),
        "source_path": str(backend_config.source_path),
        "model_path": str(backend_config.model_path),
        "dataset_scene": None,
        "command": command,
        "command_string": command_to_string(command),
        "alignment_json": str(alignment_path) if alignment_path else None,
        "prior_spec_json": str(prior_spec_json) if prior_spec_json else None,
        "generated_alignment": generated_alignment_payload,
        "generated_alignments": generated_alignment_payloads,
        "generated_alignment_candidates": generated_alignment_candidates,
        "initial_snapshot": None,
        "selected_prior": None,
        "selected_priors": [],
        "oracle_target": target_payload,
        "oracle_targets": target_payloads,
        "render_runs": [],
        "metrics_run": None,
        "archived_output_dir": str(archived_output_dir) if archived_output_dir is not None else None,
        "archived_model_path": str(archived_model_path) if archived_model_path is not None else None,
    }
    if dataset_scene is not None:
        metadata["dataset_scene"] = {
            "dataset_name": dataset_scene.dataset_name,
            "scene_id": dataset_scene.scene_id,
            "format": dataset_scene.format,
            "source_path": str(dataset_scene.source_path),
            "images": dataset_scene.images,
            "depths": dataset_scene.depths,
            "eval": dataset_scene.eval,
            "white_background": dataset_scene.white_background,
            "notes": list(dataset_scene.notes),
        }
    if backend_config.save_initial_snapshot:
        metadata["initial_snapshot"] = {
            "point_cloud": str(backend_config.model_path / "point_cloud" / "iteration_0" / "point_cloud.ply"),
            "render_sets": {
                render_set: {
                    "renders": str(backend_config.model_path / render_set / "ours_0" / "renders"),
                    "gt": str(backend_config.model_path / render_set / "ours_0" / "gt"),
                }
                for render_set in (backend_config.initial_render_sets or ("train", "test"))
            },
        }
    if selected_prior is not None:
        selected_prior_metadata = (
            selected_prior_metadata_payloads[0]
            if selected_prior_metadata_payloads
            else {
                "object_id": selected_prior.object_id,
                "score": selected_prior.score,
                "mode": selected_prior.mode,
                "gaussian_path": str(resolve_path(str(selected_prior.gaussian_path))),
                "category": selected_prior.category,
                "feature_path": str(selected_prior.feature_path) if selected_prior.feature_path else None,
                "candidate_count": selected_prior.candidate_count,
                "fallback_used": selected_prior.fallback_used,
                "normalized_confidence": insertion_controls[0]["normalized_confidence"] if insertion_controls else None,
                "point_keep_ratio": insertion_controls[0]["point_keep_ratio"] if insertion_controls else None,
                "dropped": insertion_controls[0]["dropped"] if insertion_controls else None,
                "insertion_representation": insertion_representation,
            }
        )
        metadata["selected_prior"] = {
            **selected_prior_metadata,
            "object_id": selected_prior_metadata.get("object_id", selected_prior.object_id),
            "score": selected_prior_metadata.get("score", selected_prior.score),
            "mode": selected_prior_metadata.get("mode", selected_prior.mode),
        }
    if selected_prior_metadata_payloads:
        metadata["selected_priors"] = selected_prior_metadata_payloads
    elif selected_priors:
        metadata["selected_priors"] = [
            {
                "object_id": item.object_id,
                "score": item.score,
                "mode": item.mode,
                "asset_format": "gaussian" if insertion_representation == "gaussian_direct" else "point_cloud",
                "gaussian_path": str(resolve_path(str(item.gaussian_path))),
                "category": item.category,
                "feature_path": str(item.feature_path) if item.feature_path else None,
                "candidate_count": item.candidate_count,
                "fallback_used": item.fallback_used,
                "target_object_id": target_payloads[index].get("object_id") if index < len(target_payloads) else None,
                "target_category": target_payloads[index].get("category") if index < len(target_payloads) else None,
                "normalized_confidence": insertion_controls[index]["normalized_confidence"] if index < len(insertion_controls) else None,
                "point_keep_ratio": insertion_controls[index]["point_keep_ratio"] if index < len(insertion_controls) else None,
                "dropped": insertion_controls[index]["dropped"] if index < len(insertion_controls) else None,
            }
            for index, item in enumerate(selected_priors)
        ]
    write_json(metadata_path, metadata)

    if backend_config.dry_run:
        print(f"Saved backend launch metadata to {metadata_path}")
        print(command_to_string(command))
        return 0

    stdout_path = output_dir / "backend_stdout.log"
    stderr_path = output_dir / "backend_stderr.log"
    return_code, elapsed = run_command(
        command,
        workdir=ROOT,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
    metadata.update(
        {
            "status": "completed" if return_code == 0 else "failed",
            "return_code": return_code,
            "elapsed_sec": elapsed,
            "stdout_log": str(stdout_path),
            "stderr_log": str(stderr_path),
        }
    )
    prior_init_metadata = load_prior_init_metadata(backend_config.model_path)
    if prior_init_metadata is not None:
        metadata["prior_init_metadata"] = prior_init_metadata
        metadata["prior_insertion"].update(
            {
                "sh_reset_mode": prior_init_metadata.get(
                    "prior_sh_reset_mode",
                    metadata["prior_insertion"]["sh_reset_mode"],
                ),
                "target_total_gaussians": prior_init_metadata.get(
                    "prior_target_total_gaussians",
                    metadata["prior_insertion"]["target_total_gaussians"],
                ),
                "sfm_region_replacement_mode": prior_init_metadata.get(
                    "sfm_region_replacement_mode",
                    metadata["prior_insertion"]["sfm_region_replacement_mode"],
                ),
                "sfm_removed_point_count": prior_init_metadata.get("sfm_removed_point_count"),
                "sfm_removed_point_ratio": prior_init_metadata.get("sfm_removed_point_ratio"),
            }
        )
        if prior_init_metadata.get("selected_priors"):
            metadata["selected_priors"] = list(prior_init_metadata["selected_priors"])
            metadata["selected_prior"] = metadata["selected_priors"][0]
    write_json(metadata_path, metadata)

    if return_code != 0:
        raise SystemExit(
            f"vanilla_3dgs backend failed with return code {return_code}. See {stderr_path}."
        )

    render_iterations = sorted(set(backend_config.test_iterations or backend_config.save_iterations or (backend_config.iterations,)))
    render_runs: list[dict[str, Any]] = []
    if backend_config.eval and render_iterations:
        for iteration in render_iterations:
            render_command = build_render_command(backend_config, iteration=iteration)
            render_stdout = output_dir / f"render_{iteration}_stdout.log"
            render_stderr = output_dir / f"render_{iteration}_stderr.log"
            render_return_code, render_elapsed = run_command(
                render_command,
                workdir=backend_config.repo_path,
                stdout_path=render_stdout,
                stderr_path=render_stderr,
            )
            render_record = {
                "iteration": iteration,
                "command": render_command,
                "command_string": command_to_string(render_command),
                "return_code": render_return_code,
                "elapsed_sec": render_elapsed,
                "stdout_log": str(render_stdout),
                "stderr_log": str(render_stderr),
            }
            render_runs.append(render_record)
            if render_return_code != 0:
                metadata["status"] = "failed"
                metadata["render_runs"] = render_runs
                write_json(metadata_path, metadata)
                raise SystemExit(
                    f"vanilla_3dgs render failed at iteration {iteration} with return code {render_return_code}. "
                    f"See {render_stderr}."
                )

        metrics_command = build_metrics_command(backend_config)
        metrics_stdout = output_dir / "metrics_stdout.log"
        metrics_stderr = output_dir / "metrics_stderr.log"
        metrics_return_code, metrics_elapsed = run_command(
            metrics_command,
            workdir=backend_config.repo_path,
            stdout_path=metrics_stdout,
            stderr_path=metrics_stderr,
        )
        metrics_run = {
            "command": metrics_command,
            "command_string": command_to_string(metrics_command),
            "return_code": metrics_return_code,
            "elapsed_sec": metrics_elapsed,
            "stdout_log": str(metrics_stdout),
            "stderr_log": str(metrics_stderr),
        }
        metadata["render_runs"] = render_runs
        metadata["metrics_run"] = metrics_run
        write_json(metadata_path, metadata)
        if metrics_return_code != 0:
            metadata["status"] = "failed"
            write_json(metadata_path, metadata)
            raise SystemExit(
                f"vanilla_3dgs metrics failed with return code {metrics_return_code}. See {metrics_stderr}."
            )

        target_psnr = trainer_config.get("target_psnr")
        evaluation = summarize_backend_run(
            metadata_path,
            target_psnr=float(target_psnr) if target_psnr is not None else None,
        )
        evaluation_path = write_evaluation(
            experiment["name"],
            evaluation.to_dict(),
            scene_id=dataset_scene.scene_id if dataset_scene is not None else None,
            outputs_root=outputs_root,
        )
        print(f"Saved evaluation to {evaluation_path}")

    metadata["render_runs"] = render_runs
    write_json(metadata_path, metadata)
    print(f"Saved backend launch metadata to {metadata_path}")
    print(f"Backend stdout log: {stdout_path}")
    print(f"Backend stderr log: {stderr_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a scaffold or backend-backed experiment.")
    parser.add_argument("--config", required=True, type=Path, help="Path to experiment YAML config.")
    parser.add_argument("--dataset-scene-id", type=str, help="Optional override for dataset scene_id.")
    parser.add_argument("--dataset-root", type=Path, help="Optional override for dataset root.")
    parser.add_argument("--prior-config", type=Path, help="Optional override for experiment.prior_config.")
    parser.add_argument("--backend-source-path", type=Path, help="Optional override for backend.source_path.")
    parser.add_argument("--backend-model-path", type=Path, help="Optional override for backend.model_path.")
    parser.add_argument("--outputs-dir", type=Path, help="Optional override for the outputs root directory.")
    parser.add_argument(
        "--alignment-transform-path",
        type=Path,
        help="Optional override for prior_alignment.transform_path.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Build artifacts and commands without launching training.")
    args = parser.parse_args()

    config = load_yaml(resolve_path(str(args.config)))
    if args.prior_config is not None:
        config.setdefault("experiment", {})["prior_config"] = str(args.prior_config)
    if config["experiment"].get("reconstruction_backend") == "vanilla_3dgs":
        return run_vanilla_3dgs_experiment(config, args)
    return run_placeholder_experiment(config, outputs_root=resolve_outputs_root(args.outputs_dir))


if __name__ == "__main__":
    raise SystemExit(main())
