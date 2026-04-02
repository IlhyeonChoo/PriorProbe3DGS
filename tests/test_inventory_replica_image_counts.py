from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, date, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_script_module():
    script_path = ROOT / "scripts" / "inventory_replica_image_counts.py"
    spec = importlib.util.spec_from_file_location("inventory_replica_image_counts", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_default_csv_path_uses_dated_reports_naming(tmp_path: Path) -> None:
    script = _load_script_module()

    assert script.default_csv_path(tmp_path, when=date(2026, 3, 20)) == (
        tmp_path / "outputs" / "gaussian_direct" / "reports" / "03-20_image_count_inventory_summary_2026.csv"
    )


def test_default_markdown_path_uses_dated_docs_notes_naming(tmp_path: Path) -> None:
    script = _load_script_module()

    assert script.default_markdown_path(
        tmp_path,
        when=datetime(2026, 3, 20, 8, 30, tzinfo=UTC),
    ) == (tmp_path / "docs" / "notes" / "03-20_image_count_inventory_2026.md")
