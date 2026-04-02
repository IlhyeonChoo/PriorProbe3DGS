from __future__ import annotations

import re
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


PROJECT_CONFIG_PATH = Path("configs/base/project.yaml")


@lru_cache(maxsize=None)
def _load_project_config(path: str) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        return {}
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def load_project_runtime(root: Path) -> dict[str, Any]:
    config_path = (root / PROJECT_CONFIG_PATH).resolve()
    payload = _load_project_config(str(config_path))
    runtime = payload.get("runtime", {})
    return dict(runtime) if isinstance(runtime, dict) else {}


def resolve_runtime_path(root: Path, key: str, *, fallback: str) -> Path:
    runtime = load_project_runtime(root)
    raw_value = runtime.get(key, fallback)
    path = Path(str(raw_value))
    return path if path.is_absolute() else root / path


def to_repo_relative_path(path: Path, *, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _coerce_report_date(when: date | datetime) -> date:
    if isinstance(when, datetime):
        return when.date()
    return when


def build_dated_doc_path(root: Path, *, doc_dir: str, slug: str, when: date | datetime) -> Path:
    report_date = _coerce_report_date(when)
    date_prefix = report_date.strftime("%m-%d")
    year = report_date.strftime("%Y")
    return root / "docs" / doc_dir / f"{date_prefix}_{slug}_{year}.md"


def build_dated_report_csv_path(outputs_dir: Path, *, slug: str, kind: str, when: date | datetime) -> Path:
    report_date = _coerce_report_date(when)
    date_prefix = report_date.strftime("%m-%d")
    year = report_date.strftime("%Y")
    return outputs_dir / "reports" / f"{date_prefix}_{slug}_{kind}_{year}.csv"


def legacy_report_csv_path(outputs_dir: Path, *, slug: str, kind: str) -> Path:
    return outputs_dir / "reports" / f"replica_gaussian_direct_{slug}_{kind}.csv"


def find_latest_dated_report_csv(outputs_dir: Path, *, slug: str, kind: str) -> Path | None:
    reports_dir = outputs_dir / "reports"
    if not reports_dir.exists():
        return None

    pattern = re.compile(
        rf"^(?P<month>\d{{2}})-(?P<day>\d{{2}})_{re.escape(slug)}_{re.escape(kind)}_(?P<year>\d{{4}})\.csv$"
    )
    candidates: list[tuple[date, str, Path]] = []
    for candidate in reports_dir.glob(f"??-??_{slug}_{kind}_*.csv"):
        match = pattern.fullmatch(candidate.name)
        if match is None:
            continue
        try:
            report_date = date(
                int(match.group("year")),
                int(match.group("month")),
                int(match.group("day")),
            )
        except ValueError:
            continue
        candidates.append((report_date, candidate.name, candidate))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[0], item[1]))
    return candidates[-1][2]
