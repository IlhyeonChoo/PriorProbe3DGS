#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.experiment_storage import storage_experiment_name


def move_path(source: Path, destination: Path, *, dry_run: bool) -> None:
    print(f"{source} -> {destination}")
    if dry_run:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rename gaussian_direct experiment directories to shorter branch-local names."
    )
    parser.add_argument(
        "--outputs-root",
        type=Path,
        default=Path("outputs/gaussian_direct"),
        help="Branch-specific outputs root. Defaults to outputs/gaussian_direct.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned moves without mutating the filesystem.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    outputs_root = args.outputs_root if args.outputs_root.is_absolute() else ROOT / args.outputs_root

    for bucket in ("backend_runs", "experiments"):
        bucket_root = outputs_root / bucket
        if not bucket_root.exists():
            continue
        for path in sorted(child for child in bucket_root.iterdir() if child.is_dir()):
            shortened = storage_experiment_name(path.name, outputs_root=outputs_root)
            if shortened == path.name:
                continue
            destination = bucket_root / shortened
            if not destination.exists():
                move_path(path, destination, dry_run=bool(args.dry_run))
                continue
            conflict_root = outputs_root / "legacy_prefixed" / bucket / path.name
            move_path(path, conflict_root, dry_run=bool(args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
