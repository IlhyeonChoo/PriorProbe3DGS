from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datetime import UTC, date, datetime

from priorprobe.runtime_paths import (
    build_dated_doc_path,
    build_dated_report_csv_path,
    find_latest_dated_report_csv,
    legacy_report_csv_path,
    resolve_runtime_path,
    to_repo_relative_path,
)


def test_resolve_runtime_path_reads_project_config(tmp_path: Path) -> None:
    config_path = tmp_path / "configs" / "base" / "project.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        """
runtime:
  outputs_dir: outputs/gaussian_direct
  logs_dir: logs/gaussian_direct
""".strip(),
        encoding="utf-8",
    )

    assert resolve_runtime_path(tmp_path, "outputs_dir", fallback="outputs") == (
        tmp_path / "outputs" / "gaussian_direct"
    )
    assert resolve_runtime_path(tmp_path, "logs_dir", fallback="logs") == (
        tmp_path / "logs" / "gaussian_direct"
    )


def test_to_repo_relative_path_returns_relative_path_inside_root(tmp_path: Path) -> None:
    path = tmp_path / "outputs" / "gaussian_direct" / "prior_library" / "manifest.json"

    assert to_repo_relative_path(path, root=tmp_path) == "outputs/gaussian_direct/prior_library/manifest.json"


def test_to_repo_relative_path_keeps_absolute_path_outside_root(tmp_path: Path) -> None:
    path = Path("/tmp/priorprobe/manifest.json")

    assert to_repo_relative_path(path, root=tmp_path) == str(path)


def test_build_dated_doc_path_uses_mm_dd_slug_year_format(tmp_path: Path) -> None:
    assert build_dated_doc_path(
        tmp_path,
        doc_dir="experiment_results",
        slug="phase3_room_0",
        when=date(2026, 3, 22),
    ) == (tmp_path / "docs" / "experiment_results" / "03-22_phase3_room_0_2026.md")


def test_build_dated_report_csv_path_accepts_datetime(tmp_path: Path) -> None:
    assert build_dated_report_csv_path(
        tmp_path / "outputs" / "gaussian_direct",
        slug="phase5_surface_rgb",
        kind="summary",
        when=datetime(2026, 3, 24, 8, 30, tzinfo=UTC),
    ) == (
        tmp_path
        / "outputs"
        / "gaussian_direct"
        / "reports"
        / "03-24_phase5_surface_rgb_summary_2026.csv"
    )


def test_legacy_report_csv_path_uses_legacy_replica_prefix(tmp_path: Path) -> None:
    assert legacy_report_csv_path(
        tmp_path / "outputs" / "gaussian_direct",
        slug="phase3_room_0",
        kind="summary",
    ) == (
        tmp_path
        / "outputs"
        / "gaussian_direct"
        / "reports"
        / "replica_gaussian_direct_phase3_room_0_summary.csv"
    )


def test_find_latest_dated_report_csv_returns_latest_matching_date(tmp_path: Path) -> None:
    reports_dir = tmp_path / "outputs" / "gaussian_direct" / "reports"
    reports_dir.mkdir(parents=True)
    older = reports_dir / "03-22_phase3_room_0_summary_2026.csv"
    newer = reports_dir / "03-27_phase3_room_0_summary_2026.csv"
    ignored = reports_dir / "03-28_phase3_room_0_checkpoints_2026.csv"
    older.write_text("older\n", encoding="utf-8")
    newer.write_text("newer\n", encoding="utf-8")
    ignored.write_text("ignored\n", encoding="utf-8")

    assert find_latest_dated_report_csv(
        tmp_path / "outputs" / "gaussian_direct",
        slug="phase3_room_0",
        kind="summary",
    ) == newer


def test_find_latest_dated_report_csv_returns_none_when_missing(tmp_path: Path) -> None:
    reports_dir = tmp_path / "outputs" / "gaussian_direct" / "reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "replica_gaussian_direct_phase3_room_0_summary.csv").write_text("legacy\n", encoding="utf-8")

    assert (
        find_latest_dated_report_csv(
            tmp_path / "outputs" / "gaussian_direct",
            slug="phase3_room_0",
            kind="summary",
        )
        is None
    )
