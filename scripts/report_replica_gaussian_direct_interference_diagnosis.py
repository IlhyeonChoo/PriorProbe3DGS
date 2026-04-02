#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
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


EXPERIMENTS = {
    "baseline": {
        "label": "baseline",
        "experiment_name": "gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_v2_384_15000",
    },
    "prior_none": {
        "label": "prior none",
        "experiment_name": "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_15000",
    },
    "prior_weak": {
        "label": "prior weak(0.02)",
        "experiment_name": "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_weak_15000",
    },
    "sh_zero": {
        "label": "C sh_zero",
        "experiment_name": "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_sh_zero_15000",
    },
    "sh_zero_weak": {
        "label": "C sh_zero weak(0.02)",
        "experiment_name": "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_sh_zero_weak_15000",
    },
    "replace_region": {
        "label": "B replace_region",
        "experiment_name": "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_replace_region_15000",
    },
    "replace_region_weak": {
        "label": "B replace_region weak(0.02)",
        "experiment_name": "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_replace_region_weak_15000",
    },
    "prior_25k": {
        "label": "A prior_25k",
        "experiment_name": "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_prior_25k_15000",
    },
    "prior_50k": {
        "label": "A prior_50k",
        "experiment_name": "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_prior_50k_15000",
    },
    "prior_25k_weak": {
        "label": "A prior_25k weak(0.02)",
        "experiment_name": "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_prior_25k_weak_15000",
    },
    "prior_50k_weak": {
        "label": "A prior_50k weak(0.02)",
        "experiment_name": "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_prior_50k_weak_15000",
    },
}


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
        if psnr is None:
            continue
        if float(psnr) >= float(target_psnr):
            elapsed = checkpoint.get("estimated_elapsed_sec")
            return float(elapsed) if elapsed is not None else None
    return None


def load_prior_protection(model_path: Path, iteration: int) -> dict[str, Any] | None:
    path = model_path / "point_cloud" / f"iteration_{iteration}" / "prior_protection.json"
    if not path.exists():
        return None
    return load_json(path)


