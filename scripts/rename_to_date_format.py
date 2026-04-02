#!/usr/bin/env python3
"""Rename experiment outputs to date-based format: MM-DD-{settings}-YYYY.

Usage:
    python scripts/rename_to_date_format.py              # dry-run (default)
    python scripts/rename_to_date_format.py --execute     # actually rename
    python scripts/rename_to_date_format.py --bucket experiments  # specific bucket only
"""
from __future__ import annotations

import argparse
import os
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs" / "gaussian_direct"

# ---------------------------------------------------------------------------
# Name transformation rules
# ---------------------------------------------------------------------------

STRIP_PREFIXES = [
    "gaussian_direct_",
    "surface_rgb_",
]

# Multi-token replacements applied BEFORE splitting (order matters)
MULTI_TOKEN_SHORTEN = [
    ("baseline_from_scratch", "baseline"),
    ("oracle_prior", "oracle"),
    ("same_scene", "samescene"),
    ("replace_region", "replace"),
    ("full_none", "fullnone"),
    ("sh_zero", "shzero"),
    ("cross_validation", "crossval"),
]

# Single-token replacements
SINGLE_TOKEN_SHORTEN = {
    "variance": "var",
    "repeat": "rep",
    "roomwide": "rw",
    "alignfix": "af",
    "diverse": "div",
    "existing": "exist",
    "merged": "merge",
    "retrieval": "retr",
    "select": "sel",
    "filtered": "filt",
    "weighted": "wt",
}

# Tokens to drop entirely (common defaults / redundant)
DROP_TOKENS = {
    "vanilla", "3dgs", "multi", "single", "clip", "from_scratch",
    "exact", "rgb", "mean", "geom", "direct", "gaussian",
}

# Iteration label regex.
ITER_RE = re.compile(r"^\d+$")
DATED_NAME_RE = re.compile(r"^\d{2}-\d{2}-.+-\d{4}$")


def is_already_dated_name(name: str) -> bool:
    return bool(DATED_NAME_RE.fullmatch(name))


def shorten_iter(val: str) -> str:
    n = int(val)
    if n >= 1000 and n % 1000 == 0:
        return f"{n // 1000}k"
    return val


def _merge_prior_size(tokens: list[str]) -> list[str]:
    """Merge 'prior' + size/qualifier -> 'prior25k', 'priorfull'."""
    merged: list[str] = []
    i = 0
    while i < len(tokens):
        if (
            tokens[i] == "prior"
            and i + 1 < len(tokens)
            and re.match(r"^(\d+k?|full)$", tokens[i + 1])
        ):
            merged.append(f"prior{tokens[i + 1]}")
            i += 2
        else:
            merged.append(tokens[i])
            i += 1
    return merged


def transform_dir_name(old_name: str, date_str: str) -> str:
    """Transform old directory name to new date-based format.

    Args:
        old_name: e.g. "surface_rgb_prior_25k_15000"
        date_str: e.g. "03-24-2026" (MM-DD-YYYY)

    Returns:
        New name like "03-24-prior25k-15k-2026"
    """
    if is_already_dated_name(old_name):
        return old_name

    mm, dd, yyyy = date_str.split("-")
    name = old_name

    # 1. Strip known prefixes
    for pfx in STRIP_PREFIXES:
        if name.startswith(pfx):
            name = name[len(pfx) :]

    # 2. Multi-token shortenings (before split)
    for old, new in MULTI_TOKEN_SHORTEN:
        name = name.replace(old, new)

    # 3. Split and process tokens
    tokens = [t for t in name.split("_") if t]

    # 4. Extract the last iteration-like token (>= 1000) and place it at the end.
    iter_token = None
    for index in range(len(tokens) - 1, -1, -1):
        if ITER_RE.match(tokens[index]) and int(tokens[index]) >= 1000:
            iter_token = shorten_iter(tokens[index])
            del tokens[index]
            break

    # 5. Drop common/redundant tokens
    tokens = [t for t in tokens if t.lower() not in DROP_TOKENS]

    # 6. Single-token shortenings (exact match first, then prefix match)
    shortened: list[str] = []
    for t in tokens:
        if t in SINGLE_TOKEN_SHORTEN:
            shortened.append(SINGLE_TOKEN_SHORTEN[t])
        else:
            replaced = False
            for long, short in SINGLE_TOKEN_SHORTEN.items():
                if t.startswith(long) and len(t) > len(long):
                    shortened.append(short + t[len(long):])
                    replaced = True
                    break
            if not replaced:
                shortened.append(t)
    tokens = shortened

    # 7. Merge 'prior' + size
    tokens = _merge_prior_size(tokens)

    # 8. Handle 'smoke' as a suffix: if 'smoke' is present and iter is 1k, keep it
    # (smoke is informative, not redundant)

    # 9. Remove empty tokens and join
    tokens = [t for t in tokens if t]
    settings = "-".join(tokens)

    if iter_token:
        settings = f"{settings}-{iter_token}" if settings else iter_token

    if not settings:
        settings = old_name  # fallback

    return f"{mm}-{dd}-{settings}-{yyyy}"


