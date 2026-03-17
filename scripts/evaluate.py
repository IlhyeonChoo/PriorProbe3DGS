#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.evaluation.metrics import summarize_run
from priorprobe.optimization.trainer import TrainingRun


def resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description="Recompute evaluation from a run summary.")
    parser.add_argument("--run-summary", required=True, type=Path)
    parser.add_argument("--output", type=Path, help="Optional output path for evaluation JSON.")
    args = parser.parse_args()

    run_summary_path = resolve_path(str(args.run_summary))
    payload = json.loads(run_summary_path.read_text(encoding="utf-8"))
    run = TrainingRun.from_dict(payload)
    evaluation = summarize_run(run)

    if args.output is None:
        output_path = run_summary_path.with_name("evaluation.json")
    else:
        output_path = resolve_path(str(args.output))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(evaluation.to_dict(), indent=2), encoding="utf-8")
    print(f"Wrote evaluation to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
