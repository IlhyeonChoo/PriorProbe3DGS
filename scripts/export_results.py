#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def collect_evaluations(outputs_root: Path) -> list[dict]:
    evaluations: list[dict] = []
    for path in sorted(outputs_root.glob("experiments/*/evaluation.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["experiment_name"] = path.parent.name
        evaluations.append(payload)
    return evaluations


def to_markdown_table(rows: list[dict]) -> str:
    lines = [
        "| experiment | total_time_sec | time_to_target_sec | psnr | ssim | lpips |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {experiment_name} | {total_optimization_time_sec} | {time_to_target_quality_sec} | {psnr} | {ssim} | {lpips} |".format(
                **row
            )
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export experiment results to a Markdown table.")
    parser.add_argument("--outputs-dir", default="outputs", type=Path)
    parser.add_argument("--output", default="outputs/reports/summary.md", type=Path)
    args = parser.parse_args()

    outputs_dir = args.outputs_dir if args.outputs_dir.is_absolute() else ROOT / args.outputs_dir
    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    rows = collect_evaluations(outputs_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(to_markdown_table(rows), encoding="utf-8")
    print(f"Exported {len(rows)} evaluations to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
