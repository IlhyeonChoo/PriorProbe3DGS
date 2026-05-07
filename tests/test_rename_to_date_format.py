from __future__ import annotations

import importlib.util
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_rename_module():
    script_path = ROOT / "scripts" / "rename_to_date_format.py"
    spec = importlib.util.spec_from_file_location("rename_to_date_format", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_transform_dir_name_uses_dated_short_format() -> None:
    rename_module = _load_rename_module()

    assert rename_module.transform_dir_name("surface_rgb_prior_25k_15000", "03-24-2026") == (
        "03-24-prior25k-15k-2026"
    )
    assert rename_module.transform_dir_name("surface_rgb_baseline_15000_fixscale", "03-26-2026") == (
        "03-26-baseline-fixscale-15k-2026"
    )
    assert rename_module.transform_report_name(
        "replica_image_count_inventory_2026-03-20.csv",
        "03-20-2026",
    ) == "03-20-image-count-inventory-2026.csv"
    assert rename_module.transform_prior_name("replica_surface_exact_trained_7000", "03-23-2026") == (
        "03-23-surface-trained-7k-2026"
    )
    assert rename_module.transform_dir_name("03-24-baseline-15k-2026", "04-02-2026") == (
        "03-24-baseline-15k-2026"
    )
    assert rename_module.transform_report_name(
        "03-24-phase5-surface-rgb-summary-2026.csv",
        "04-02-2026",
    ) == "03-24-phase5-surface-rgb-summary-2026.csv"
    assert rename_module.transform_prior_name(
        "03-24-target-surface-trained-2026",
        "04-02-2026",
    ) == "03-24-target-surface-trained-2026"


def test_collect_renames_dirs_disambiguates_collisions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rename_module = _load_rename_module()
    outputs_root = tmp_path / "outputs" / "gaussian_direct"
    experiments_dir = outputs_root / "experiments"
    experiments_dir.mkdir(parents=True)

    for name in (
        "baseline_from_scratch",
        "baseline_from_scratch_vanilla_3dgs",
        "baseline_from_scratch_vanilla_3dgs_multi",
    ):
        (experiments_dir / name).mkdir()

    mtime = datetime(2026, 3, 19, tzinfo=UTC).timestamp()
    for path in experiments_dir.iterdir():
        os.utime(path, (mtime, mtime))

    monkeypatch.setattr(rename_module, "OUTPUTS", outputs_root)

    renames = rename_module.collect_renames_dirs("experiments")
    actual = {old_path.name: new_path.name for old_path, new_path, _ in renames}

    assert actual == {
        "baseline_from_scratch": "03-19-baseline-2026",
        "baseline_from_scratch_vanilla_3dgs": "03-19-baseline-a-2026",
        "baseline_from_scratch_vanilla_3dgs_multi": "03-19-baseline-b-2026",
    }
