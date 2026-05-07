#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.validation import validate_prior_positions


_REEXEC_ENV = "PRIOR_POSITION_VALIDATOR_REEXEC"


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
    parser = argparse.ArgumentParser(description="Validate prior insertion positions with multi-view 2D evidence.")
    parser.add_argument("--backend-run-dir", required=True, type=Path, help="Backend model directory under outputs/.../backend_runs")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory to write validation reports and overlays")
    parser.add_argument("--iou-threshold", type=float, default=0.50)
    parser.add_argument("--bbox-iou-threshold", type=float, default=0.60)
    parser.add_argument("--centroid-threshold-px", type=float, default=15.0)
    parser.add_argument("--edge-threshold-px", type=float, default=12.0)
    parser.add_argument("--min-views", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _maybe_reexec_under_backend_python(args.backend_run_dir)
    result = validate_prior_positions(
        args.backend_run_dir,
        mask_iou_threshold=float(args.iou_threshold),
        bbox_iou_threshold=float(args.bbox_iou_threshold),
        centroid_threshold_px=float(args.centroid_threshold_px),
        edge_threshold_px=float(args.edge_threshold_px),
        min_views=int(args.min_views),
        output_dir=args.output_dir,
    )
    contact_sheet_path = args.output_dir / "contact_sheet.png"
    print(json.dumps({
        "decision": result.decision,
        "summary_path": str(args.output_dir / "summary.json"),
        "contact_sheet": str(contact_sheet_path) if contact_sheet_path.exists() else None,
        "decision_reasons": result.summary.get("decision_reasons", []),
    }, ensure_ascii=False))
    if result.decision == "PASS":
        return 0
    if result.decision == "AMBIGUOUS":
        return 2
    if result.decision == "INPUT_MISMATCH":
        return 3
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
