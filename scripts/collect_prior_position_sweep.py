#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw
from plyfile import PlyData, PlyElement

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.gaussian_affine import transform_gaussian_vertex
from priorprobe.validation import prior_position_validator as validator

_REEXEC_ENV = "PRIOR_POSITION_SWEEP_REEXEC"


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
    parser = argparse.ArgumentParser(description="Collect per-prior position sweep validation artifacts.")
    parser.add_argument("--backend-run-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--xy-values", nargs="*", type=float, default=[-0.24, -0.16, -0.08, 0.0, 0.08, 0.16, 0.24])
    parser.add_argument("--z-values", nargs="*", type=float, default=[-0.16, -0.08, -0.04, 0.04, 0.08, 0.16])
    parser.add_argument("--object-ids", nargs="*", type=int, default=None)
    parser.add_argument("--limit-variants", type=int, default=0)
    parser.add_argument("--max-contact-views", type=int, default=16)
    return parser.parse_args()


def _generate_local_offsets(xy_values: list[float], z_values: list[float]) -> list[np.ndarray]:
    offsets: list[np.ndarray] = []
    seen: set[tuple[float, float, float]] = set()
    for dx in xy_values:
        for dy in xy_values:
            triple = (float(dx), float(dy), 0.0)
            if triple in seen:
                continue
            seen.add(triple)
            offsets.append(np.asarray(triple, dtype=np.float32))
    for dz in z_values:
        triple = (0.0, 0.0, float(dz))
        if triple in seen:
            continue
        seen.add(triple)
        offsets.append(np.asarray(triple, dtype=np.float32))
    return offsets


def _load_vertex(path: Path) -> np.ndarray:
    return np.array(PlyData.read(path)["vertex"].data, copy=True)


def _write_vertex(path: Path, vertex: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    PlyData([PlyElement.describe(vertex, "vertex")]).write(path)


def _variant_slug(index: int, local_offset: np.ndarray) -> str:
    dx, dy, dz = [float(x) for x in local_offset.tolist()]
    return f"v{index:03d}_dx{dx:+.2f}_dy{dy:+.2f}_dz{dz:+.2f}".replace(".", "p")


def _select_evenly_spaced_names(names: list[str], count: int) -> list[str]:
    if count <= 0 or not names:
        return []
    ordered = sorted(names)
    if len(ordered) <= count:
        return ordered
    indices = np.linspace(0, len(ordered) - 1, num=count, dtype=int)
    return [ordered[index] for index in indices.tolist()]


def _select_views_for_contact(view_metrics: dict[str, Any], max_views: int) -> list[str]:
    valid = [name for name, payload in view_metrics.items() if payload.get("status") == "valid"]
    if valid:
        return _select_evenly_spaced_names(valid, max_views)
    all_views = sorted(view_metrics.keys())
    return _select_evenly_spaced_names(all_views, max_views)


def _image_edge_background(image: np.ndarray) -> np.ndarray:
    rgb = np.asarray(image)
    if rgb.dtype != np.uint8:
        rgb_float = np.asarray(rgb, dtype=np.float32)
        if rgb_float.size and float(np.nanmax(rgb_float)) <= 1.0:
            rgb_float *= 255.0
        rgb = np.clip(rgb_float, 0.0, 255.0).astype(np.uint8)

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edge = cv2.Canny(blurred, threshold1=20, threshold2=80)
    return np.stack([edge, edge, edge], axis=2)


def _make_comparison_view_image(
    *,
    image: np.ndarray,
    gt_mask: np.ndarray,
    prior_mask: np.ndarray,
    title: str,
    metrics: dict[str, Any],
) -> Image.Image:
    rgb_panel = Image.fromarray(np.asarray(image, dtype=np.uint8), mode="RGB")
    edge_panel = Image.fromarray(_image_edge_background(image), mode="RGB")

    edge_draw = ImageDraw.Draw(edge_panel)
    validator._draw_mask_outline(edge_draw, gt_mask, color=(0, 255, 0))
    validator._draw_mask_outline(edge_draw, prior_mask, color=(255, 64, 64))

    panel_width = rgb_panel.width
    panel_height = rgb_panel.height
    header_height = 44
    canvas = Image.new("RGB", (panel_width * 2, panel_height + header_height), color=(255, 255, 255))
    canvas.paste(rgb_panel, (0, header_height))
    canvas.paste(edge_panel, (panel_width, header_height))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, canvas.width - 1, header_height - 1), fill=(0, 0, 0))
    draw.text((8, 6), title, fill=(255, 255, 255))
    draw.text((8, 24), "left: RGB  |  right: image edges + GT(green) + prior(red)", fill=(220, 220, 220))
    metric_text = (
        f"IoU={metrics.get('mask_iou', 0.0):.3f} "
        f"bbox={metrics.get('bbox_iou', 0.0):.3f} "
        f"centroid={metrics.get('centroid_distance_px')} "
        f"edge={metrics.get('edge_distance_px')}"
    )
    draw.text((panel_width + 8, 6), metric_text, fill=(255, 255, 255))
    return canvas


