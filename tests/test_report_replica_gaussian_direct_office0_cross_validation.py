from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _load_script_module():
    script_path = ROOT / "scripts" / "report_replica_gaussian_direct_office0_cross_validation.py"
    spec = importlib.util.spec_from_file_location("report_replica_gaussian_direct_office0_cross_validation", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_summary_csv(path: Path, *, label: str, iter_0_psnr: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"label,iter_0_psnr\n{label},{iter_0_psnr}\n", encoding="utf-8")


def test_resolve_room0_reference_summary_prefers_latest_dated_csv(tmp_path: Path) -> None:
    script = _load_script_module()
    outputs_dir = tmp_path / "outputs" / "gaussian_direct"
    reports_dir = outputs_dir / "reports"
    legacy = reports_dir / "replica_gaussian_direct_interference_combinations_room_0_summary.csv"
    older = reports_dir / "03-22_interference_combinations_room_0_summary_2026.csv"
    newer = reports_dir / "03-24_interference_combinations_room_0_summary_2026.csv"
    _write_summary_csv(legacy, label="baseline", iter_0_psnr="1.0")
    _write_summary_csv(older, label="baseline", iter_0_psnr="2.0")
    _write_summary_csv(newer, label="baseline", iter_0_psnr="3.0")

    resolved = script.resolve_room0_reference_summary(outputs_dir)
    loaded = script.load_room0_reference(outputs_dir)

    assert resolved == newer
    assert loaded["baseline"]["iter_0_psnr"] == "3.0"


def test_resolve_room0_reference_summary_falls_back_to_legacy_csv(tmp_path: Path) -> None:
    script = _load_script_module()
    outputs_dir = tmp_path / "outputs" / "gaussian_direct"
    legacy = outputs_dir / "reports" / "replica_gaussian_direct_interference_combinations_room_0_summary.csv"
    _write_summary_csv(legacy, label="A prior_25k", iter_0_psnr="4.0")

    resolved = script.resolve_room0_reference_summary(outputs_dir)
    loaded = script.load_room0_reference(outputs_dir)

    assert resolved == legacy
    assert loaded["A prior_25k"]["iter_0_psnr"] == "4.0"


def test_load_room0_reference_returns_empty_mapping_when_missing(tmp_path: Path) -> None:
    script = _load_script_module()
    outputs_dir = tmp_path / "outputs" / "gaussian_direct"

    assert script.resolve_room0_reference_summary(outputs_dir) is None
    assert script.load_room0_reference(outputs_dir) == {}
