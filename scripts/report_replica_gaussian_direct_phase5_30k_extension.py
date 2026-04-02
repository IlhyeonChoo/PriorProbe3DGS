#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
import sys

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.evaluation.metrics import summarize_backend_run
from priorprobe.experiment_storage import resolve_experiment_storage_dir
from priorprobe.runtime_paths import build_dated_doc_path, build_dated_report_csv_path


EXPERIMENTS = [
    {"label": "baseline_30000", "group": "extension", "experiment_name": "gaussian_direct_surface_rgb_baseline_30000"},
    {"label": "prior_100k_30000", "group": "extension", "experiment_name": "gaussian_direct_surface_rgb_prior_100k_30000"},
    {"label": "prior_full_30000", "group": "extension", "experiment_name": "gaussian_direct_surface_rgb_prior_full_30000"},
    {"label": "prior_25k_30000", "group": "extension", "experiment_name": "gaussian_direct_surface_rgb_prior_25k_30000"},
    {
        "label": "prior_25k_full_none_30000",
        "group": "extension",
        "experiment_name": "gaussian_direct_surface_rgb_prior_25k_full_none_30000",
    },
    {"label": "prior_50k_30000", "group": "extension", "experiment_name": "gaussian_direct_surface_rgb_prior_50k_30000"},
    {"label": "prior_75k_30000", "group": "extension", "experiment_name": "gaussian_direct_surface_rgb_prior_75k_30000"},
    {
        "label": "prior_100k_geo_30000",
        "group": "extension",
        "experiment_name": "gaussian_direct_surface_rgb_prior_100k_geo_30000",
    },
    {
        "label": "prior_50k_geo_30000",
        "group": "extension",
        "experiment_name": "gaussian_direct_surface_rgb_prior_50k_geo_30000",
    },
]

SCENES = ("room_0", "office_0")
FINAL_ITERATION = 30000


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def checkpoint_by_iteration(checkpoints: list[dict[str, Any]], iteration: int) -> dict[str, Any] | None:
    for checkpoint in checkpoints:
        if int(checkpoint.get("iteration", -1)) == int(iteration):
            return dict(checkpoint)
    return None


def derive_time_to_target_sec(checkpoints: list[dict[str, Any]], target_psnr: float | None) -> float | None:
    if target_psnr is None:
        return None
    ordered = sorted(checkpoints, key=lambda item: float(item.get("estimated_elapsed_sec", 0.0) or 0.0))
    for checkpoint in ordered:
        psnr = checkpoint.get("psnr")
        if psnr is not None and float(psnr) >= float(target_psnr):
            elapsed = checkpoint.get("estimated_elapsed_sec")
            return float(elapsed) if elapsed is not None else None
    return None


def load_prior_protection(model_path: Path, iteration: int) -> dict[str, Any] | None:
    path = model_path / "point_cloud" / f"iteration_{iteration}" / "prior_protection.json"
    if not path.exists():
        return None
    return load_json(path)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def fmt_float(value: Any, digits: int = 6) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def fmt_int(value: Any) -> str:
    if value is None:
        return "n/a"
    return str(int(value))