def transform_report_name(old_name: str, date_str: str) -> str:
    """Transform report filename to new format.

    Old: replica_gaussian_direct_phase5_surface_rgb_summary.csv
    New: 03-24-phase5-surface-rgb-summary-2026.csv
    """
    mm, dd, yyyy = date_str.split("-")
    stem = Path(old_name).stem
    ext = Path(old_name).suffix

    if is_already_dated_name(stem):
        return old_name

    # Strip common prefixes
    for pfx in [
        "replica_gaussian_direct_",
        "replica_",
        "gaussian_direct_",
    ]:
        if stem.startswith(pfx):
            stem = stem[len(pfx) :]
    if stem.startswith("surface_rgb_"):
        stem = stem[len("surface_rgb_") :]

    stem = re.sub(r"(?:_|-)\d{4}-\d{2}-\d{2}$", "", stem)

    # Replace _ with -
    stem = stem.replace("_", "-")

    return f"{mm}-{dd}-{stem}-{yyyy}{ext}"


def transform_prior_name(old_name: str, date_str: str) -> str:
    """Transform prior library/training names.

    Old: replica_target_surface_exact_trained_clip
    New: 03-20-target-surface-trained-2026
    """
    if is_already_dated_name(old_name):
        return old_name

    mm, dd, yyyy = date_str.split("-")
    name = old_name

    # Strip replica_ prefix
    if name.startswith("replica_"):
        name = name[len("replica_") :]

    # Remove redundant tokens
    for token in ["exact", "clip"]:
        name = name.replace(f"_{token}", "")
        if name.startswith(f"{token}_"):
            name = name[len(f"{token}_") :]

    tokens = [token for token in name.split("_") if token]
    shortened_tokens = [
        shorten_iter(token) if ITER_RE.match(token) and int(token) >= 1000 else token
        for token in tokens
    ]
    name = "-".join(shortened_tokens)

    return f"{mm}-{dd}-{name}-{yyyy}"


def _alpha_suffix(index: int) -> str:
    """Convert 1-based collision index to a stable alphabetic suffix."""
    if index < 1:
        raise ValueError("collision index must be >= 1")

    chars: list[str] = []
    current = index
    while current > 0:
        current -= 1
        chars.append(chr(ord("a") + (current % 26)))
        current //= 26
    return "".join(reversed(chars))


def _insert_suffix_before_year(name: str, suffix: str) -> str:
    """Insert disambiguation suffix before the trailing -YYYY.

    '03-19-baseline-2026' + 'a' -> '03-19-baseline-a-2026'
    """
    match = re.match(r"^(.+)-(\d{4})$", name)
    if match:
        return f"{match.group(1)}-{suffix}-{match.group(2)}"
    return f"{name}-{suffix}"


def _with_disambiguation_suffix(path: Path, suffix: str, *, is_file: bool) -> Path:
    name = path.name
    if is_file:
        suffixes = "".join(Path(name).suffixes)
        stem = name[: -len(suffixes)] if suffixes else name
        new_stem = _insert_suffix_before_year(stem, suffix)
        return path.with_name(f"{new_stem}{suffixes}")
    return path.with_name(_insert_suffix_before_year(name, suffix))


def ensure_unique_targets(renames: list[tuple[Path, Path, str]]) -> list[tuple[Path, Path, str]]:
    """Disambiguate rename targets that would otherwise collide."""
    if not renames:
        return renames

    grouped: dict[Path, list[tuple[Path, Path, str]]] = {}
    for rename in renames:
        grouped.setdefault(rename[0].parent, []).append(rename)

    deduplicated: list[tuple[Path, Path, str]] = []
    for parent, items in grouped.items():
        old_names = {old_path.name for old_path, _, _ in items}
        reserved_names = {
            entry.name for entry in parent.iterdir() if entry.name not in old_names
        }
        used_names = set(reserved_names)

        for old_path, new_path, reason in items:
            candidate = new_path
            collision_index = 0
            while candidate.name in used_names:
                collision_index += 1
                candidate = _with_disambiguation_suffix(
                    new_path,
                    _alpha_suffix(collision_index),
                    is_file=old_path.is_file(),
                )
            used_names.add(candidate.name)
            if candidate != new_path:
                reason = f"{reason} (disambiguated to {candidate.name})"
            deduplicated.append((old_path, candidate, reason))

    return deduplicated


# ---------------------------------------------------------------------------
# Filesystem operations
# ---------------------------------------------------------------------------


