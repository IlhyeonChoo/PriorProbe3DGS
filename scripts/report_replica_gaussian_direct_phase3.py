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
        "group": "reference",
        "label": "baseline",
        "experiment_name": "gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_v2_384_15000",
    },
    "prior_100k": {
        "group": "reference",
        "label": "prior 100K current",
        "experiment_name": "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_15000",
    },
    "prior_25k_current": {
        "group": "reference",
        "label": "A 25K current",
        "experiment_name": "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_prior_25k_15000",
    },
    "prior_25k_lr01": {
        "group": "phase3",
        "label": "lr_0.1",
        "experiment_name": "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_prior_25k_lr01_15000",
    },
    "prior_25k_lr10": {
        "group": "phase3",
        "label": "lr_1.0",
        "experiment_name": "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_prior_25k_lr10_15000",
    },
    "prior_25k_full_none": {
        "group": "phase3",
        "label": "full_none",
        "experiment_name": "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_prior_25k_full_none_15000",
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


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def fmt_float(value: Any, *, digits: int = 6) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def fmt_int(value: Any) -> str:
    if value is None:
        return "n/a"
    return str(int(value))


def fmt_delta(candidate: dict[str, Any] | None, reference: dict[str, Any] | None, key: str) -> str:
    if candidate is None or reference is None:
        return "n/a"
    lhs = candidate.get(key)
    rhs = reference.get(key)
    if lhs is None or rhs is None:
        return "n/a"
    return f"{float(lhs) - float(rhs):+.6f}"


def final_psnr_relation(candidate: float | None, reference: float | None) -> str:
    if candidate is None or reference is None:
        return "insufficient data"
    delta = float(candidate) - float(reference)
    if delta > 0.01:
        return "higher"
    if delta < -0.01:
        return "lower"
    return "similar"


def main() -> int:
    parser = argparse.ArgumentParser(description="Report Gaussian-direct Phase 3 runs.")
    parser.add_argument("--outputs-dir", type=Path, default=ROOT / "outputs" / "gaussian_direct")
    parser.add_argument("--scene-id", type=str, default="room_0")
    args = parser.parse_args()
    report_date = datetime.now(UTC).date()
    report_slug = f"phase3_{args.scene_id}"

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
        (experiment_dir / "evaluation.json").write_text(json.dumps(evaluation, indent=2), encoding="utf-8")

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
        protection_iter0 = load_prior_protection(model_path, 0)

        prior_original_total = sum(int(item.get("original_point_count", 0) or 0) for item in selected_priors)
        prior_kept_total = sum(int(item.get("kept_point_count", 0) or 0) for item in selected_priors)
        prior_3000 = protection_3000.get("protected_point_count") if protection_3000 else None
        prior_15000 = protection_15000.get("protected_point_count") if protection_15000 else None
        prior_0 = protection_iter0.get("protected_point_count") if protection_iter0 else None
        prior_survival_3000 = (float(prior_3000) / float(prior_kept_total)) if prior_3000 is not None and prior_kept_total else None
        prior_survival_15000 = (float(prior_15000) / float(prior_kept_total)) if prior_15000 is not None and prior_kept_total else None
        prior_densified_3000 = (int(prior_3000) - int(prior_kept_total)) if prior_3000 is not None and prior_kept_total else None
        prior_densified_15000 = (int(prior_15000) - int(prior_kept_total)) if prior_15000 is not None and prior_kept_total else None
        protection = dict(backend_run.get("prior_protection") or {})

        row = {
            "family_id": family_id,
            "group": spec["group"],
            "label": spec["label"],
            "experiment_name": experiment_name,
            "scene_id": args.scene_id,
            "prior_lr_scale": protection.get("lr_scale"),
            "protect_from_prune": protection.get("protect_from_prune"),
            "protect_from_densify": protection.get("protect_from_densify"),
            "prior_original_total": prior_original_total,
            "prior_kept_total": prior_kept_total,
            "prior_0": prior_0,
            "prior_3000": prior_3000,
            "prior_15000": prior_15000,
            "prior_survival_3000": prior_survival_3000,
            "prior_survival_15000": prior_survival_15000,
            "prior_densified_3000": prior_densified_3000,
            "prior_densified_15000": prior_densified_15000,
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
                    "group": row["group"],
                    "scene_id": row["scene_id"],
                    "prior_lr_scale": row["prior_lr_scale"],
                    "protect_from_prune": row["protect_from_prune"],
                    "protect_from_densify": row["protect_from_densify"],
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
            "group",
            "label",
            "experiment_name",
            "scene_id",
            "prior_lr_scale",
            "protect_from_prune",
            "protect_from_densify",
            "prior_original_total",
            "prior_kept_total",
            "prior_0",
            "prior_3000",
            "prior_15000",
            "prior_survival_3000",
            "prior_survival_15000",
            "prior_densified_3000",
            "prior_densified_15000",
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
        ],
        summary_rows,
    )
    write_csv(
        checkpoints_csv,
        [
            "experiment_name",
            "label",
            "group",
            "scene_id",
            "prior_lr_scale",
            "protect_from_prune",
            "protect_from_densify",
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

    row_map = {row["family_id"]: row for row in summary_rows}
    reference = row_map.get("prior_25k_current")
    baseline = row_map.get("baseline")
    lr01 = row_map.get("prior_25k_lr01")
    lr10 = row_map.get("prior_25k_lr10")
    full_none = row_map.get("prior_25k_full_none")

    md_lines = [
        "# Replica Gaussian-Direct Phase 3",
        "",
        f"- Date: {report_date.isoformat()}",
        f"- Scene: `{args.scene_id}`",
        "- Dataset family: `roomwide_v2_384`",
        "- 비교 기준: baseline / prior 100K current / A 25K current / Phase 3 세 조건",
        "- 주 지표: `iter_0`, `iter_3000`, `iter_15000` PSNR/SSIM/LPIPS, prior 생존량, total gaussian count",
        "- 참고: `time_to_target_sec`는 표에는 남기되 판단의 주 근거로 쓰지 않음",
        "",
        "## Summary",
        "",
        "| label | group | lr_scale | prune_protect | densify_protect | iter_0_psnr | iter_3000_psnr | iter_15000_psnr | gaussians@0 | gaussians@3000 | gaussians@15000 | prior@0 | prior@3000 | prior@15000 |",
        "|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        md_lines.append(
            f"| {row['label']} | {row['group']} | {fmt_float(row['prior_lr_scale'], digits=2)} | "
            f"{row['protect_from_prune']} | {row['protect_from_densify']} | "
            f"{fmt_float(row['iter_0_psnr'])} | {fmt_float(row['iter_3000_psnr'])} | {fmt_float(row['iter_15000_psnr'])} | "
            f"{fmt_int(row['iter_0_gaussians'])} | {fmt_int(row['iter_3000_gaussians'])} | {fmt_int(row['iter_15000_gaussians'])} | "
            f"{fmt_int(row['prior_0'])} | {fmt_int(row['prior_3000'])} | {fmt_int(row['prior_15000'])} |"
        )

    md_lines.extend(
        [
            "",
            "## Phase 3 Focus",
            "",
            "| label | final vs A25K | iter_3000 vs A25K | final vs baseline | prior_survival@3000 | prior_survival@15000 | prior_densified@3000 | prior_densified@15000 | total_time_sec | time_to_target_sec |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for key in ("prior_25k_lr01", "prior_25k_lr10", "prior_25k_full_none"):
        row = row_map.get(key)
        if row is None:
            continue
        md_lines.append(
            f"| {row['label']} | {fmt_delta(row, reference, 'iter_15000_psnr')} | {fmt_delta(row, reference, 'iter_3000_psnr')} | "
            f"{fmt_delta(row, baseline, 'iter_15000_psnr')} | {fmt_float(row['prior_survival_3000'])} | {fmt_float(row['prior_survival_15000'])} | "
            f"{fmt_int(row['prior_densified_3000'])} | {fmt_int(row['prior_densified_15000'])} | "
            f"{fmt_float(row['total_time_sec'])} | {fmt_float(row['time_to_target_sec'])} |"
        )

    md_lines.extend(
        [
            "",
            "## Interpretation Hints",
            "",
            f"- 현재 기준 비교점 `A 25K current`: iter_0 `{fmt_float(reference.get('iter_0_psnr') if reference else None)}`, iter_3000 `{fmt_float(reference.get('iter_3000_psnr') if reference else None)}`, final `{fmt_float(reference.get('iter_15000_psnr') if reference else None)}`",
            f"- `lr_1.0` final vs A25K: `{fmt_delta(lr10, reference, 'iter_15000_psnr')}` -> `{final_psnr_relation(lr10.get('iter_15000_psnr') if lr10 else None, reference.get('iter_15000_psnr') if reference else None)}`",
            f"- `lr_0.1` final vs A25K: `{fmt_delta(lr01, reference, 'iter_15000_psnr')}` -> `{final_psnr_relation(lr01.get('iter_15000_psnr') if lr01 else None, reference.get('iter_15000_psnr') if reference else None)}`",
            f"- `full_none` final vs A25K: `{fmt_delta(full_none, reference, 'iter_15000_psnr')}` -> `{final_psnr_relation(full_none.get('iter_15000_psnr') if full_none else None, reference.get('iter_15000_psnr') if reference else None)}`",
            f"- `full_none` prior@15000: `{fmt_int(full_none.get('prior_15000') if full_none else None)}` / kept `{fmt_int(full_none.get('prior_kept_total') if full_none else None)}`",
            f"- `full_none` densified@15000: `{fmt_int(full_none.get('prior_densified_15000') if full_none else None)}`",
        ]
    )

    output_path = build_dated_doc_path(ROOT, doc_dir="experiment_results", slug=report_slug, when=report_date)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")
    print(f"Summary CSV: {summary_csv}")
    print(f"Checkpoints CSV: {checkpoints_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
