#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from plyfile import PlyData


ROOT = Path(__file__).resolve().parents[1]


DEFAULT_EXPERIMENTS = [
    "gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_15000",
    "gaussian_direct_same_scene_exact_clip_15000",
    "gaussian_direct_merged_oracle_select_clip_15000",
    "gaussian_direct_merged_clip_retrieval_15000",
    "gaussian_direct_existing_clip_only_15000",
]

SMOKE_EXPERIMENTS = [
    "gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_smoke_1000",
    "gaussian_direct_same_scene_exact_clip_smoke_1000",
    "gaussian_direct_merged_oracle_select_clip_smoke_1000",
    "gaussian_direct_merged_clip_retrieval_smoke_1000",
    "gaussian_direct_existing_clip_only_smoke_1000",
]


def resolve_path(path_value: Path) -> Path:
    return path_value if path_value.is_absolute() else ROOT / path_value


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def count_ply_vertices(path: Path) -> int | None:
    if not path.exists():
        return None
    return int(PlyData.read(path)["vertex"].count)


def load_prior_init_metadata(model_path: Path) -> dict[str, Any] | None:
    metadata_path = model_path / "prior_init" / "metadata.json"
    if not metadata_path.exists():
        return None
    return load_json(metadata_path)


def collect_rows(outputs_dir: Path, experiments: list[str], scene_ids: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for experiment_name in experiments:
        for scene_id in scene_ids:
            evaluation_path = outputs_dir / "experiments" / experiment_name / scene_id / "evaluation.json"
            backend_run_path = outputs_dir / "experiments" / experiment_name / scene_id / "backend_run.json"
            if not evaluation_path.exists() or not backend_run_path.exists():
                continue
            evaluation = load_json(evaluation_path)
            backend_run = load_json(backend_run_path)
            model_path = resolve_path(Path(str(backend_run["model_path"])))
            prior_init_metadata = load_prior_init_metadata(model_path)
            initial_snapshot = model_path / "point_cloud" / "iteration_0" / "point_cloud.ply"
            initial_gaussian_count = count_ply_vertices(initial_snapshot)
            inserted_gaussian_count = None
            if prior_init_metadata is not None:
                inserted_gaussian_count = int(
                    sum(int(item.get("kept_point_count", 0) or 0) for item in prior_init_metadata.get("selected_priors", []))
                )
            rows.append(
                {
                    "experiment_name": experiment_name,
                    "scene_id": scene_id,
                    "evaluation": evaluation,
                    "backend_run": backend_run,
                    "prior_init_metadata": prior_init_metadata,
                    "initial_gaussian_count": initial_gaussian_count,
                    "inserted_gaussian_count": inserted_gaussian_count,
                }
            )
    return rows


def provenance_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        backend_run = row["backend_run"]
        selected_priors = backend_run.get("selected_priors") or []
        oracle_targets = backend_run.get("oracle_targets") or []
        for selected, target in zip(selected_priors, oracle_targets):
            extras = dict(selected.get("metadata_extras") or {})
            expected_key = f"{target.get('scene_id')}:{target.get('object_id')}"
            candidate_key = extras.get("exact_match_key")
            candidate_scene = extras.get("replica_scene_id")
            candidate_object = extras.get("replica_object_id")
            exact_match = candidate_key == expected_key or (
                str(candidate_scene) == str(target.get("scene_id"))
                and str(candidate_object) == str(target.get("object_id"))
            )
            output.append(
                {
                    "experiment_name": row["experiment_name"],
                    "scene_id": row["scene_id"],
                    "target_object_id": target.get("object_id"),
                    "target_category": target.get("category"),
                    "selected_prior": selected.get("object_id"),
                    "selected_category": selected.get("category"),
                    "retrieval_mode": selected.get("mode"),
                    "score": selected.get("score"),
                    "exact_match": exact_match,
                    "same_scene_match": bool(extras.get("same_scene_match", False)),
                    "asset_format": selected.get("asset_format")
                    or ("gaussian" if selected.get("insertion_representation") == "gaussian_direct" else None),
                }
            )
    return output


def checkpoint_psnr_for_reference_iteration(
    evaluation: dict[str, Any],
    *,
    reference_iteration: int,
) -> tuple[float | None, int | None]:
    checkpoints = list(evaluation.get("checkpoint_metrics") or [])
    if not checkpoints:
        return None, None
    checkpoints = sorted(checkpoints, key=lambda item: int(item.get("iteration", 0)))
    exact_match = next((item for item in checkpoints if int(item.get("iteration", 0)) == reference_iteration), None)
    if exact_match is not None:
        psnr = exact_match.get("psnr")
        return (float(psnr), reference_iteration) if psnr is not None else (None, reference_iteration)
    eligible = [item for item in checkpoints if int(item.get("iteration", 0)) <= reference_iteration]
    chosen = eligible[-1] if eligible else checkpoints[-1]
    psnr = chosen.get("psnr")
    return (float(psnr), int(chosen.get("iteration", 0))) if psnr is not None else (None, int(chosen.get("iteration", 0)))


def derive_target_psnr_by_scene(
    rows: list[dict[str, Any]],
    *,
    baseline_experiment: str,
    reference_iteration: int,
) -> dict[str, dict[str, Any]]:
    scene_targets: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row["experiment_name"] != baseline_experiment:
            continue
        target_psnr, actual_iteration = checkpoint_psnr_for_reference_iteration(
            row["evaluation"],
            reference_iteration=reference_iteration,
        )
        if target_psnr is None:
            continue
        scene_targets[str(row["scene_id"])] = {
            "target_psnr": target_psnr,
            "reference_iteration": actual_iteration,
        }
    return scene_targets


def derive_time_to_target_sec(evaluation: dict[str, Any], *, target_psnr: float | None) -> float | None:
    if target_psnr is None:
        return None
    checkpoints = sorted(
        list(evaluation.get("checkpoint_metrics") or []),
        key=lambda item: float(item.get("estimated_elapsed_sec", 0.0) or 0.0),
    )
    for checkpoint in checkpoints:
        checkpoint_psnr = checkpoint.get("psnr")
        if checkpoint_psnr is None:
            continue
        if float(checkpoint_psnr) >= float(target_psnr):
            elapsed = checkpoint.get("estimated_elapsed_sec")
            return float(elapsed) if elapsed is not None else None
    return None


def summarize_provenance(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    summary: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row["experiment_name"]), str(row["scene_id"]))
        item = summary.setdefault(
            key,
            {
                "count": 0,
                "exact_match_count": 0,
                "same_scene_match_count": 0,
                "gaussian_asset_count": 0,
            },
        )
        item["count"] += 1
        item["exact_match_count"] += 1 if row.get("exact_match") else 0
        item["same_scene_match_count"] += 1 if row.get("same_scene_match") else 0
        item["gaussian_asset_count"] += 1 if row.get("asset_format") == "gaussian" else 0
    return summary