def get_dir_date(path: Path) -> str:
    """Get modification date as MM-DD-YYYY."""
    mtime = os.path.getmtime(path)
    dt = datetime.fromtimestamp(mtime)
    return dt.strftime("%m-%d-%Y")


def get_file_date(path: Path) -> str:
    """Get modification date of a file as MM-DD-YYYY."""
    mtime = os.path.getmtime(path)
    dt = datetime.fromtimestamp(mtime)
    return dt.strftime("%m-%d-%Y")


def collect_renames_dirs(bucket: str) -> list[tuple[Path, Path, str]]:
    """Collect (old_path, new_path, reason) for a bucket directory."""
    bucket_path = OUTPUTS / bucket
    if not bucket_path.is_dir():
        return []

    renames = []
    for entry in sorted(bucket_path.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("legacy_bugged_"):
            continue
        if is_already_dated_name(entry.name):
            continue
        date_str = get_dir_date(entry)
        new_name = transform_dir_name(entry.name, date_str)
        if new_name != entry.name:
            new_path = entry.parent / new_name
            renames.append((entry, new_path, f"{entry.name} -> {new_name}"))
    return ensure_unique_targets(renames)


def collect_renames_reports() -> list[tuple[Path, Path, str]]:
    """Collect renames for report files."""
    reports_dir = OUTPUTS / "reports"
    if not reports_dir.is_dir():
        return []

    renames = []
    for entry in sorted(reports_dir.iterdir()):
        if not entry.is_file():
            continue
        if entry.name.startswith("legacy_bugged_"):
            continue
        if is_already_dated_name(entry.stem):
            continue
        date_str = get_file_date(entry)
        new_name = transform_report_name(entry.name, date_str)
        if new_name != entry.name:
            new_path = entry.parent / new_name
            renames.append((entry, new_path, f"{entry.name} -> {new_name}"))
    return ensure_unique_targets(renames)


def collect_renames_prior(bucket: str) -> list[tuple[Path, Path, str]]:
    """Collect renames for prior_library or prior_training entries."""
    bucket_path = OUTPUTS / bucket
    if not bucket_path.is_dir():
        return []

    renames = []
    for entry in sorted(bucket_path.iterdir()):
        if entry.name.startswith("legacy_bugged_"):
            continue

        date_str = get_file_date(entry) if entry.is_file() else get_dir_date(entry)
        base = entry.name
        ext = ""
        if entry.is_file():
            ext = "".join(entry.suffixes)
            for s in entry.suffixes:
                base = base.removesuffix(s)
        if is_already_dated_name(base):
            continue

        # For companion files (manifest, inventory, yaml), match their parent dir name
        new_base = transform_prior_name(base, date_str)
        new_name = f"{new_base}{ext}"

        if new_name != entry.name:
            new_path = entry.parent / new_name
            renames.append((entry, new_path, f"{entry.name} -> {new_name}"))
    return ensure_unique_targets(renames)


def execute_rename(old_path: Path, new_path: Path, *, dry_run: bool = True) -> bool:
    """Rename a file or directory. Returns True if successful."""
    if new_path.exists():
        print(f"  SKIP (target exists): {new_path.name}")
        return False
    if not dry_run:
        old_path.rename(new_path)
    return True


def main():
    parser = argparse.ArgumentParser(description="Rename experiment outputs to date-based format")
    parser.add_argument("--execute", action="store_true", help="Actually perform renames (default: dry-run)")
    parser.add_argument("--bucket", choices=["experiments", "backend_runs", "reports", "prior_library", "prior_training", "all"], default="all")
    args = parser.parse_args()

    dry_run = not args.execute
    buckets = (
        ["experiments", "backend_runs", "reports", "prior_library", "prior_training"]
        if args.bucket == "all"
        else [args.bucket]
    )

    total_renames = 0

    for bucket in buckets:
        print(f"\n{'='*60}")
        print(f"  {bucket}")
        print(f"{'='*60}")

        if bucket == "reports":
            renames = collect_renames_reports()
        elif bucket in ("prior_library", "prior_training"):
            renames = collect_renames_prior(bucket)
        else:
            renames = collect_renames_dirs(bucket)

        if not renames:
            print("  (no renames needed)")
            continue

        for old_path, new_path, reason in renames:
            prefix = "[DRY-RUN] " if dry_run else ""
            success = execute_rename(old_path, new_path, dry_run=dry_run)
            status = "OK" if success else "SKIP"
            print(f"  {prefix}{status}: {reason}")
            if success:
                total_renames += 1

    print(f"\n{'='*60}")
    mode = "DRY-RUN" if dry_run else "EXECUTED"
    print(f"  {mode}: {total_renames} renames")
    if dry_run:
        print("  Run with --execute to apply.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
