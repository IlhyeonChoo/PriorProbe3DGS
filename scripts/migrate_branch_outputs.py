#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STANDARD_OUTPUT_DIRS = ("backend_runs", "experiments", "prior_library", "reports")


def resolve_path(root: Path, path_value: Path) -> Path:
    return path_value if path_value.is_absolute() else root / path_value


def ensure_parent(path: Path, *, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)


def move_path(
    source: Path,
    destination: Path,
    *,
    dry_run: bool,
    conflict_destination: Path | None = None,
) -> None:
    if not source.exists():
        return
    if destination.exists():
        if source.is_dir() and destination.is_dir():
            merge_directory(
                source,
                destination,
                dry_run=dry_run,
                conflict_root=conflict_destination,
            )
            return
        if conflict_destination is None:
            raise FileExistsError(f"destination already exists: {destination}")
        if conflict_destination.exists():
            raise FileExistsError(f"conflict destination already exists: {conflict_destination}")
        print(f"{source} -> {conflict_destination} (collision)")
        if dry_run:
            return
        ensure_parent(conflict_destination, dry_run=False)
        shutil.move(str(source), str(conflict_destination))
        return
    print(f"{source} -> {destination}")
    if dry_run:
        return
    ensure_parent(destination, dry_run=False)
    shutil.move(str(source), str(destination))


def merge_directory(
    source: Path,
    destination: Path,
    *,
    dry_run: bool,
    conflict_root: Path | None,
) -> None:
    for child in sorted(source.iterdir()):
        child_conflict = conflict_root / child.name if conflict_root is not None else None
        move_path(
            child,
            destination / child.name,
            dry_run=dry_run,
            conflict_destination=child_conflict,
        )
    if dry_run:
        return
    source.rmdir()


def migrate_outputs(outputs_root: Path, *, branch_slug: str, dry_run: bool) -> None:
    branch_root = outputs_root / branch_slug
    for name in STANDARD_OUTPUT_DIRS:
        move_path(
            outputs_root / name,
            branch_root / name,
            dry_run=dry_run,
            conflict_destination=branch_root / "legacy_misc" / name,
        )

    for path in sorted(outputs_root.iterdir()):
        if path.name in {".gitkeep", branch_slug}:
            continue
        if path.name in STANDARD_OUTPUT_DIRS:
            continue
        move_path(path, branch_root / "legacy_misc" / path.name, dry_run=dry_run)


def migrate_logs(logs_root: Path, *, branch_slug: str, dry_run: bool) -> None:
    branch_root = logs_root / branch_slug
    if dry_run:
        print(f"ensure {branch_root}")
        return
    branch_root.mkdir(parents=True, exist_ok=True)
    gitkeep = branch_root / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Move legacy outputs and logs into a branch-specific root.")
    parser.add_argument("--branch-slug", required=True, help="Target branch slug such as pointcloud or gaussian_direct.")
    parser.add_argument("--repo-root", type=Path, default=ROOT, help="Repository root to migrate.")
    parser.add_argument("--outputs-root", type=Path, default=Path("outputs"), help="Outputs root relative to repo root.")
    parser.add_argument("--logs-root", type=Path, default=Path("logs"), help="Logs root relative to repo root.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned moves without mutating the filesystem.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = resolve_path(ROOT, args.repo_root).resolve()
    outputs_root = resolve_path(repo_root, args.outputs_root)
    logs_root = resolve_path(repo_root, args.logs_root)

    if not outputs_root.exists():
        raise SystemExit(f"outputs root does not exist: {outputs_root}")

    migrate_outputs(outputs_root, branch_slug=args.branch_slug, dry_run=bool(args.dry_run))
    migrate_logs(logs_root, branch_slug=args.branch_slug, dry_run=bool(args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
