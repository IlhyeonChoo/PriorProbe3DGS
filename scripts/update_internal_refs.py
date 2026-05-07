#!/usr/bin/env python3
"""Update internal references under outputs/gaussian_direct before renaming.

Usage:
    python scripts/update_internal_refs.py              # dry-run (default)
    python scripts/update_internal_refs.py --execute     # apply updates
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs" / "gaussian_direct"


@dataclass(frozen=True)
class ComponentReplacement:
    old: str
    new: str
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class ReplacementRules:
    exact_map: dict[str, str]
    component_replacements: tuple[ComponentReplacement, ...]


@dataclass(frozen=True)
class FileUpdate:
    path: Path
    change_count: int
    details: tuple[str, ...]


def load_rename_module():
    script_path = ROOT / "scripts" / "rename_to_date_format.py"
    spec = importlib.util.spec_from_file_location("rename_to_date_format", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def build_rules_from_maps(
    *,
    exact_map: dict[str, str],
    component_map: dict[str, str],
) -> ReplacementRules:
    replacements: list[ComponentReplacement] = []
    for old, new in sorted(component_map.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = re.compile(
            rf"(^|[/='\"(,\s:])({re.escape(old)})(?=$|[/='\"),\s:])"
        )
        replacements.append(ComponentReplacement(old=old, new=new, pattern=pattern))
    return ReplacementRules(
        exact_map=dict(exact_map),
        component_replacements=tuple(replacements),
    )


def _rename_pairs_to_name_map(
    renames: list[tuple[Path, Path, str]],
) -> dict[str, str]:
    return {old_path.name: new_path.name for old_path, new_path, _ in renames}


def _derive_stem_map(name_map: dict[str, str]) -> dict[str, str]:
    stem_map: dict[str, str] = {}
    for old_name, new_name in name_map.items():
        old_path = Path(old_name)
        new_path = Path(new_name)
        if old_path.suffix and new_path.suffix:
            stem_map[old_path.stem] = new_path.stem
    return stem_map


def build_replacement_rules() -> ReplacementRules:
    rename_module = load_rename_module()

    experiment_dir_map = _rename_pairs_to_name_map(
        rename_module.collect_renames_dirs("experiments")
    )
    backend_run_dir_map = _rename_pairs_to_name_map(
        rename_module.collect_renames_dirs("backend_runs")
    )
    prior_library_map = _rename_pairs_to_name_map(
        rename_module.collect_renames_prior("prior_library")
    )
    prior_training_map = _rename_pairs_to_name_map(
        rename_module.collect_renames_prior("prior_training")
    )
    prior_library_stem_map = _derive_stem_map(prior_library_map)

    exact_map: dict[str, str] = {}
    exact_map.update(experiment_dir_map)
    exact_map.update({f"gaussian_direct_{old}": new for old, new in experiment_dir_map.items()})
    exact_map.update(backend_run_dir_map)
    exact_map.update(prior_library_map)
    exact_map.update(prior_training_map)
    exact_map.update(prior_library_stem_map)

    component_map: dict[str, str] = {}
    component_map.update(experiment_dir_map)
    component_map.update(backend_run_dir_map)
    component_map.update(prior_library_map)
    component_map.update(prior_training_map)
    component_map.update(prior_library_stem_map)

    return build_rules_from_maps(exact_map=exact_map, component_map=component_map)


def is_legacy_path(path: Path) -> bool:
    return any(part.startswith("legacy_bugged_") for part in path.parts)


def transform_string(value: str, rules: ReplacementRules) -> str:
    updated = rules.exact_map.get(value, value)
    for replacement in rules.component_replacements:
        updated = replacement.pattern.sub(
            lambda match: f"{match.group(1)}{replacement.new}",
            updated,
        )
    return updated


def transform_json_value(
    value: Any,
    rules: ReplacementRules,
    *,
    location: str = "$",
) -> tuple[Any, list[str]]:
    if isinstance(value, dict):
        updated_dict: dict[str, Any] = {}
        changed_locations: list[str] = []
        for key, nested_value in value.items():
            next_location = f"{location}.{key}"
            updated_value, nested_changes = transform_json_value(
                nested_value,
                rules,
                location=next_location,
            )
            updated_dict[key] = updated_value
            changed_locations.extend(nested_changes)
        return updated_dict, changed_locations

    if isinstance(value, list):
        updated_list: list[Any] = []
        changed_locations: list[str] = []
        for index, nested_value in enumerate(value):
            next_location = f"{location}[{index}]"
            updated_value, nested_changes = transform_json_value(
                nested_value,
                rules,
                location=next_location,
            )
            updated_list.append(updated_value)
            changed_locations.extend(nested_changes)
        return updated_list, changed_locations

    if isinstance(value, str):
        updated = transform_string(value, rules)
        if updated != value:
            return updated, [location]
        return value, []

    return value, []


def update_text_content(text: str, rules: ReplacementRules) -> tuple[str, tuple[str, ...]]:
    updated = transform_string(text, rules)
    if updated == text:
        return text, ()

    matched_keys = [
        replacement.old
        for replacement in rules.component_replacements
        if replacement.pattern.search(text)
    ]
    return updated, tuple(matched_keys[:8])


def _write_text_preserving_times(path: Path, content: str) -> None:
    stat_result = path.stat()
    with path.open("w", encoding="utf-8") as handle:
        handle.write(content)
    os.utime(path, ns=(stat_result.st_atime_ns, stat_result.st_mtime_ns))


def process_json_file(path: Path, rules: ReplacementRules, *, dry_run: bool) -> FileUpdate | None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    updated_payload, changed_locations = transform_json_value(payload, rules)
    if not changed_locations:
        return None

    if not dry_run:
        serialized = json.dumps(updated_payload, indent=2) + "\n"
        _write_text_preserving_times(path, serialized)

    return FileUpdate(
        path=path,
        change_count=len(changed_locations),
        details=tuple(changed_locations[:6]),
    )


def process_text_file(path: Path, rules: ReplacementRules, *, dry_run: bool) -> FileUpdate | None:
    original = path.read_text(encoding="utf-8")
    updated, matched_keys = update_text_content(original, rules)
    if updated == original:
        return None

    if not dry_run:
        _write_text_preserving_times(path, updated)

    return FileUpdate(
        path=path,
        change_count=max(1, len(matched_keys)),
        details=matched_keys,
    )


def process_csv_file(path: Path, rules: ReplacementRules, *, dry_run: bool) -> FileUpdate | None:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))

    if not rows:
        return None

    headers = rows[0]
    changed_columns: list[str] = []
    changed_count = 0

    for row_index, row in enumerate(rows):
        for column_index, cell in enumerate(row):
            updated = transform_string(cell, rules)
            if updated == cell:
                continue
            rows[row_index][column_index] = updated
            changed_count += 1
            header = headers[column_index] if column_index < len(headers) else f"column_{column_index}"
            if header not in changed_columns:
                changed_columns.append(header)

    if changed_count == 0:
        return None

    if not dry_run:
        stat_result = path.stat()
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerows(rows)
        os.utime(path, ns=(stat_result.st_atime_ns, stat_result.st_mtime_ns))

    return FileUpdate(
        path=path,
        change_count=changed_count,
        details=tuple(changed_columns[:8]),
    )


def _iter_experiment_jsons() -> list[Path]:
    root = OUTPUTS / "experiments"
    return sorted(
        path
        for path in root.rglob("*.json")
        if not is_legacy_path(path)
    )


def _iter_backend_cfg_args() -> list[Path]:
    root = OUTPUTS / "backend_runs"
    return sorted(
        path
        for path in root.rglob("cfg_args")
        if not is_legacy_path(path)
    )


def _iter_prior_training_cfg_args() -> list[Path]:
    root = OUTPUTS / "prior_training"
    return sorted(
        path
        for path in root.rglob("cfg_args")
        if not is_legacy_path(path)
    )


def _iter_report_csvs() -> list[Path]:
    root = OUTPUTS / "reports"
    return sorted(
        path
        for path in root.glob("*.csv")
        if not is_legacy_path(path)
    )


def _iter_prior_library_files() -> list[Path]:
    root = OUTPUTS / "prior_library"
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix in {".json", ".yaml", ".yml"}
        and not is_legacy_path(path)
    )


def _run_updates(
    label: str,
    paths: list[Path],
    processor,
    rules: ReplacementRules,
    *,
    dry_run: bool,
) -> tuple[int, int]:
    print(f"\n{'=' * 60}")
    print(f"{label}")
    print(f"{'=' * 60}")

    changed_files = 0
    total_changes = 0
    for path in paths:
        update = processor(path, rules, dry_run=dry_run)
        if update is None:
            continue

        changed_files += 1
        total_changes += update.change_count
        details = ", ".join(update.details) if update.details else "content"
        prefix = "[DRY-RUN]" if dry_run else "[UPDATED]"
        print(
            f"{prefix} {update.path.relative_to(ROOT)}"
            f" ({update.change_count} changes: {details})"
        )

    if changed_files == 0:
        print("(no changes)")
    else:
        print(f"changed files: {changed_files}, replacements: {total_changes}")
    return changed_files, total_changes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update internal references under outputs/gaussian_direct."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually write the changes (default: dry-run).",
    )
    args = parser.parse_args()

    rules = build_replacement_rules()
    dry_run = not args.execute

    total_files = 0
    total_replacements = 0

    sections = [
        ("experiments JSON", _iter_experiment_jsons(), process_json_file),
        ("backend_runs cfg_args", _iter_backend_cfg_args(), process_text_file),
        ("prior_training cfg_args", _iter_prior_training_cfg_args(), process_text_file),
        ("reports CSV", _iter_report_csvs(), process_csv_file),
        ("prior_library JSON/YAML", _iter_prior_library_files(), process_text_file),
    ]

    for label, paths, processor in sections:
        changed_files, change_count = _run_updates(
            label,
            paths,
            processor,
            rules,
            dry_run=dry_run,
        )
        total_files += changed_files
        total_replacements += change_count

    print(f"\n{'=' * 60}")
    print(f"mode: {'DRY-RUN' if dry_run else 'EXECUTE'}")
    print(f"changed files: {total_files}")
    print(f"total replacements: {total_replacements}")
    if dry_run:
        print("run with --execute to apply updates")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
