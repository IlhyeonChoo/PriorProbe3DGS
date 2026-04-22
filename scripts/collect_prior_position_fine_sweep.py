#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np
from plyfile import PlyData, PlyElement

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.gaussian_affine import transform_gaussian_vertex
from priorprobe.validation import prior_position_validator as validator

_REEXEC_ENV = "PRIOR_POSITION_FINE_SWEEP_REEXEC"

DEFAULT_ANCHORS = {
    "11": ["v020_dx-0p08_dy+0p24_dz+0p00", "v027_dx+0p00_dy+0p24_dz+0p00"],
    "73": ["v020_dx-0p08_dy+0p24_dz+0p00", "v027_dx+0p00_dy+0p24_dz+0p00"],
    "74": ["v020_dx-0p08_dy+0p24_dz+0p00", "v027_dx+0p00_dy+0p24_dz+0p00", "v034_dx+0p08_dy+0p24_dz+0p00"],
    "77": ["v050_dx+0p00_dy+0p00_dz-0p08"],
}


def _load_sweep_helpers():
    script_path = ROOT / "scripts" / "collect_prior_position_sweep.py"
    spec = importlib.util.spec_from_file_location("collect_prior_position_sweep", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


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


def _resolve_backend_python(backend_run_dir: Path) -> Path | None:
    backend_run_json_path = _derive_backend_run_json_path(backend_run_dir)
    if backend_run_json_path is not None:
        backend_run = json.loads(backend_run_json_path.read_text(encoding="utf-8"))
        command = backend_run.get("command") or []
        if command:
            candidate = Path(str(command[0]))
            if candidate.exists():
                return candidate
        repo_path = backend_run.get("repo_path")
        if repo_path:
            candidate = Path(str(repo_path)) / "venv" / "bin" / "python"
            if candidate.exists():
                return candidate
    return None


def _maybe_reexec_under_backend_python(backend_run_dir: Path) -> None:
    if os.environ.get(_REEXEC_ENV) == "1":
        return
    backend_python = _resolve_backend_python(backend_run_dir)
    if backend_python is None:
        return
    if backend_python.resolve() == Path(sys.executable).resolve():
        return
    env = dict(os.environ)
    env[_REEXEC_ENV] = "1"
    os.execve(str(backend_python), [str(backend_python), __file__, *sys.argv[1:]], env)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect fine prior position sweeps around user-approved anchor variants.")
    parser.add_argument("--backend-run-dir", required=True, type=Path)
    parser.add_argument("--coarse-sweep-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--variants-per-object", type=int, default=100)
    parser.add_argument("--object-ids", nargs="*", type=int, default=None)
    parser.add_argument("--max-contact-views", type=int, default=16)
    parser.add_argument("--xy-deltas", nargs="*", type=float, default=[-0.06, -0.045, -0.03, -0.015, 0.0, 0.015, 0.03, 0.045, 0.06])
    parser.add_argument("--z-deltas", nargs="*", type=float, default=[-0.03, -0.015, 0.0, 0.015, 0.03])
    parser.add_argument("--anchor-spec-json", type=Path, default=None)
    parser.add_argument("--override-source-prior-json", type=Path, default=None)
    return parser.parse_args()


def _load_anchor_spec(path: Path | None) -> dict[str, list[str]]:
    if path is None:
        return dict(DEFAULT_ANCHORS)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object->variants mapping in {path}")
    return {str(key): [str(item) for item in value] for key, value in payload.items()}


def _load_override_source_prior_map(path: Path | None) -> dict[int, Path]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object->source_prior mapping in {path}")
    return {int(key): Path(str(value)).resolve() for key, value in payload.items()}


def _load_vertex(path: Path) -> np.ndarray:
    return np.array(PlyData.read(path)["vertex"].data, copy=True)


def _write_vertex(path: Path, vertex: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    PlyData([PlyElement.describe(vertex, "vertex")]).write(path)


def _aligned_base_vertex(selected: dict[str, Any], override_source_prior_map: dict[int, Path]) -> np.ndarray:
    object_id = int(selected["target_object_id"])
    if object_id not in override_source_prior_map:
        return _load_vertex(Path(str(selected["aligned_prior"])))
    source_vertex = _load_vertex(override_source_prior_map[object_id])
    alignment = dict(selected.get("alignment") or {})
    alignment_debug = dict(selected.get("alignment_debug") or {})
    rotation = np.asarray(
        alignment.get("rotation_matrix")
        or alignment_debug.get("target_rotation_matrix")
        or np.eye(3, dtype=np.float32),
        dtype=np.float32,
    ).reshape(3, 3)
    scale = np.asarray(alignment.get("scale") or [1.0, 1.0, 1.0], dtype=np.float32).reshape(3)
    translation = np.asarray(alignment.get("translation") or [0.0, 0.0, 0.0], dtype=np.float32).reshape(3)
    return transform_gaussian_vertex(
        source_vertex,
        rotation_matrix=rotation,
        scale=scale,
        translation=translation,
    )


def _sorted_micro_offsets(xy_deltas: list[float], z_deltas: list[float]) -> list[np.ndarray]:
    offsets: list[np.ndarray] = []
    for dz in z_deltas:
        for dx in xy_deltas:
            for dy in xy_deltas:
                offsets.append(np.asarray([float(dx), float(dy), float(dz)], dtype=np.float32))
    offsets.sort(key=lambda item: (float(np.linalg.norm(item)), abs(float(item[2])), abs(float(item[0])) + abs(float(item[1])), float(item[0]), float(item[1]), float(item[2])))
    unique: list[np.ndarray] = []
    seen: set[tuple[float, float, float]] = set()
    for item in offsets:
        key = tuple(round(float(x), 6) for x in item.tolist())
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _load_variant_rows(summary_path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    rows = payload.get("variants") or []
    return {str(row["variant"]): dict(row) for row in rows}


def _distribute_counts(total: int, anchor_count: int) -> list[int]:
    base = total // anchor_count
    remainder = total % anchor_count
    counts = []
    for index in range(anchor_count):
        counts.append(base + (1 if index < remainder else 0))
    return counts


def _build_object_variant_plan(
    *,
    object_id: int,
    anchor_variants: list[str],
    coarse_object_summary: Path,
    micro_offsets: list[np.ndarray],
    total_count: int,
) -> list[dict[str, Any]]:
    if not anchor_variants:
        raise ValueError(f"Anchor variant list is empty for object {object_id}")
    variant_rows = _load_variant_rows(coarse_object_summary)
    counts = _distribute_counts(total_count, len(anchor_variants))
    used: set[tuple[float, float, float]] = set()
    plan: list[dict[str, Any]] = []
    for anchor_index, (anchor_variant, required_count) in enumerate(zip(anchor_variants, counts, strict=False)):
        if anchor_variant not in variant_rows:
            raise ValueError(f"Anchor variant {anchor_variant} missing in {coarse_object_summary}")
        anchor_row = variant_rows[anchor_variant]
        anchor_local = np.asarray(
            [
                float(anchor_row["offset_local_x_m"]),
                float(anchor_row["offset_local_y_m"]),
                float(anchor_row["offset_local_z_m"]),
            ],
            dtype=np.float32,
        )
        selected_for_anchor = 0
        for delta_index, micro_delta in enumerate(micro_offsets):
            candidate_local = anchor_local + micro_delta
            key = tuple(round(float(value), 6) for value in candidate_local.tolist())
            if key in used:
                continue
            used.add(key)
            plan.append(
                {
                    "object_id": int(object_id),
                    "anchor_variant": anchor_variant,
                    "anchor_index": anchor_index,
                    "anchor_local_offset_m": [float(value) for value in anchor_local.tolist()],
                    "micro_delta_local_m": [float(value) for value in micro_delta.tolist()],
                    "candidate_local_offset_m": [float(value) for value in candidate_local.tolist()],
                    "sequence_index": selected_for_anchor,
                }
            )
            selected_for_anchor += 1
            if selected_for_anchor >= required_count:
                break
        if selected_for_anchor < required_count:
            raise ValueError(
                f"Not enough unique fine offsets for object {object_id} anchor {anchor_variant}: {selected_for_anchor} < {required_count}"
            )
    if len(plan) != total_count:
        raise ValueError(f"Expected {total_count} variants for object {object_id}, got {len(plan)}")
    return plan


def _fine_variant_slug(index: int, local_offset: np.ndarray, anchor_variant: str) -> str:
    dx, dy, dz = [float(value) for value in local_offset.tolist()]
    anchor_token = anchor_variant.split("_", 1)[0]
    return (
        f"{anchor_token}_f{index:03d}_dx{dx:+.3f}_dy{dy:+.3f}_dz{dz:+.3f}".replace(".", "p")
    )


def _metrics_row(
    *,
    object_id: int,
    variant_slug: str,
    decision: str,
    decision_reasons: list[str],
    anchor_variant: str,
    anchor_local: np.ndarray,
    local_offset: np.ndarray,
    world_offset: np.ndarray,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "object_id": int(object_id),
        "anchor_variant": anchor_variant,
        "variant": variant_slug,
        "decision": decision,
        "decision_reasons": ";".join(decision_reasons),
        "anchor_local_x_m": float(anchor_local[0]),
        "anchor_local_y_m": float(anchor_local[1]),
        "anchor_local_z_m": float(anchor_local[2]),
        "offset_local_x_m": float(local_offset[0]),
        "offset_local_y_m": float(local_offset[1]),
        "offset_local_z_m": float(local_offset[2]),
        "offset_world_x_m": float(world_offset[0]),
        "offset_world_y_m": float(world_offset[1]),
        "offset_world_z_m": float(world_offset[2]),
        "median_mask_iou": metrics.get("median_mask_iou"),
        "median_bbox_iou": metrics.get("median_bbox_iou"),
        "median_centroid_distance_px": metrics.get("median_centroid_distance_px"),
        "median_edge_distance_px": metrics.get("median_edge_distance_px"),
        "median_coverage_ratio": metrics.get("median_coverage_ratio"),
        "valid_view_count": metrics.get("valid_view_count"),
        "ignored_view_count": metrics.get("ignored_view_count"),
        "invalid_view_count": metrics.get("invalid_view_count"),
        "gt_low_confidence_view_count": metrics.get("gt_low_confidence_view_count"),
    }


def _validate_variants_per_object(value: int) -> int:
    if int(value) <= 0:
        raise ValueError(f"--variants-per-object must be > 0, got {value}")
    return int(value)


def _selected_fine_sweep_object_ids(
    anchor_spec: dict[str, list[str]],
    requested_object_ids: set[int],
) -> list[int]:
    object_ids = [
        int(object_key)
        for object_key in anchor_spec.keys()
        if not requested_object_ids or int(object_key) in requested_object_ids
    ]
    if object_ids:
        return object_ids
    if requested_object_ids:
        joined = ", ".join(str(object_id) for object_id in sorted(requested_object_ids))
        raise ValueError(f"No anchor-spec objects matched requested object ids: {joined}")
    raise ValueError("Anchor spec contains no objects for fine sweep")


def _write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = list(rows[0].keys()) if rows else []
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def main() -> int:
    args = parse_args()
    _maybe_reexec_under_backend_python(args.backend_run_dir)
    sweep_helpers = _load_sweep_helpers()

    inputs = validator.resolve_position_validation_inputs(args.backend_run_dir)
    if inputs.input_consistency.get("status") != "OK":
        raise RuntimeError(f"Input mismatch: {inputs.input_consistency}")
    thresholds = validator.ValidationThresholds()
    gt_bundle = validator._render_gt_semantic_bundle(
        inputs,
        sample_count=int(thresholds.sample_count),
        apply_binary_closing=bool(thresholds.apply_binary_closing),
    )
    modules, train_view_names, test_cameras, cameras_extent, separate_sh = validator._build_render_context(inputs)
    anchor_spec = _load_anchor_spec(args.anchor_spec_json)
    override_source_prior_map = _load_override_source_prior_map(args.override_source_prior_json)
    micro_offsets = _sorted_micro_offsets(list(args.xy_deltas), list(args.z_deltas))
    if not micro_offsets:
        raise ValueError("No micro offsets were generated from --xy-deltas/--z-deltas")
    variants_per_object = _validate_variants_per_object(int(args.variants_per_object))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    decision_root = args.output_dir / "by_decision"
    aggregate_rows: list[dict[str, Any]] = []
    aggregate_summary: dict[str, Any] = {
        "base_backend_run_dir": str(args.backend_run_dir.resolve()),
        "coarse_sweep_root": str(args.coarse_sweep_root.resolve()),
        "scene_id": inputs.scene_id,
        "dataset_family": inputs.dataset_family,
        "variants_per_object": int(args.variants_per_object),
        "micro_xy_deltas_m": [float(value) for value in args.xy_deltas],
        "micro_z_deltas_m": [float(value) for value in args.z_deltas],
        "decision_bucket_root": str(decision_root.resolve()),
        "objects": {},
    }

    selected_priors_by_id = {int(item["target_object_id"]): item for item in inputs.selected_priors}
    requested_object_ids = {int(item) for item in (args.object_ids or [])}
    object_ids = _selected_fine_sweep_object_ids(anchor_spec, requested_object_ids)
    for object_id in object_ids:
        anchor_variants = list(anchor_spec[str(object_id)])
        if object_id not in selected_priors_by_id:
            raise ValueError(f"Object {object_id} not found in selected priors")
        selected = selected_priors_by_id[object_id]
        rotation = np.asarray(
            selected.get("alignment", {}).get("rotation_matrix")
            or selected.get("alignment_debug", {}).get("target_rotation_matrix")
            or np.eye(3, dtype=np.float32),
            dtype=np.float32,
        ).reshape(3, 3)
        base_vertex = _aligned_base_vertex(selected, override_source_prior_map)
        object_dir = args.output_dir / f"object_{object_id}"
        coarse_summary_path = args.coarse_sweep_root / f"object_{object_id}" / "summary.json"
        plan = _build_object_variant_plan(
            object_id=object_id,
            anchor_variants=list(anchor_variants),
            coarse_object_summary=coarse_summary_path,
            micro_offsets=micro_offsets,
            total_count=variants_per_object,
        )
        rows: list[dict[str, Any]] = []
        decision_counts = {"PASS": 0, "FAIL": 0, "AMBIGUOUS": 0}

        for index, plan_item in enumerate(plan):
            local_offset = np.asarray(plan_item["candidate_local_offset_m"], dtype=np.float32)
            anchor_local = np.asarray(plan_item["anchor_local_offset_m"], dtype=np.float32)
            world_offset = rotation @ local_offset
            shifted_vertex = transform_gaussian_vertex(
                base_vertex,
                rotation_matrix=np.eye(3, dtype=np.float32),
                scale=np.ones(3, dtype=np.float32),
                translation=np.asarray(world_offset, dtype=np.float32),
            )
            variant_slug = _fine_variant_slug(index, local_offset, str(plan_item["anchor_variant"]))
            variant_dir = object_dir / variant_slug
            aligned_variant_path = variant_dir / "aligned_prior.ply"
            _write_vertex(aligned_variant_path, shifted_vertex)
            gaussians = validator._load_gaussian_from_aligned_paths(
                [aligned_variant_path],
                modules=modules,
                sh_degree=int(getattr(inputs.cfg_args, "sh_degree", 3)),
                train_view_names=train_view_names,
                cameras_extent=cameras_extent,
                train_test_exp=bool(getattr(inputs.cfg_args, "train_test_exp", False)),
            )
            renders = validator._render_gaussian_model_views(
                gaussians,
                modules=modules,
                test_cameras=test_cameras,
                cfg_args=inputs.cfg_args,
                separate_sh=separate_sh,
            )
            prior_masks = {
                object_id: {
                    view_name: (np.asarray(frame.depth, dtype=np.float32) > 0.0)
                    for view_name, frame in renders.items()
                }
            }
            metrics = validator.compute_position_metrics(
                {object_id: gt_bundle.masks[object_id]},
                prior_masks,
                min_visible_pixel_ratio=float(thresholds.min_visible_pixel_ratio),
            )[object_id]
            decision, reasons, _, _ = validator._object_decision(metrics, thresholds)
            decision_counts[decision] = decision_counts.get(decision, 0) + 1
            row = _metrics_row(
                object_id=object_id,
                variant_slug=variant_slug,
                decision=decision,
                decision_reasons=reasons,
                anchor_variant=str(plan_item["anchor_variant"]),
                anchor_local=anchor_local,
                local_offset=local_offset,
                world_offset=world_offset,
                metrics=metrics,
            )
            rows.append(row)
            aggregate_rows.append(row)
            sweep_helpers._save_variant_artifacts(
                variant_dir=variant_dir,
                decision_bucket_root=decision_root / decision,
                scene_root=inputs.scene_root,
                gt_rgbs=gt_bundle.rgbs,
                gt_masks=gt_bundle.masks[object_id],
                prior_masks=prior_masks[object_id],
                view_metrics=metrics["views"],
                object_id=object_id,
                local_offset=local_offset,
                world_offset=world_offset,
                decision=decision,
                decision_reasons=reasons,
                max_contact_views=int(args.max_contact_views),
            )
            print(
                json.dumps(
                    {
                        "object_id": object_id,
                        "variant": variant_slug,
                        "anchor_variant": plan_item["anchor_variant"],
                        "decision": decision,
                        "offset_local_m": [float(value) for value in local_offset.tolist()],
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )

        object_csv_path = object_dir / "summary.csv"
        _write_rows_csv(object_csv_path, rows)
        object_json_path = object_dir / "summary.json"
        object_json_path.write_text(
            json.dumps(
                {
                    "object_id": object_id,
                    "decision_counts": decision_counts,
                    "variant_count": len(rows),
                    "anchor_variants": list(anchor_variants),
                    "variants": rows,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        aggregate_summary["objects"][str(object_id)] = {
            "decision_counts": decision_counts,
            "variant_count": len(rows),
            "anchor_variants": list(anchor_variants),
            "summary_csv": str(object_csv_path),
            "summary_json": str(object_json_path),
        }

    if not aggregate_rows:
        raise ValueError("No fine sweep variants were generated after filtering requested objects")
    aggregate_csv_path = args.output_dir / "aggregate_summary.csv"
    _write_rows_csv(aggregate_csv_path, aggregate_rows)
    aggregate_json_path = args.output_dir / "aggregate_summary.json"
    aggregate_json_path.write_text(json.dumps(aggregate_summary, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_dir": str(args.output_dir.resolve()),
                "aggregate_csv": str(aggregate_csv_path.resolve()),
                "aggregate_json": str(aggregate_json_path.resolve()),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
