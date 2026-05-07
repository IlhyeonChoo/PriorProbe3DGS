#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.runtime_paths import resolve_runtime_path


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def collect_evaluations(outputs_root: Path) -> list[dict[str, Any]]:
    evaluations: list[dict[str, Any]] = []
    for path in sorted((outputs_root / "experiments").glob("**/evaluation.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload.setdefault("experiment_name", path.parent.parent.name if path.parent.parent != outputs_root / "experiments" else path.parent.name)
        payload.setdefault("scene_id", path.parent.name if path.parent.parent != outputs_root / "experiments" else None)
        evaluations.append(payload)
    return evaluations


def _summary_fieldnames() -> list[str]:
    return [
        "experiment_name",
        "backend",
        "initialization",
        "status",
        "dataset_name",
        "scene_id",
        "total_optimization_time_sec",
        "time_to_target_quality_sec",
        "target_psnr",
        "final_iteration",
        "psnr",
        "ssim",
        "lpips",
        "gaussian_count",
        "retrieval_accuracy",
        "prior_object_id",
        "prior_category",
        "prior_count",
        "prior_object_ids",
        "warning_count",
    ]


def _summary_row(evaluation: dict[str, Any]) -> dict[str, Any]:
    return {
        "experiment_name": evaluation.get("experiment_name"),
        "backend": evaluation.get("backend"),
        "initialization": evaluation.get("initialization"),
        "status": evaluation.get("status"),
        "dataset_name": evaluation.get("dataset_name"),
        "scene_id": evaluation.get("scene_id"),
        "total_optimization_time_sec": evaluation.get("total_optimization_time_sec"),
        "time_to_target_quality_sec": evaluation.get("time_to_target_quality_sec"),
        "target_psnr": evaluation.get("target_psnr"),
        "final_iteration": evaluation.get("final_iteration"),
        "psnr": evaluation.get("psnr"),
        "ssim": evaluation.get("ssim"),
        "lpips": evaluation.get("lpips"),
        "gaussian_count": evaluation.get("gaussian_count"),
        "retrieval_accuracy": evaluation.get("retrieval_accuracy"),
        "prior_object_id": evaluation.get("prior_object_id"),
        "prior_category": evaluation.get("prior_category"),
        "prior_count": evaluation.get("prior_count"),
        "prior_object_ids": ",".join(evaluation.get("prior_object_ids", [])),
        "warning_count": len(evaluation.get("warnings", [])),
    }


def flatten_checkpoint_rows(evaluations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for evaluation in evaluations:
        for checkpoint in evaluation.get("checkpoint_metrics", []):
            rows.append(
                {
                    "experiment_name": evaluation.get("experiment_name"),
                    "scene_id": evaluation.get("scene_id"),
                    "initialization": evaluation.get("initialization"),
                    "prior_object_id": evaluation.get("prior_object_id"),
                    "prior_count": evaluation.get("prior_count"),
                    "iteration": checkpoint.get("iteration"),
                    "method": checkpoint.get("method"),
                    "psnr": checkpoint.get("psnr"),
                    "ssim": checkpoint.get("ssim"),
                    "lpips": checkpoint.get("lpips"),
                    "gaussian_count": checkpoint.get("gaussian_count"),
                    "estimated_elapsed_sec": checkpoint.get("estimated_elapsed_sec"),
                }
            )
    return rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def to_markdown_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| experiment | scene | init | total_time_sec | time_to_target_sec | final_iter | psnr | ssim | lpips | gaussians | prior |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {experiment_name} | {scene_id} | {initialization} | {total_optimization_time_sec} | {time_to_target_quality_sec} | {final_iteration} | {psnr} | {ssim} | {lpips} | {gaussian_count} | {prior_object_id} |".format(
                **row
            )
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    default_outputs_dir = resolve_runtime_path(ROOT, "outputs_dir", fallback="outputs")
    default_reports_dir = default_outputs_dir / "reports"

    parser = argparse.ArgumentParser(description="Export experiment results to Markdown and CSV tables.")
    parser.add_argument("--outputs-dir", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--summary-csv", type=Path)
    parser.add_argument("--checkpoint-csv", type=Path)
    args = parser.parse_args()

    outputs_dir = _resolve(args.outputs_dir) if args.outputs_dir is not None else default_outputs_dir
    markdown_output = (
        _resolve(args.markdown_output) if args.markdown_output is not None else default_reports_dir / "summary.md"
    )
    summary_csv = _resolve(args.summary_csv) if args.summary_csv is not None else default_reports_dir / "summary.csv"
    checkpoint_csv = (
        _resolve(args.checkpoint_csv) if args.checkpoint_csv is not None else default_reports_dir / "checkpoints.csv"
    )

    evaluations = collect_evaluations(outputs_dir)
    summary_rows = [_summary_row(evaluation) for evaluation in evaluations]
    checkpoint_rows = flatten_checkpoint_rows(evaluations)

    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(to_markdown_table(summary_rows), encoding="utf-8")
    write_csv(summary_csv, _summary_fieldnames(), summary_rows)
    if checkpoint_rows:
        write_csv(
            checkpoint_csv,
            [
                "experiment_name",
                "scene_id",
                "initialization",
                "prior_object_id",
                "prior_count",
                "iteration",
                "method",
                "psnr",
                "ssim",
                "lpips",
                "gaussian_count",
                "estimated_elapsed_sec",
            ],
            checkpoint_rows,
        )
    else:
        checkpoint_csv.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_csv.write_text("", encoding="utf-8")

    print(f"Exported {len(summary_rows)} evaluations to {markdown_output}")
    print(f"Summary CSV: {summary_csv}")
    print(f"Checkpoint CSV: {checkpoint_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
