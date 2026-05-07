from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    script_path = ROOT / "scripts" / "prepare_replica_phase5_surface_assets.py"
    spec = importlib.util.spec_from_file_location("prepare_replica_phase5_surface_assets", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_validate_phase5_output_paths_rejects_partial_shared_defaults(tmp_path: Path) -> None:
    module = _load_module()
    output_paths = dict(module.shared_phase5_output_defaults())
    output_paths["inventory-out"] = (tmp_path / "custom_inventory.json").resolve()

    with pytest.raises(ValueError, match="--dataset-config-out"):
        module.validate_phase5_output_paths(is_partial_run=True, output_paths=output_paths)


def test_validate_phase5_output_paths_allows_partial_custom_outputs(tmp_path: Path) -> None:
    module = _load_module()
    output_paths = {
        "dataset-config-out": (tmp_path / "dataset.yaml").resolve(),
        "manifest-out": (tmp_path / "manifest.json").resolve(),
        "config-out": (tmp_path / "manifest.yaml").resolve(),
        "inventory-out": (tmp_path / "inventory.json").resolve(),
        "report-out": (tmp_path / "report.md").resolve(),
        "prior-stage-root": (tmp_path / "prior_stage").resolve(),
    }

    module.validate_phase5_output_paths(is_partial_run=True, output_paths=output_paths)


def test_is_partial_phase5_run_treats_target_object_filter_as_partial() -> None:
    module = _load_module()

    assert module.is_partial_phase5_run(
        requested_scene_ids=None,
        available_scene_ids=["room_0", "office_0"],
        requested_object_ids={74},
    )
