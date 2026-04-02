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
from priorprobe.runtime_paths import (
    build_dated_doc_path,
    build_dated_report_csv_path,
    find_latest_dated_report_csv,
    legacy_report_csv_path,
)


EXPERIMENTS = {
    "baseline": {
        "group": "reference",
        "label": "baseline",
        "experiment_name": "gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_v2_384_15000",
    },
    "prior_100k": {
        "group": "reference",
        "label": "prior 100K legacy",
        "experiment_name": "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_15000",
    },
    "prior_25k": {
        "group": "cross_validation",
        "label": "A 25K",
        "experiment_name": "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_prior_25k_15000",
    },
    "combo_ac": {
        "group": "cross_validation",
        "label": "A+C",
        "experiment_name": "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_prior_25k_sh_zero_15000",
    },
    "combo_ab": {
        "group": "cross_validation",
        "label": "A+B",
        "experiment_name": "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_prior_25k_replace_region_15000",
    },
    "combo_abc": {
        "group": "cross_validation",
        "label": "A+B+C",
        "experiment_name": "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_prior_25k_replace_region_sh_zero_15000",
    },
}

ROOM0_REFERENCE_SLUG = "interference_combinations_room_0"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_backend_run_payload(
    backend_run_path: Path,
    *,
    outputs_dir: Path,
    experiment_name: str,
    scene_id: str,
) -> dict[str, Any]:
    payload = load_json(backend_run_path)
    model_path_value = payload.get("model_path")
    model_path = Path(str(model_path_value)) if model_path_value else None
    if model_path is not None and model_path.exists():
        return payload

    resolved_model_path = resolve_experiment_storage_dir(outputs_dir, "backend_runs", experiment_name) / scene_id
    if resolved_model_path.exists():
        payload["model_path"] = str(resolved_model_path)
        backend_run_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


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


def maybe_float(value: str | float | int | None) -> float | None:
    if value in (None, "", "n/a"):
        return None
    return float(value)


def fmt_delta(lhs: float | None, rhs: float | None) -> str:
    if lhs is None or rhs is None:
        return "n/a"
    return f"{lhs - rhs:+.6f}"


def resolve_room0_reference_summary(outputs_dir: Path) -> Path | None:
    dated = find_latest_dated_report_csv(outputs_dir, slug=ROOM0_REFERENCE_SLUG, kind="summary")
    if dated is not None:
        return dated
    legacy = legacy_report_csv_path(outputs_dir, slug=ROOM0_REFERENCE_SLUG, kind="summary")
    if legacy.exists():
        return legacy
    return None


def load_room0_reference(outputs_dir: Path) -> dict[str, dict[str, Any]]:
    candidate = resolve_room0_reference_summary(outputs_dir)
    if candidate is None:
        return {}
    with candidate.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return {}
    by_label: dict[str, dict[str, Any]] = {}
    for row in rows:
        label = str(row.get("label") or "")
        by_label[label] = row
    return by_label


