#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
import sys

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.result_ply_naming import ensure_named_point_cloud, infer_experiment_name


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rename_iteration_dir(iteration_dir: Path) -> Path:
    model_path = iteration_dir.parent.parent
    experiment_name = infer_experiment_name(model_path)
    iteration = int(iteration_dir.name.split("_")[-1])
    protection_path = iteration_dir / "prior_protection.json"
    if protection_path.exists():
        protection = load_json(protection_path)
        mode = str(protection.get("mode", "none"))
        protect_from_prune = bool(protection.get("protect_from_prune", False))
        protect_from_densify = bool(protection.get("protect_from_densify", False))
    else:
        mode = "none"
        protect_from_prune = False
        protect_from_densify = False
    return ensure_named_point_cloud(
        iteration_dir=iteration_dir,
        experiment_name=experiment_name,
        iteration=iteration,
        protection_mode=mode,
        protect_from_prune=protect_from_prune,
        protect_from_densify=protect_from_densify,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Rename saved point cloud PLY files to the normalized result format.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("outputs/gaussian_direct/backend_runs"),
        help="Root directory to scan for point_cloud/iteration_* folders.",
    )
    args = parser.parse_args()

    root = args.root if args.root.is_absolute() else ROOT / args.root
    iteration_dirs = sorted(root.glob("**/point_cloud/iteration_*"))
    renamed = 0
    for iteration_dir in iteration_dirs:
        canonical_path = iteration_dir / "point_cloud.ply"
        if not canonical_path.exists() and not canonical_path.is_symlink():
            continue
        target = rename_iteration_dir(iteration_dir)
        renamed += 1
        print(f"{canonical_path} -> {target.name}")

    print(f"Renamed or refreshed {renamed} iteration directories under {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
