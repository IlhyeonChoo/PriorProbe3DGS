#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKEND_RUNS_DIR = ROOT / "outputs" / "gaussian_direct" / "backend_runs"
VIEWER_SCRIPT = ROOT / "scripts" / "build_initial_snapshot_viewer.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build inspection viewers for the most recent backend-run experiments."
    )
    parser.add_argument(
        "count",
        nargs="?",
        type=int,
        default=None,
        help="Number of recent experiment directories to process. Prompts when omitted.",
    )
    parser.add_argument(
        "--backend-runs-dir",
        type=Path,
        default=DEFAULT_BACKEND_RUNS_DIR,
        help="Directory containing experiment subdirectories under outputs/gaussian_direct/backend_runs.",
    )
    parser.add_argument(
        "--max-views",
        type=int,
        default=6,
        help="Number of views to include in each generated contact sheet.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the selected experiments and commands without generating viewers.",
    )
    return parser.parse_args()


def parse_positive_count(value: str) -> int:
    try:
        count = int(value)
    except ValueError as exc:
        raise ValueError("Count must be an integer.") from exc
    if count <= 0:
        raise ValueError("Count must be positive.")
    return count


def resolve_count(count: int | None) -> int:
    if count is not None:
        if count <= 0:
            raise SystemExit("Count must be positive.")
        return count
    while True:
        try:
            raw_value = input("How many recent experiments should be processed? ").strip()
        except EOFError as exc:
            raise SystemExit("Failed to read experiment count from stdin.") from exc
        try:
            return parse_positive_count(raw_value)
        except ValueError as exc:
            print(exc, file=sys.stderr)


def list_recent_experiment_dirs(backend_runs_dir: Path, count: int) -> list[Path]:
    if not backend_runs_dir.exists():
        raise FileNotFoundError(f"Missing backend runs directory: {backend_runs_dir}")
    experiment_dirs = [path for path in backend_runs_dir.iterdir() if path.is_dir()]
    experiment_dirs.sort(key=lambda path: (path.stat().st_mtime_ns, path.name), reverse=True)
    return experiment_dirs[:count]


def discover_backend_run_dirs(experiment_dir: Path) -> list[Path]:
    backend_run_dirs = []
    for child in sorted(experiment_dir.iterdir()):
        if child.is_dir() and (child / "cfg_args").exists():
            backend_run_dirs.append(child)
    return backend_run_dirs


def build_viewer_command(backend_run_dir: Path, max_views: int) -> list[str]:
    return [
        sys.executable,
        str(VIEWER_SCRIPT),
        "--backend-run-dir",
        str(backend_run_dir),
        "--max-views",
        str(max_views),
    ]


def main() -> int:
    args = parse_args()
    count = resolve_count(args.count)
    backend_runs_dir = args.backend_runs_dir.resolve()
    experiment_dirs = list_recent_experiment_dirs(backend_runs_dir, count)
    if not experiment_dirs:
        raise SystemExit(f"No experiment directories found under {backend_runs_dir}")

    print(f"Selected {len(experiment_dirs)} recent experiments from {backend_runs_dir}")

    generated = 0
    failures = 0
    for experiment_dir in experiment_dirs:
        backend_run_dirs = discover_backend_run_dirs(experiment_dir)
        if not backend_run_dirs:
            print(f"- Skipping {experiment_dir.name}: no scene backend runs found")
            continue
        print(f"- {experiment_dir.name}: {len(backend_run_dirs)} scene(s)")
        for backend_run_dir in backend_run_dirs:
            command = build_viewer_command(backend_run_dir, max_views=args.max_views)
            print(f"  - {backend_run_dir.name}")
            if args.dry_run:
                print(f"    {' '.join(command)}")
                continue
            try:
                subprocess.run(command, check=True)
                generated += 1
            except subprocess.CalledProcessError as exc:
                failures += 1
                print(
                    f"    Failed with exit code {exc.returncode}: {backend_run_dir}",
                    file=sys.stderr,
                )

    if args.dry_run:
        print("Dry run completed.")
        return 0

    print(f"Generated viewers for {generated} backend run(s).")
    if failures:
        print(f"Encountered failures for {failures} backend run(s).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
