#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

import sys

SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.runtime_paths import build_dated_doc_path, build_dated_report_csv_path


@dataclass(slots=True)
class RunRecord:
    experiment_name: str
    scene_name: str
    run_dir: Path
    source_path: Path
    source_root: str
    image_count: int
    train_view_count: int | None
    test_view_count: int | None
    iterations: int | None
    is_backup: bool


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def infer_scene_name(backend_run_path: Path) -> tuple[str, str]:
    scene_name = backend_run_path.parent.name
    experiment_name = backend_run_path.parent.parent.name
    if experiment_name == "experiments":
        experiment_name = backend_run_path.parent.name
        scene_name = "default"
    return experiment_name, scene_name


def count_images(source_path: Path) -> int:
    images_dir = source_path / "images"
    if not images_dir.is_dir():
        return 0
    return sum(1 for entry in images_dir.iterdir() if entry.is_file())


def parse_record(backend_run_path: Path) -> RunRecord | None:
    payload = load_json(backend_run_path)
    source_path_value = payload.get("source_path")
    if not source_path_value:
        return None
    source_path = Path(str(source_path_value))
    if "replica_colmap" not in str(source_path):
        return None
    experiment_name, scene_name = infer_scene_name(backend_run_path)
    if scene_name == "default":
        scene_name = source_path.name
    image_count = count_images(source_path)
    scene_meta_path = source_path / "scene_meta.json"
    train_view_count = None
    test_view_count = None
    if scene_meta_path.is_file():
        scene_meta = load_json(scene_meta_path)
        train_view_count = scene_meta.get("train_view_count")
        test_view_count = scene_meta.get("test_view_count")
    command = payload.get("command", [])
    iterations = None
    for index, token in enumerate(command):
        if token == "--iterations" and index + 1 < len(command):
            try:
                iterations = int(command[index + 1])
            except ValueError:
                iterations = None
            break
    return RunRecord(
        experiment_name=experiment_name,
        scene_name=scene_name,
        run_dir=backend_run_path.parent,
        source_path=source_path,
        source_root=str(source_path.parent),
        image_count=image_count,
        train_view_count=int(train_view_count) if train_view_count is not None else None,
        test_view_count=int(test_view_count) if test_view_count is not None else None,
        iterations=iterations,
        is_backup="_backup_" in scene_name or "_backup_" in experiment_name,
    )


def collect_records(experiments_root: Path) -> list[RunRecord]:
    records: list[RunRecord] = []
    for backend_run_path in sorted(experiments_root.rglob("backend_run.json")):
        record = parse_record(backend_run_path)
        if record is not None:
            records.append(record)
    return records


def write_csv(records: list[RunRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "experiment_name",
                "scene_name",
                "run_dir",
                "source_path",
                "source_root",
                "image_count",
                "train_view_count",
                "test_view_count",
                "iterations",
                "is_backup",
            ]
        )
        for record in records:
            writer.writerow(
                [
                    record.experiment_name,
                    record.scene_name,
                    str(record.run_dir),
                    str(record.source_path),
                    record.source_root,
                    record.image_count,
                    record.train_view_count if record.train_view_count is not None else "",
                    record.test_view_count if record.test_view_count is not None else "",
                    record.iterations if record.iterations is not None else "",
                    int(record.is_backup),
                ]
            )


def render_group(group_key: tuple[str, int], items: list[RunRecord]) -> list[str]:
    source_root, image_count = group_key
    lines = [f"## {image_count} images", ""]
    lines.append(f"- source root: `{source_root}`")
    lines.append(f"- run count: `{len(items)}`")
    scenes = ", ".join(sorted({item.scene_name for item in items}))
    lines.append(f"- scenes: `{scenes}`")
    split_pairs = sorted(
        {
            (
                item.train_view_count if item.train_view_count is not None else -1,
                item.test_view_count if item.test_view_count is not None else -1,
            )
            for item in items
        }
    )
    split_labels = ", ".join(
        f"{train if train >= 0 else '?'} train / {test if test >= 0 else '?'} test" for train, test in split_pairs
    )
    lines.append(f"- splits: `{split_labels}`")
    lines.append("")
    lines.append("| Experiment | Scene | Iterations | Backup | Run Dir |")
    lines.append("| --- | --- | ---: | --- | --- |")
    for item in sorted(items, key=lambda entry: (entry.experiment_name, entry.scene_name, str(entry.run_dir))):
        lines.append(
            f"| `{item.experiment_name}` | `{item.scene_name}` | `{item.iterations if item.iterations is not None else ''}` | "
            f"`{'yes' if item.is_backup else 'no'}` | `{item.run_dir}` |"
        )
    lines.append("")
    return lines


def write_markdown(records: list[RunRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    groups: dict[tuple[str, int], list[RunRecord]] = defaultdict(list)
    for record in records:
        groups[(record.source_root, record.image_count)].append(record)

    lines = [
        "# Replica Image Count Inventory",
        "",
        "- 목적: 현재 gaussian-direct 실험 결과를 reconstruction 입력 이미지 수 기준으로 정리한다.",
        "- 기준: `outputs/gaussian_direct/experiments/**/backend_run.json`를 스캔하고, 각 run의 `source_path/images` 실제 파일 수를 센다.",
        "",
        "## Summary",
        "",
        f"- total runs: `{len(records)}`",
        f"- groups: `{len(groups)}`",
        "",
    ]
    for group_key in sorted(groups.keys(), key=lambda item: (item[1], item[0])):
        lines.extend(render_group(group_key, groups[group_key]))
    path.write_text("\n".join(lines), encoding="utf-8")


def default_csv_path(root: Path, *, when: date | datetime) -> Path:
    return build_dated_report_csv_path(
        root / "outputs" / "gaussian_direct",
        slug="image_count_inventory",
        kind="summary",
        when=when,
    )


def default_markdown_path(root: Path, *, when: date | datetime) -> Path:
    return build_dated_doc_path(root, doc_dir="notes", slug="image_count_inventory", when=when)


def main() -> int:
    report_date = datetime.now(UTC).date()
    parser = argparse.ArgumentParser(description="Inventory Replica experiment runs by reconstruction image count.")
    parser.add_argument(
        "--experiments-root",
        type=Path,
        default=ROOT / "outputs/gaussian_direct/experiments",
        help="Experiment root containing backend_run.json files.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=default_csv_path(ROOT, when=report_date),
        help="Output CSV path.",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=default_markdown_path(ROOT, when=report_date),
        help="Output markdown path.",
    )
    args = parser.parse_args()

    records = collect_records(args.experiments_root.resolve())
    write_csv(records, args.csv.resolve())
    write_markdown(records, args.markdown.resolve())
    print(f"Wrote {len(records)} run records")
    print(args.csv.resolve())
    print(args.markdown.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