def mode_label(backend_run: dict[str, Any]) -> str:
    protection = dict(backend_run.get("prior_protection") or {})
    mode = str(protection.get("mode") or "none")
    if mode == "weak":
        return f"weak({float(protection.get('lr_scale', 0.0)):.2f})"
    return mode


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Report Gaussian-direct interference diagnosis runs.")
    parser.add_argument("--outputs-dir", type=Path, default=ROOT / "outputs" / "gaussian_direct")
    parser.add_argument("--scene-id", type=str, default="room_0")
    args = parser.parse_args()
    report_date = datetime.now(UTC).date()
    report_slug = f"interference_diagnosis_{args.scene_id}"

    rows: list[dict[str, Any]] = []
    baseline_target_psnr: float | None = None

    for family_id, spec in EXPERIMENTS.items():
        experiment_name = str(spec["experiment_name"])
        experiment_dir = resolve_experiment_storage_dir(args.outputs_dir, "experiments", experiment_name) / args.scene_id
        backend_run_path = experiment_dir / "backend_run.json"
        if not backend_run_path.exists():
            continue
        backend_run = load_json(backend_run_path)
        summary = summarize_backend_run(backend_run_path)
        evaluation = summary.to_dict()
        evaluation_path = experiment_dir / "evaluation.json"
        evaluation_path.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")

        checkpoints = list(evaluation.get("checkpoint_metrics") or [])
        if family_id == "baseline":
            baseline_3000 = checkpoint_by_iteration(checkpoints, 3000)
            if baseline_3000 is not None and baseline_3000.get("psnr") is not None:
                baseline_target_psnr = float(baseline_3000["psnr"])

        model_path = Path(str(backend_run["model_path"]))
        prior_init_metadata = load_json(model_path / "prior_init" / "metadata.json") if (model_path / "prior_init" / "metadata.json").exists() else {}
        selected_priors = list(prior_init_metadata.get("selected_priors") or backend_run.get("selected_priors") or [])
        protection_3000 = load_prior_protection(model_path, 3000)
        protection_15000 = load_prior_protection(model_path, 15000)
        insertion = dict(backend_run.get("prior_insertion") or {})
        prior_original_total = sum(int(item.get("original_point_count", 0) or 0) for item in selected_priors)
        prior_kept_total = sum(int(item.get("kept_point_count", 0) or 0) for item in selected_priors)

        row = {
            "family_id": family_id,
            "label": spec["label"],
            "experiment_name": experiment_name,
            "scene_id": args.scene_id,
            "protection_mode": mode_label(backend_run),
            "prior_sh_reset_mode": insertion.get("sh_reset_mode", prior_init_metadata.get("prior_sh_reset_mode")),
            "prior_target_total_gaussians": insertion.get(
                "target_total_gaussians",
                prior_init_metadata.get("prior_target_total_gaussians"),
            ),
            "sfm_region_replacement_mode": insertion.get(
                "sfm_region_replacement_mode",
                prior_init_metadata.get("sfm_region_replacement_mode"),
            ),
            "sfm_removed_point_count": insertion.get("sfm_removed_point_count", prior_init_metadata.get("sfm_removed_point_count")),
            "sfm_removed_point_ratio": insertion.get("sfm_removed_point_ratio", prior_init_metadata.get("sfm_removed_point_ratio")),
            "prior_original_total": prior_original_total,
            "prior_kept_total": prior_kept_total,
            "total_time_sec": evaluation.get("total_optimization_time_sec"),
            "target_psnr": None,
            "time_to_target_sec": None,
            "iter_0_psnr": (checkpoint_by_iteration(checkpoints, 0) or {}).get("psnr"),
            "iter_0_ssim": (checkpoint_by_iteration(checkpoints, 0) or {}).get("ssim"),
            "iter_0_lpips": (checkpoint_by_iteration(checkpoints, 0) or {}).get("lpips"),
            "iter_0_gaussians": (checkpoint_by_iteration(checkpoints, 0) or {}).get("gaussian_count"),
            "iter_3000_psnr": (checkpoint_by_iteration(checkpoints, 3000) or {}).get("psnr"),
            "iter_3000_ssim": (checkpoint_by_iteration(checkpoints, 3000) or {}).get("ssim"),
            "iter_3000_lpips": (checkpoint_by_iteration(checkpoints, 3000) or {}).get("lpips"),
            "iter_3000_gaussians": (checkpoint_by_iteration(checkpoints, 3000) or {}).get("gaussian_count"),
            "iter_15000_psnr": (checkpoint_by_iteration(checkpoints, 15000) or {}).get("psnr"),
            "iter_15000_ssim": (checkpoint_by_iteration(checkpoints, 15000) or {}).get("ssim"),
            "iter_15000_lpips": (checkpoint_by_iteration(checkpoints, 15000) or {}).get("lpips"),
            "iter_15000_gaussians": (checkpoint_by_iteration(checkpoints, 15000) or {}).get("gaussian_count"),
            "protected_3000": protection_3000.get("protected_point_count") if protection_3000 else None,
            "protected_15000": protection_15000.get("protected_point_count") if protection_15000 else None,
            "checkpoints": checkpoints,
        }
        rows.append(row)

    for row in rows:
        row["target_psnr"] = baseline_target_psnr
        row["time_to_target_sec"] = derive_time_to_target_sec(row["checkpoints"], baseline_target_psnr)

    summary_rows = [{key: value for key, value in row.items() if key != "checkpoints"} for row in rows]
    checkpoint_rows: list[dict[str, Any]] = []
    for row in rows:
        for checkpoint in row["checkpoints"]:
            checkpoint_rows.append(
                {
                    "experiment_name": row["experiment_name"],
                    "label": row["label"],
                    "scene_id": row["scene_id"],
                    "protection_mode": row["protection_mode"],
                    "prior_sh_reset_mode": row["prior_sh_reset_mode"],
                    "prior_target_total_gaussians": row["prior_target_total_gaussians"],
                    "sfm_region_replacement_mode": row["sfm_region_replacement_mode"],
                    "iteration": checkpoint.get("iteration"),
                    "method": checkpoint.get("method"),
                    "psnr": checkpoint.get("psnr"),
                    "ssim": checkpoint.get("ssim"),
                    "lpips": checkpoint.get("lpips"),
                    "gaussian_count": checkpoint.get("gaussian_count"),
                    "estimated_elapsed_sec": checkpoint.get("estimated_elapsed_sec"),
                }
            )

    summary_csv = build_dated_report_csv_path(args.outputs_dir, slug=report_slug, kind="summary", when=report_date)
    checkpoints_csv = build_dated_report_csv_path(
        args.outputs_dir,
        slug=report_slug,
        kind="checkpoints",
        when=report_date,
    )
    write_csv(
        summary_csv,
        [
            "family_id",
            "label",
            "experiment_name",
            "scene_id",
            "protection_mode",
            "prior_sh_reset_mode",
            "prior_target_total_gaussians",
            "sfm_region_replacement_mode",
            "sfm_removed_point_count",
            "sfm_removed_point_ratio",
            "prior_original_total",
            "prior_kept_total",
            "target_psnr",
            "time_to_target_sec",
            "total_time_sec",
            "iter_0_psnr",
            "iter_0_ssim",
            "iter_0_lpips",
            "iter_0_gaussians",
            "iter_3000_psnr",
            "iter_3000_ssim",
            "iter_3000_lpips",
            "iter_3000_gaussians",
            "iter_15000_psnr",
            "iter_15000_ssim",
            "iter_15000_lpips",
            "iter_15000_gaussians",
            "protected_3000",
            "protected_15000",
        ],
        summary_rows,
    )
    write_csv(
        checkpoints_csv,
        [
            "experiment_name",
            "label",
            "scene_id",
            "protection_mode",
            "prior_sh_reset_mode",
            "prior_target_total_gaussians",
            "sfm_region_replacement_mode",
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

    by_id = {row["family_id"]: row for row in summary_rows}
    exact_none = by_id.get("prior_none")
    lines = [
        "# Replica Gaussian-Direct Interference Diagnosis",
        "",
        f"- Date: {report_date.isoformat()}",
        f"- Scene: `{args.scene_id}`",
        "- Dataset family: `roomwide_v2_384`",
        "- 기준 비교: baseline / prior none / prior weak(0.02)",
        "- 주 지표: `iter_0`, `iter_3000`, `iter_15000` PSNR/SSIM/LPIPS와 gaussian count",
        "- 참고: `time_to_target_sec`는 baseline 3000-iter PSNR 기준으로 계산했지만 결론의 주 근거로 쓰지 않음",
        "",
        "## Summary",
        "",
        "| label | protection | sh_reset | prior_budget | sfm_replace | sfm_removed | iter_0_psnr | iter_3000_psnr | iter_15000_psnr | gaussians@0 | gaussians@3000 | gaussians@15000 |",
        "|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            "| {label} | {protection_mode} | {prior_sh_reset_mode} | {prior_target_total_gaussians} | {sfm_region_replacement_mode} | {sfm_removed_point_count} | {iter_0_psnr} | {iter_3000_psnr} | {iter_15000_psnr} | {iter_0_gaussians} | {iter_3000_gaussians} | {iter_15000_gaussians} |".format(
                **{
                    **row,
                    "sfm_removed_point_count": row["sfm_removed_point_count"] if row["sfm_removed_point_count"] is not None else "n/a",
                }
            )
        )

    lines.extend(
        [
            "",
            "## Insertion Diagnostics",
            "",
            "| label | prior_original_total | prior_kept_total | protected@3000 | protected@15000 | sfm_removed_ratio | total_time_sec | time_to_target_sec |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary_rows:
        lines.append(
            "| {label} | {prior_original_total} | {prior_kept_total} | {protected_3000} | {protected_15000} | {sfm_removed_point_ratio} | {total_time_sec} | {time_to_target_sec} |".format(
                **{
                    **row,
                    "protected_3000": row["protected_3000"] if row["protected_3000"] is not None else "n/a",
                    "protected_15000": row["protected_15000"] if row["protected_15000"] is not None else "n/a",
                    "sfm_removed_point_ratio": (
                        f"{float(row['sfm_removed_point_ratio']):.6f}"
                        if row["sfm_removed_point_ratio"] is not None
                        else "n/a"
                    ),
                    "time_to_target_sec": (
                        f"{float(row['time_to_target_sec']):.6f}"
                        if row["time_to_target_sec"] is not None
                        else "n/a"
                    ),
                }
            )
        )

    if exact_none is not None:
        lines.extend(
            [
                "",
                "## Interpretation Hints",
                "",
                f"- `prior none` 기준 iter_0 PSNR: `{exact_none['iter_0_psnr']}`",
                f"- `C sh_zero` 개선폭: `{(float(by_id['sh_zero']['iter_0_psnr']) - float(exact_none['iter_0_psnr'])) if by_id.get('sh_zero') and exact_none.get('iter_0_psnr') is not None else 'n/a'}` dB",
                f"- `B replace_region` 개선폭: `{(float(by_id['replace_region']['iter_0_psnr']) - float(exact_none['iter_0_psnr'])) if by_id.get('replace_region') and exact_none.get('iter_0_psnr') is not None else 'n/a'}` dB",
                f"- `A prior_25k` 개선폭: `{(float(by_id['prior_25k']['iter_0_psnr']) - float(exact_none['iter_0_psnr'])) if by_id.get('prior_25k') and exact_none.get('iter_0_psnr') is not None else 'n/a'}` dB",
                f"- `A prior_50k` 개선폭: `{(float(by_id['prior_50k']['iter_0_psnr']) - float(exact_none['iter_0_psnr'])) if by_id.get('prior_50k') and exact_none.get('iter_0_psnr') is not None else 'n/a'}` dB",
            ]
        )

    report_path = build_dated_doc_path(ROOT, doc_dir="experiment_results", slug=report_slug, when=report_date)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved report to {report_path}")
    print(f"Saved summary CSV to {summary_csv}")
    print(f"Saved checkpoint CSV to {checkpoints_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
