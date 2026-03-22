#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

DATASET_FAMILIES = {
    "96_view": {
        "label": "Replica 96-view",
        "baseline_experiment": "gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_15000",
        "experiments": [
            "gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_15000",
            "gaussian_direct_same_scene_exact_clip_15000",
            "gaussian_direct_same_scene_exact_clip_weak_15000",
        ],
    },
    "dense_384": {
        "label": "Replica dense diverse 384-view",
        "baseline_experiment": "gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_diverse_384_15000",
        "experiments": [
            "gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_diverse_384_15000",
            "gaussian_direct_same_scene_exact_clip_diverse_384_15000",
            "gaussian_direct_same_scene_exact_clip_diverse_384_weak_15000",
            "gaussian_direct_same_scene_exact_clip_diverse_384_freeze_15000",
        ],
    },
}

CHECKPOINT_ITERATIONS = (0, 3000, 15000)


def resolve_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def mode_label(backend_run: dict[str, Any]) -> str:
    protection = dict(backend_run.get("prior_protection") or {})
    mode = str(protection.get("mode") or "none")
    if mode == "none":
        return "none"
    if mode == "weak":
        return f"weak({float(protection.get('lr_scale', 0.0)):.2f})"
    return mode


def collect_rows(outputs_dir: Path, scene_ids: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family_id, family in DATASET_FAMILIES.items():
        for experiment_name in family["experiments"]:
            for scene_id in scene_ids:
                experiment_dir = outputs_dir / "experiments" / experiment_name / scene_id
                evaluation_path = experiment_dir / "evaluation.json"
                backend_run_path = experiment_dir / "backend_run.json"
                if not evaluation_path.exists() or not backend_run_path.exists():
                    continue
                evaluation = load_json(evaluation_path)
                backend_run = load_json(backend_run_path)
                rows.append(
                    {
                        "family_id": family_id,
                        "family_label": family["label"],
                        "experiment_name": experiment_name,
                        "scene_id": scene_id,
                        "evaluation": evaluation,
                        "backend_run": backend_run,
                    }
                )
    return rows


def checkpoint_by_iteration(evaluation: dict[str, Any], iteration: int) -> dict[str, Any] | None:
    for checkpoint in evaluation.get("checkpoint_metrics", []):
        if int(checkpoint.get("iteration", -1)) == int(iteration):
            return dict(checkpoint)
    return None


def derive_target_psnr_map(rows: list[dict[str, Any]], baseline_iteration: int) -> dict[tuple[str, str], float]:
    mapping: dict[tuple[str, str], float] = {}
    for row in rows:
        family_id = str(row["family_id"])
        experiment_name = str(row["experiment_name"])
        scene_id = str(row["scene_id"])
        baseline_name = str(DATASET_FAMILIES[family_id]["baseline_experiment"])
        if experiment_name != baseline_name:
            continue
        checkpoint = checkpoint_by_iteration(row["evaluation"], baseline_iteration)
        if checkpoint is None or checkpoint.get("psnr") is None:
            continue
        mapping[(family_id, scene_id)] = float(checkpoint["psnr"])
    return mapping


def derive_time_to_target_sec(evaluation: dict[str, Any], target_psnr: float | None) -> float | None:
    if target_psnr is None:
        return None
    checkpoints = sorted(
        list(evaluation.get("checkpoint_metrics") or []),
        key=lambda item: float(item.get("estimated_elapsed_sec", 0.0) or 0.0),
    )
    for checkpoint in checkpoints:
        psnr = checkpoint.get("psnr")
        if psnr is None:
            continue
        if float(psnr) >= float(target_psnr):
            elapsed = checkpoint.get("estimated_elapsed_sec")
            return float(elapsed) if elapsed is not None else None
    return None


def load_prior_protection(model_path: Path, iteration: int) -> dict[str, Any] | None:
    protection_path = model_path / "point_cloud" / f"iteration_{iteration}" / "prior_protection.json"
    if not protection_path.exists():
        return None
    return load_json(protection_path)


def checkpoint_csv_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        evaluation = row["evaluation"]
        backend_run = row["backend_run"]
        model_path = resolve_path(backend_run["model_path"])
        for iteration in CHECKPOINT_ITERATIONS:
            checkpoint = checkpoint_by_iteration(evaluation, iteration)
            protection = load_prior_protection(model_path, iteration)
            output.append(
                {
                    "dataset_family": row["family_id"],
                    "experiment_name": row["experiment_name"],
                    "scene_id": row["scene_id"],
                    "protection_mode": mode_label(backend_run),
                    "iteration": iteration,
                    "psnr": checkpoint.get("psnr") if checkpoint else None,
                    "ssim": checkpoint.get("ssim") if checkpoint else None,
                    "lpips": checkpoint.get("lpips") if checkpoint else None,
                    "gaussian_count": checkpoint.get("gaussian_count") if checkpoint else None,
                    "estimated_elapsed_sec": checkpoint.get("estimated_elapsed_sec") if checkpoint else None,
                    "protected_point_count": protection.get("protected_point_count") if protection else None,
                    "total_point_count": protection.get("total_point_count") if protection else None,
                }
            )
    return output


def summary_rows(rows: list[dict[str, Any]], target_psnr_map: dict[tuple[str, str], float]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        evaluation = row["evaluation"]
        backend_run = row["backend_run"]
        model_path = resolve_path(backend_run["model_path"])
        protection_3000 = load_prior_protection(model_path, 3000)
        protection_15000 = load_prior_protection(model_path, 15000)
        target_psnr = target_psnr_map.get((str(row["family_id"]), str(row["scene_id"])))
        output.append(
            {
                "dataset_family": row["family_id"],
                "dataset_label": row["family_label"],
                "experiment_name": row["experiment_name"],
                "scene_id": row["scene_id"],
                "protection_mode": mode_label(backend_run),
                "target_psnr": target_psnr,
                "time_to_target_sec": derive_time_to_target_sec(evaluation, target_psnr),
                "total_time_sec": evaluation.get("total_optimization_time_sec"),
                "psnr_15000": evaluation.get("psnr"),
                "ssim_15000": evaluation.get("ssim"),
                "lpips_15000": evaluation.get("lpips"),
                "gaussians_0": (checkpoint_by_iteration(evaluation, 0) or {}).get("gaussian_count"),
                "gaussians_3000": (checkpoint_by_iteration(evaluation, 3000) or {}).get("gaussian_count"),
                "gaussians_15000": (checkpoint_by_iteration(evaluation, 15000) or {}).get("gaussian_count"),
                "protected_3000": protection_3000.get("protected_point_count") if protection_3000 else None,
                "protected_15000": protection_15000.get("protected_point_count") if protection_15000 else None,
            }
        )
    return output


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def markdown_results_table(rows: list[dict[str, Any]], *, family_id: str) -> str:
    filtered = [row for row in rows if row["dataset_family"] == family_id]
    lines = [
        "| experiment | scene | protection | target_psnr | time_to_target_sec | total_time_sec | psnr@15000 | ssim@15000 | lpips@15000 | gaussians@0 | gaussians@3000 | gaussians@15000 | protected@3000 | protected@15000 |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in filtered:
        lines.append(
            "| {experiment_name} | {scene_id} | {protection_mode} | {target_psnr} | {time_to_target_sec} | {total_time_sec} | {psnr_15000} | {ssim_15000} | {lpips_15000} | {gaussians_0} | {gaussians_3000} | {gaussians_15000} | {protected_3000} | {protected_15000} |".format(
                experiment_name=row["experiment_name"],
                scene_id=row["scene_id"],
                protection_mode=row["protection_mode"],
                target_psnr=f"{float(row['target_psnr']):.6f}" if row["target_psnr"] is not None else "n/a",
                time_to_target_sec=f"{float(row['time_to_target_sec']):.6f}" if row["time_to_target_sec"] is not None else "n/a",
                total_time_sec=row["total_time_sec"],
                psnr_15000=row["psnr_15000"],
                ssim_15000=row["ssim_15000"],
                lpips_15000=row["lpips_15000"],
                gaussians_0=row["gaussians_0"],
                gaussians_3000=row["gaussians_3000"],
                gaussians_15000=row["gaussians_15000"],
                protected_3000=row["protected_3000"] if row["protected_3000"] is not None else "n/a",
                protected_15000=row["protected_15000"] if row["protected_15000"] is not None else "n/a",
            )
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the Replica gaussian-direct Phase 1 protection report.")
    parser.add_argument("--outputs-dir", type=Path, default=Path("outputs/gaussian_direct"))
    parser.add_argument("--scene-id", action="append", dest="scene_ids")
    parser.add_argument("--baseline-iteration", type=int, default=3000)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--summary-csv", type=Path)
    parser.add_argument("--checkpoint-csv", type=Path)
    args = parser.parse_args()

    outputs_dir = resolve_path(args.outputs_dir)
    scene_ids = list(args.scene_ids or ["room_0", "office_0"])
    output_path = (
        resolve_path(args.output)
        if args.output is not None
        else ROOT / "docs" / "experiments" / f"replica_gaussian_direct_protection_phase1_{datetime.now(UTC).strftime('%Y-%m-%d')}.md"
    )
    summary_csv_path = (
        resolve_path(args.summary_csv)
        if args.summary_csv is not None
        else outputs_dir / "reports" / "replica_gaussian_direct_protection_phase1_summary.csv"
    )
    checkpoint_csv_path = (
        resolve_path(args.checkpoint_csv)
        if args.checkpoint_csv is not None
        else outputs_dir / "reports" / "replica_gaussian_direct_protection_phase1_checkpoints.csv"
    )

    rows = collect_rows(outputs_dir, scene_ids)
    target_psnr_map = derive_target_psnr_map(rows, args.baseline_iteration)
    summary = summary_rows(rows, target_psnr_map)
    checkpoints = checkpoint_csv_rows(rows)

    write_csv(
        summary_csv_path,
        [
            "dataset_family",
            "dataset_label",
            "experiment_name",
            "scene_id",
            "protection_mode",
            "target_psnr",
            "time_to_target_sec",
            "total_time_sec",
            "psnr_15000",
            "ssim_15000",
            "lpips_15000",
            "gaussians_0",
            "gaussians_3000",
            "gaussians_15000",
            "protected_3000",
            "protected_15000",
        ],
        summary,
    )
    write_csv(
        checkpoint_csv_path,
        [
            "dataset_family",
            "experiment_name",
            "scene_id",
            "protection_mode",
            "iteration",
            "psnr",
            "ssim",
            "lpips",
            "gaussian_count",
            "estimated_elapsed_sec",
            "protected_point_count",
            "total_point_count",
        ],
        checkpoints,
    )

    lines = [
        "# Replica Gaussian-Direct Phase 1 Protection Sweep",
        "",
        f"- 기준 iteration: baseline `{args.baseline_iteration}` checkpoint PSNR",
        "- 비교 범위: 96-view same-scene exact vs dense 384 same-scene exact",
        "- protection 비교: `none`, `weak(0.02)`, `freeze`",
        "",
        "## 96-view",
        "",
        markdown_results_table(summary, family_id="96_view"),
        "",
        "## Dense 384-view",
        "",
        markdown_results_table(summary, family_id="dense_384"),
        "",
        "## Artifacts",
        "",
        f"- Summary CSV: `{summary_csv_path}`",
        f"- Checkpoint CSV: `{checkpoint_csv_path}`",
        "",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote report to {output_path}")
    print(f"Summary CSV: {summary_csv_path}")
    print(f"Checkpoint CSV: {checkpoint_csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