def protection_group_index(payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if payload is None:
        return {}
    groups = payload.get("group_summaries") or []
    index: dict[str, dict[str, Any]] = {}
    for item in groups:
        prior_object_id = item.get("prior_object_id")
        if prior_object_id is None:
            continue
        index[str(prior_object_id)] = dict(item)
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description="Report Phase 5.3 30K extension runs.")
    parser.add_argument("--outputs-dir", type=Path, default=ROOT / "outputs" / "gaussian_direct")
    args = parser.parse_args()
    report_date = date(2026, 3, 24)

    summary_rows: list[dict[str, Any]] = []
    checkpoint_rows: list[dict[str, Any]] = []
    object_rows: list[dict[str, Any]] = []
    baseline_target_psnr: dict[str, float] = {}
    baseline_final_psnr: dict[str, float] = {}

    for experiment in EXPERIMENTS:
        for scene_id in SCENES:
            experiment_name = str(experiment["experiment_name"])
            experiment_dir = resolve_experiment_storage_dir(args.outputs_dir, "experiments", experiment_name) / scene_id
            backend_run_path = experiment_dir / "backend_run.json"
            if not backend_run_path.exists():
                continue

            backend_run = load_json(backend_run_path)
            evaluation = summarize_backend_run(backend_run_path).to_dict()
            (experiment_dir / "evaluation.json").write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
            checkpoints = list(evaluation.get("checkpoint_metrics") or [])

            if experiment["label"] == "baseline_30000":
                baseline_3000 = checkpoint_by_iteration(checkpoints, 3000)
                baseline_final = checkpoint_by_iteration(checkpoints, FINAL_ITERATION)
                if baseline_3000 is not None and baseline_3000.get("psnr") is not None:
                    baseline_target_psnr[scene_id] = float(baseline_3000["psnr"])
                if baseline_final is not None and baseline_final.get("psnr") is not None:
                    baseline_final_psnr[scene_id] = float(baseline_final["psnr"])

            model_path = Path(str(backend_run["model_path"]))
            prior_metadata_path = model_path / "prior_init" / "metadata.json"
            prior_metadata = load_json(prior_metadata_path) if prior_metadata_path.exists() else {}
            selected_priors = list(prior_metadata.get("selected_priors") or backend_run.get("selected_priors") or [])
            protection_3000 = load_prior_protection(model_path, 3000)
            protection_final = load_prior_protection(model_path, FINAL_ITERATION)
            protection_3000_index = protection_group_index(protection_3000)
            protection_final_index = protection_group_index(protection_final)

            prior_original_total = sum(int(item.get("original_point_count", 0) or 0) for item in selected_priors)
            prior_inserted_total = sum(
                int(item.get("inserted_point_count", item.get("kept_point_count", 0)) or 0) for item in selected_priors
            )
            prior_survived_3000 = sum(
                int(item.get("survived_point_count", 0) or 0) for item in protection_3000_index.values()
            )
            prior_survived_final = sum(
                int(item.get("survived_point_count", 0) or 0) for item in protection_final_index.values()
            )

            iter_0 = checkpoint_by_iteration(checkpoints, 0) or {}
            iter_3000 = checkpoint_by_iteration(checkpoints, 3000) or {}
            iter_15000 = checkpoint_by_iteration(checkpoints, 15000) or {}
            iter_final = checkpoint_by_iteration(checkpoints, FINAL_ITERATION) or {}

            summary_rows.append(
                {
                    "scene_id": scene_id,
                    "group": experiment["group"],
                    "label": experiment["label"],
                    "experiment_name": experiment_name,
                    "target_psnr": baseline_target_psnr.get(scene_id),
                    "time_to_target_sec": derive_time_to_target_sec(checkpoints, baseline_target_psnr.get(scene_id)),
                    "total_time_sec": evaluation.get("total_optimization_time_sec"),
                    "iter_0_psnr": iter_0.get("psnr"),
                    "iter_3000_psnr": iter_3000.get("psnr"),
                    "iter_15000_psnr": iter_15000.get("psnr"),
                    "iter_30000_psnr": iter_final.get("psnr"),
                    "iter_30000_ssim": iter_final.get("ssim"),
                    "iter_30000_lpips": iter_final.get("lpips"),
                    "iter_30000_gaussians": iter_final.get("gaussian_count"),
                    "delta_final_psnr_vs_baseline": (
                        float(iter_final.get("psnr")) - baseline_final_psnr.get(scene_id, float("nan"))
                        if experiment["label"] != "baseline_30000"
                        and iter_final.get("psnr") is not None
                        and scene_id in baseline_final_psnr
                        else None
                    ),
                    "prior_original_total": prior_original_total,
                    "prior_inserted_total": prior_inserted_total,
                    "prior_survived_3000": prior_survived_3000 if selected_priors else None,
                    "prior_survived_30000": prior_survived_final if selected_priors else None,
                    "prior_survival_ratio_3000": (
                        float(prior_survived_3000 / prior_inserted_total) if prior_inserted_total > 0 else None
                    ),
                    "prior_survival_ratio_30000": (
                        float(prior_survived_final / prior_inserted_total) if prior_inserted_total > 0 else None
                    ),
                }
            )

            for checkpoint in checkpoints:
                checkpoint_rows.append(
                    {
                        "scene_id": scene_id,
                        "group": experiment["group"],
                        "label": experiment["label"],
                        "experiment_name": experiment_name,
                        "iteration": checkpoint.get("iteration"),
                        "method": checkpoint.get("method"),
                        "psnr": checkpoint.get("psnr"),
                        "ssim": checkpoint.get("ssim"),
                        "lpips": checkpoint.get("lpips"),
                        "gaussian_count": checkpoint.get("gaussian_count"),
                        "estimated_elapsed_sec": checkpoint.get("estimated_elapsed_sec"),
                    }
                )

            for item in selected_priors:
                prior_object_id = str(item.get("prior_object_id"))
                g3000 = protection_3000_index.get(prior_object_id, {})
                gfinal = protection_final_index.get(prior_object_id, {})
                inserted_count = int(item.get("inserted_point_count", item.get("kept_point_count", 0)) or 0)
                object_rows.append(
                    {
                        "scene_id": scene_id,
                        "label": experiment["label"],
                        "experiment_name": experiment_name,
                        "target_object_id": item.get("target_object_id"),
                        "target_category": item.get("target_category"),
                        "prior_object_id": prior_object_id,
                        "asset_format": item.get("asset_format"),
                        "original_count": item.get("original_point_count"),
                        "inserted_count": inserted_count,
                        "inserted_ratio": (
                            float(inserted_count / int(item.get("original_point_count", 0)))
                            if int(item.get("original_point_count", 0) or 0) > 0
                            else None
                        ),
                        "survived_3000": g3000.get("survived_point_count"),
                        "survival_ratio_3000": g3000.get("survival_ratio"),
                        "survived_30000": gfinal.get("survived_point_count"),
                        "survival_ratio_30000": gfinal.get("survival_ratio"),
                    }
                )

    reports_dir = args.outputs_dir / "reports"
    summary_csv = build_dated_report_csv_path(
        reports_dir.parent,
        slug="phase5_30k_extension",
        kind="summary",
        when=report_date,
    )
    checkpoints_csv = build_dated_report_csv_path(
        reports_dir.parent,
        slug="phase5_30k_extension",
        kind="checkpoints",
        when=report_date,
    )
    object_csv = build_dated_report_csv_path(
        reports_dir.parent,
        slug="phase5_30k_extension",
        kind="object_survival",
        when=report_date,
    )
    if summary_rows:
        write_csv(summary_csv, list(summary_rows[0].keys()), summary_rows)
    if checkpoint_rows:
        write_csv(checkpoints_csv, list(checkpoint_rows[0].keys()), checkpoint_rows)
    if object_rows:
        write_csv(object_csv, list(object_rows[0].keys()), object_rows)

    report_path = build_dated_doc_path(ROOT, doc_dir="experiment_results", slug="phase5_30k_extension", when=report_date)
    lines = [
        "# Replica Gaussian-Direct Phase 5.3 30K Extension",
        "",
        "- Date: 2026-03-24",
        "- Dataset family: `surface_rgb_roomwide_v2_384`",
        "- Scenes: `room_0`, `office_0`",
        "- Protection: `none`",
        "- 비교 기준: absolute PSNR/SSIM/LPIPS와 scene별 baseline_30000 대비 delta",
        "",
        "## Summary",
        "",
        "| scene | label | iter_0_psnr | iter_3000_psnr | iter_15000_psnr | final_psnr | final_delta_vs_baseline | total_time_sec | ttt_sec | prior_inserted_total | survived@30000 | survival@30000 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["scene_id"]),
                    str(row["label"]),
                    fmt_float(row["iter_0_psnr"], 4),
                    fmt_float(row["iter_3000_psnr"], 4),
                    fmt_float(row["iter_15000_psnr"], 4),
                    fmt_float(row["iter_30000_psnr"], 4),
                    fmt_float(row["delta_final_psnr_vs_baseline"], 4),
                    fmt_float(row["total_time_sec"], 2),
                    fmt_float(row["time_to_target_sec"], 2),
                    fmt_int(row["prior_inserted_total"]),
                    fmt_int(row["prior_survived_30000"]),
                    fmt_float(row["prior_survival_ratio_30000"], 4),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Object Survival",
            "",
            "| scene | label | target_object_id | category | prior_object_id | original | inserted | insert_ratio | survived@3000 | ratio@3000 | survived@30000 | ratio@30000 |",
            "|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in object_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["scene_id"]),
                    str(row["label"]),
                    fmt_int(row["target_object_id"]),
                    str(row["target_category"]),
                    str(row["prior_object_id"]),
                    fmt_int(row["original_count"]),
                    fmt_int(row["inserted_count"]),
                    fmt_float(row["inserted_ratio"], 4),
                    fmt_int(row["survived_3000"]),
                    fmt_float(row["survival_ratio_3000"], 4),
                    fmt_int(row["survived_30000"]),
                    fmt_float(row["survival_ratio_30000"], 4),
                ]
            )
            + " |"
        )
    lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {summary_csv}")
    print(f"Wrote {checkpoints_csv}")
    print(f"Wrote {object_csv}")
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