def format_targets_table(scene_targets: dict[str, dict[str, Any]]) -> str:
    lines = [
        "| scene | target_psnr | reference_iteration |",
        "|---|---:|---:|",
    ]
    for scene_id, payload in scene_targets.items():
        lines.append(
            "| {scene_id} | {target_psnr:.6f} | {reference_iteration} |".format(
                scene_id=scene_id,
                target_psnr=float(payload["target_psnr"]),
                reference_iteration=int(payload["reference_iteration"]),
            )
        )
    return "\n".join(lines)


def format_results_table(rows: list[dict[str, Any]], *, scene_targets: dict[str, dict[str, Any]]) -> str:
    prov_summary = summarize_provenance(provenance_rows(rows))
    lines = [
        "| experiment | scene | target_psnr | time_to_target_sec | total_time_sec | psnr | ssim | lpips | prior_count | initial_gaussians | inserted_gaussians | exact_match_rate | same_scene_rate |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        evaluation = row["evaluation"]
        summary = prov_summary.get((row["experiment_name"], row["scene_id"]), {})
        count = int(summary.get("count", 0) or 0)
        exact_rate = (summary.get("exact_match_count", 0) / count) if count else None
        same_scene_rate = (summary.get("same_scene_match_count", 0) / count) if count else None
        scene_target = scene_targets.get(str(row["scene_id"]), {})
        derived_target_psnr = scene_target.get("target_psnr")
        derived_time_to_target = derive_time_to_target_sec(
            evaluation,
            target_psnr=float(derived_target_psnr) if derived_target_psnr is not None else None,
        )
        reported_time_to_target = evaluation.get("time_to_target_quality_sec")
        final_time_to_target = (
            float(reported_time_to_target)
            if reported_time_to_target is not None
            else derived_time_to_target
        )
        lines.append(
            "| {experiment_name} | {scene_id} | {target_psnr} | {time_to_target_sec} | {total_optimization_time_sec} | {psnr} | {ssim} | {lpips} | {prior_count} | {initial_gaussian_count} | {inserted_gaussian_count} | {exact_rate} | {same_scene_rate} |".format(
                experiment_name=row["experiment_name"],
                scene_id=row["scene_id"],
                target_psnr=f"{float(derived_target_psnr):.6f}" if derived_target_psnr is not None else "n/a",
                time_to_target_sec=f"{float(final_time_to_target):.6f}" if final_time_to_target is not None else "n/a",
                total_optimization_time_sec=evaluation.get("total_optimization_time_sec"),
                psnr=evaluation.get("psnr"),
                ssim=evaluation.get("ssim"),
                lpips=evaluation.get("lpips"),
                prior_count=evaluation.get("prior_count"),
                initial_gaussian_count=row.get("initial_gaussian_count"),
                inserted_gaussian_count=row.get("inserted_gaussian_count"),
                exact_rate=f"{exact_rate:.3f}" if exact_rate is not None else "n/a",
                same_scene_rate=f"{same_scene_rate:.3f}" if same_scene_rate is not None else "n/a",
            )
        )
    return "\n".join(lines)


def format_provenance_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| experiment | scene | target_object | target_category | selected_prior | selected_category | score | exact_match | same_scene_match | asset_format |",
        "|---|---|---:|---|---|---|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {experiment_name} | {scene_id} | {target_object_id} | {target_category} | {selected_prior} | {selected_category} | {score} | {exact_match} | {same_scene_match} | {asset_format} |".format(
                **row
            )
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a markdown report for the Replica gaussian-direct upper-bound study.")
    parser.add_argument("--outputs-dir", type=Path, default=Path("outputs/gaussian_direct"))
    parser.add_argument("--scene-id", action="append", dest="scene_ids")
    parser.add_argument("--experiment", action="append", dest="experiments")
    parser.add_argument("--smoke", action="store_true", help="Use the 1000-iteration smoke experiment names by default.")
    parser.add_argument(
        "--baseline-iteration",
        type=int,
        default=3000,
        help="Reference baseline checkpoint iteration used to derive the target PSNR when evaluation JSON lacks time_to_target_quality_sec.",
    )
    parser.add_argument(
        "--baseline-experiment",
        type=str,
        help="Optional baseline experiment name used to derive the target PSNR threshold.",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    outputs_dir = resolve_path(args.outputs_dir)
    scene_ids = list(args.scene_ids or ["room_0", "office_0"])
    default_experiments = SMOKE_EXPERIMENTS if args.smoke else DEFAULT_EXPERIMENTS
    experiments = list(args.experiments or default_experiments)
    baseline_experiment = args.baseline_experiment or (
        "gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_smoke_1000"
        if args.smoke
        else "gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_15000"
    )
    output_path = (
        resolve_path(args.output)
        if args.output is not None
        else ROOT
        / "docs"
        / "experiments"
        / f"replica_gaussian_direct_upper_bound_{datetime.now(UTC).strftime('%Y-%m-%d')}.md"
    )

    rows = collect_rows(outputs_dir, experiments, scene_ids)
    scene_targets = derive_target_psnr_by_scene(
        rows,
        baseline_experiment=baseline_experiment,
        reference_iteration=args.baseline_iteration,
    )
    prov_rows = provenance_rows(rows)

    lines = [
        "# Replica Gaussian-Direct Upper Bound",
        "",
        "## Assumptions",
        "",
        "- Prior insertion uses `gaussian_direct` rather than point-cloud proxy conversion.",
        "- Alignment is fixed to `oracle_target_box` for all prior-based runs.",
        "- `same_scene_exact` and `merged_oracle_select` are upper-bound settings, not generalization settings.",
        f"- Target PSNR is derived from `{baseline_experiment}` at iteration {args.baseline_iteration}, or the nearest earlier checkpoint when that iteration is absent.",
        "",
        "## Target Quality Thresholds",
        "",
        format_targets_table(scene_targets),
        "",
        "## Results",
        "",
        format_results_table(rows, scene_targets=scene_targets),
        "",
        "## Retrieval Provenance",
        "",
        format_provenance_table(prov_rows),
        "",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote report to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