def _save_variant_artifacts(
    *,
    variant_dir: Path,
    decision_bucket_root: Path,
    scene_root: Path,
    gt_rgbs: dict[str, np.ndarray],
    gt_masks: dict[str, np.ndarray],
    prior_masks: dict[str, np.ndarray],
    view_metrics: dict[str, Any],
    object_id: int,
    local_offset: np.ndarray,
    world_offset: np.ndarray,
    decision: str,
    decision_reasons: list[str],
    max_contact_views: int,
) -> None:
    variant_dir.mkdir(parents=True, exist_ok=True)
    selected_views = _select_views_for_contact(view_metrics, max_contact_views)
    comparison_paths: list[Path] = []
    for view_name in selected_views:
        comparison_path = variant_dir / "comparisons" / f"{Path(view_name).stem}.png"
        comparison = _make_comparison_view_image(
            image=validator._load_overlay_rgb(scene_root, gt_rgbs, view_name),
            gt_mask=gt_masks[view_name],
            prior_mask=prior_masks[view_name],
            title=f"obj {object_id} {view_name}",
            metrics=view_metrics[view_name],
        )
        comparison_path.parent.mkdir(parents=True, exist_ok=True)
        comparison.save(comparison_path)
        comparison_paths.append(comparison_path)
    validator._make_contact_sheet(
        comparison_paths,
        variant_dir / "contact_sheet.png",
        title=f"obj {object_id} decision={decision} offset_local={local_offset.tolist()} offset_world={world_offset.tolist()}",
        columns=4,
    )
    decision_bucket_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        variant_dir / "contact_sheet.png",
        decision_bucket_root / f"obj_{object_id}_{variant_dir.name}.png",
    )
    payload = {
        "object_id": int(object_id),
        "decision": decision,
        "decision_reasons": list(decision_reasons),
        "offset_local_m": [float(x) for x in local_offset.tolist()],
        "offset_world_m": [float(x) for x in world_offset.tolist()],
        "selected_views": selected_views,
        "view_metrics": view_metrics,
        "decision_bucket_contact_sheet": str((decision_bucket_root / f"obj_{object_id}_{variant_dir.name}.png").resolve()),
    }
    (variant_dir / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _metrics_row(
    *,
    object_id: int,
    variant_slug: str,
    decision: str,
    decision_reasons: list[str],
    local_offset: np.ndarray,
    world_offset: np.ndarray,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "object_id": int(object_id),
        "variant": variant_slug,
        "decision": decision,
        "decision_reasons": ";".join(decision_reasons),
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


def _selected_priors_for_sweep(
    selected_priors: list[dict[str, Any]],
    requested_object_ids: set[int],
) -> list[dict[str, Any]]:
    filtered = [
        item
        for item in selected_priors
        if not requested_object_ids or int(item["target_object_id"]) in requested_object_ids
    ]
    if filtered:
        return filtered
    if requested_object_ids:
        joined = ", ".join(str(object_id) for object_id in sorted(requested_object_ids))
        raise ValueError(f"No selected priors matched requested object ids: {joined}")
    raise ValueError("No selected priors available for sweep")


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

    inputs = validator.resolve_position_validation_inputs(args.backend_run_dir)
    if inputs.input_consistency.get("status") != "OK":
        raise RuntimeError(f"Input mismatch: {inputs.input_consistency}")
    if not inputs.selected_priors:
        raise RuntimeError("Base run has no selected priors")

    thresholds = validator.ValidationThresholds()
    offsets = _generate_local_offsets(list(args.xy_values), list(args.z_values))
    if int(args.limit_variants) > 0:
        offsets = offsets[: int(args.limit_variants)]
    if not offsets:
        raise ValueError("No local offsets were generated from --xy-values/--z-values")
    gt_bundle = validator._render_gt_semantic_bundle(
        inputs,
        sample_count=int(thresholds.sample_count),
        apply_binary_closing=bool(thresholds.apply_binary_closing),
    )
    modules, train_view_names, test_cameras, cameras_extent, separate_sh = validator._build_render_context(inputs)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    decision_root = args.output_dir / "by_decision"
    aggregate_rows: list[dict[str, Any]] = []
    aggregate_summary: dict[str, Any] = {
        "base_backend_run_dir": str(args.backend_run_dir.resolve()),
        "scene_id": inputs.scene_id,
        "dataset_family": inputs.dataset_family,
        "offset_count_per_object": len(offsets),
        "decision_bucket_root": str(decision_root.resolve()),
        "objects": {},
    }

    requested_object_ids = {int(item) for item in (args.object_ids or [])}
    selected_priors = _selected_priors_for_sweep(inputs.selected_priors, requested_object_ids)
    for selected in selected_priors:
        object_id = int(selected["target_object_id"])
        object_dir = args.output_dir / f"object_{object_id}"
        aligned_path = Path(str(selected["aligned_prior"]))
        base_vertex = _load_vertex(aligned_path)
        rotation = np.asarray(
            selected.get("alignment", {}).get("rotation_matrix")
            or selected.get("alignment_debug", {}).get("target_rotation_matrix")
            or np.eye(3, dtype=np.float32),
            dtype=np.float32,
        ).reshape(3, 3)
        rows: list[dict[str, Any]] = []
        decision_counts = {"PASS": 0, "FAIL": 0, "AMBIGUOUS": 0}

        for index, local_offset in enumerate(offsets):
            world_offset = rotation @ np.asarray(local_offset, dtype=np.float32)
            shifted_vertex = transform_gaussian_vertex(
                base_vertex,
                rotation_matrix=np.eye(3, dtype=np.float32),
                scale=np.ones(3, dtype=np.float32),
                translation=np.asarray(world_offset, dtype=np.float32),
            )
            variant_slug = _variant_slug(index, local_offset)
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
            rows.append(
                _metrics_row(
                    object_id=object_id,
                    variant_slug=variant_slug,
                    decision=decision,
                    decision_reasons=reasons,
                    local_offset=local_offset,
                    world_offset=world_offset,
                    metrics=metrics,
                )
            )
            aggregate_rows.append(rows[-1])
            _save_variant_artifacts(
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
                        "decision": decision,
                        "offset_local_m": [float(x) for x in local_offset.tolist()],
                        "offset_world_m": [float(x) for x in world_offset.tolist()],
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
                    "variants": rows,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        aggregate_summary["objects"][str(object_id)] = {
            "decision_counts": decision_counts,
            "variant_count": len(rows),
            "summary_csv": str(object_csv_path),
            "summary_json": str(object_json_path),
        }

    aggregate_csv_path = args.output_dir / "aggregate_summary.csv"
    if not aggregate_rows:
        raise ValueError("No sweep variants were generated after filtering requested objects")
    _write_rows_csv(aggregate_csv_path, aggregate_rows)
    (args.output_dir / "aggregate_summary.json").write_text(
        json.dumps(aggregate_summary, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "output_dir": str(args.output_dir.resolve()),
                "aggregate_csv": str(aggregate_csv_path.resolve()),
                "aggregate_json": str((args.output_dir / 'aggregate_summary.json').resolve()),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