def main() -> int:
    parser = argparse.ArgumentParser(description="Report office_0 cross-validation runs.")
    parser.add_argument("--outputs-dir", type=Path, default=ROOT / "outputs" / "gaussian_direct")
    parser.add_argument("--scene-id", type=str, default="office_0")
    args = parser.parse_args()
    outputs_dir = args.outputs_dir
    report_date = datetime.now(UTC).date()
    report_slug = "office0_cross_validation" if args.scene_id == "office_0" else f"office0_cross_validation_{args.scene_id}"

    rows: list[dict[str, Any]] = []
    baseline_target_psnr: float | None = None

    for family_id, spec in EXPERIMENTS.items():
        experiment_name = str(spec["experiment_name"])
        experiment_dir = resolve_experiment_storage_dir(outputs_dir, "experiments", experiment_name) / args.scene_id
        backend_run_path = experiment_dir / "backend_run.json"
        if not backend_run_path.exists():
            continue
        backend_run = load_backend_run_payload(
            backend_run_path,
            outputs_dir=outputs_dir,
            experiment_name=experiment_name,
            scene_id=args.scene_id,
        )
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
        prior_init_metadata_path = model_path / "prior_init" / "metadata.json"
        prior_init_metadata = load_json(prior_init_metadata_path) if prior_init_metadata_path.exists() else {}
        selected_priors = list(prior_init_metadata.get("selected_priors") or backend_run.get("selected_priors") or [])
        protection_3000 = load_prior_protection(model_path, 3000)
        protection_15000 = load_prior_protection(model_path, 15000)
        insertion = dict(backend_run.get("prior_insertion") or {})

        row = {
            "family_id": family_id,
            "group": spec["group"],
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
            "sfm_removed_point_count": insertion.get(
                "sfm_removed_point_count",
                prior_init_metadata.get("sfm_removed_point_count"),
            ),
            "sfm_removed_point_ratio": insertion.get(
                "sfm_removed_point_ratio",
                prior_init_metadata.get("sfm_removed_point_ratio"),
            ),
            "prior_original_total": sum(int(item.get("original_point_count", 0) or 0) for item in selected_priors),
            "prior_kept_total": sum(int(item.get("kept_point_count", 0) or 0) for item in selected_priors),
            "target_psnr": None,
            "time_to_target_sec": None,
            "total_time_sec": evaluation.get("total_optimization_time_sec"),
            "iter_0_psnr": (checkpoint_by_iteration(checkpoints, 0) or {}).get("psnr"),
            "iter_3000_psnr": (checkpoint_by_iteration(checkpoints, 3000) or {}).get("psnr"),
            "iter_15000_psnr": (checkpoint_by_iteration(checkpoints, 15000) or {}).get("psnr"),
            "iter_15000_ssim": (checkpoint_by_iteration(checkpoints, 15000) or {}).get("ssim"),
            "iter_15000_lpips": (checkpoint_by_iteration(checkpoints, 15000) or {}).get("lpips"),
            "iter_0_gaussians": (checkpoint_by_iteration(checkpoints, 0) or {}).get("gaussian_count"),
            "iter_3000_gaussians": (checkpoint_by_iteration(checkpoints, 3000) or {}).get("gaussian_count"),
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
                    "group": row["group"],
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

    summary_csv = build_dated_report_csv_path(outputs_dir, slug=report_slug, kind="summary", when=report_date)
    checkpoints_csv = build_dated_report_csv_path(
        outputs_dir,
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
            "iter_3000_psnr",
            "iter_15000_psnr",
            "iter_15000_ssim",
            "iter_15000_lpips",
            "iter_0_gaussians",
            "iter_3000_gaussians",
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
            "group",
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

    room0_reference = load_room0_reference(outputs_dir)
    by_id = {row["family_id"]: row for row in summary_rows}
    baseline = by_id.get("baseline")
    a25k = by_id.get("prior_25k")

    lines = [
        "# Office_0 교차 검증: 간섭 완화 조합 실험",
        "",
        f"- Date: {report_date.isoformat()}",
        f"- Scene: `{args.scene_id}`",
        "- Dataset family: `roomwide_v2_384`",
        "- 기준선: 기존 `baseline` 재사용",
        "- 신규 clean run: `A 25K`, `A+C`, `A+B`, `A+B+C`",
        "- 참고: `prior 100K legacy`는 metadata/seed 버그 수정 전 run이며 metric reference로만 사용",
        "",
        "## Summary",
        "",
        "| label | group | sh_reset | prior_budget | sfm_replace | sfm_removed | iter_0_psnr | iter_3000_psnr | final_psnr | final_ssim | final_lpips | ttt_sec | total_sec |",
        "|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            "| {label} | {group} | {prior_sh_reset_mode} | {prior_target_total_gaussians} | {sfm_region_replacement_mode} | {sfm_removed_point_count} | {iter_0_psnr} | {iter_3000_psnr} | {iter_15000_psnr} | {iter_15000_ssim} | {iter_15000_lpips} | {time_to_target_sec} | {total_time_sec} |".format(
                **{
                    **row,
                    "sfm_removed_point_count": row["sfm_removed_point_count"] if row["sfm_removed_point_count"] is not None else "n/a",
                    "time_to_target_sec": (
                        f"{float(row['time_to_target_sec']):.6f}"
                        if row["time_to_target_sec"] is not None
                        else "n/a"
                    ),
                }
            )
        )

    lines.extend(
        [
            "",
            "## Cross-Validation Focus",
            "",
            "| label | final vs baseline | final vs A25K | iter_3000 vs baseline | iter_3000 vs A25K | prior_kept_total | protected@15000 |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for family_id in ("prior_25k", "combo_ac", "combo_ab", "combo_abc"):
        row = by_id.get(family_id)
        if row is None:
            continue
        lines.append(
            "| {label} | {d_final_base} | {d_final_a25k} | {d_i3000_base} | {d_i3000_a25k} | {prior_kept_total} | {protected_15000} |".format(
                label=row["label"],
                d_final_base=fmt_delta(maybe_float(row.get("iter_15000_psnr")), maybe_float((baseline or {}).get("iter_15000_psnr"))),
                d_final_a25k=fmt_delta(maybe_float(row.get("iter_15000_psnr")), maybe_float((a25k or {}).get("iter_15000_psnr"))),
                d_i3000_base=fmt_delta(maybe_float(row.get("iter_3000_psnr")), maybe_float((baseline or {}).get("iter_3000_psnr"))),
                d_i3000_a25k=fmt_delta(maybe_float(row.get("iter_3000_psnr")), maybe_float((a25k or {}).get("iter_3000_psnr"))),
                prior_kept_total=row["prior_kept_total"],
                protected_15000=row["protected_15000"] if row["protected_15000"] is not None else "n/a",
            )
        )

    if room0_reference:
        lines.extend(
            [
                "",
                "## Room_0 Reference",
                "",
                "| label | room_0 iter_0 | office_0 iter_0 | room_0 iter_3000 | office_0 iter_3000 | room_0 final | office_0 final | office-room delta |",
                "|---|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for label in ("baseline", "A prior_25k", "A+C", "A+B", "A+B+C"):
            ref = room0_reference.get(label)
            if ref is None:
                continue
            office_label = {
                "baseline": "baseline",
                "A prior_25k": "A 25K",
                "A+C": "A+C",
                "A+B": "A+B",
                "A+B+C": "A+B+C",
            }[label]
            office_row = next((row for row in summary_rows if row["label"] == office_label), None)
            lines.append(
                "| {label} | {r0_i0} | {o0_i0} | {r0_i3} | {o0_i3} | {r0_f} | {o0_f} | {delta} |".format(
                    label=label,
                    r0_i0=ref.get("iter_0_psnr", "n/a"),
                    o0_i0=office_row.get("iter_0_psnr", "n/a") if office_row else "n/a",
                    r0_i3=ref.get("iter_3000_psnr", "n/a"),
                    o0_i3=office_row.get("iter_3000_psnr", "n/a") if office_row else "n/a",
                    r0_f=ref.get("iter_15000_psnr", "n/a"),
                    o0_f=office_row.get("iter_15000_psnr", "n/a") if office_row else "n/a",
                    delta=fmt_delta(
                        maybe_float(office_row.get("iter_15000_psnr") if office_row else None),
                        maybe_float(ref.get("iter_15000_psnr")),
                    ),
                )
            )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `A 25K`가 office_0에서도 최선이면 room_0에서 본 패턴이 재현된 것으로 본다.",
            "- `A+C` 또는 `A+B+C`가 A25K를 넘으면 scene 의존적인 조합 효과를 의심한다.",
            "- `A+B`가 여전히 약하면 SfM region replacement는 scene-agnostic하게 비효율적일 가능성이 크다.",
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
