from __future__ import annotations

import importlib.util
import os
import sys
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_update_module():
    script_path = ROOT / "scripts" / "update_internal_refs.py"
    spec = importlib.util.spec_from_file_location("update_internal_refs", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_transform_json_value_updates_nested_paths_and_exact_names() -> None:
    update_module = _load_update_module()
    rules = update_module.build_rules_from_maps(
        exact_map={
            "gaussian_direct_surface_rgb_baseline_15000": "03-24-baseline-15k-2026",
            "surface_rgb_baseline_15000": "03-24-baseline-15k-2026",
        },
        component_map={
            "surface_rgb_baseline_15000": "03-24-baseline-15k-2026",
            "replica_target_surface_exact_trained_clip": "03-20-target-surface-trained-2026",
        },
    )

    original = {
        "experiment_name": "gaussian_direct_surface_rgb_baseline_15000",
        "storage_experiment_name": "surface_rgb_baseline_15000",
        "model_path": (
            "/tmp/outputs/gaussian_direct/backend_runs/surface_rgb_baseline_15000/room_0"
        ),
        "command_string": (
            "/tmp/tool --model_path "
            "/tmp/outputs/gaussian_direct/backend_runs/surface_rgb_baseline_15000/room_0"
        ),
        "render_runs": [
            {
                "stdout_log": (
                    "/tmp/outputs/gaussian_direct/experiments/"
                    "surface_rgb_baseline_15000/room_0/render_500_stdout.log"
                ),
            }
        ],
        "selected_prior": {
            "source_prior_path": (
                "/tmp/outputs/gaussian_direct/prior_library/"
                "replica_target_surface_exact_trained_clip/assets/chair/splat.ply"
            )
        },
    }

    updated, changed_locations = update_module.transform_json_value(original, rules)

    assert updated["experiment_name"] == "03-24-baseline-15k-2026"
    assert updated["storage_experiment_name"] == "03-24-baseline-15k-2026"
    assert "/03-24-baseline-15k-2026/" in updated["model_path"]
    assert "/03-24-baseline-15k-2026/" in updated["command_string"]
    assert "/03-24-baseline-15k-2026/" in updated["render_runs"][0]["stdout_log"]
    assert "/03-20-target-surface-trained-2026/" in updated["selected_prior"]["source_prior_path"]
    assert "$.selected_prior.source_prior_path" in changed_locations


def test_process_csv_and_text_files_preserve_mtime(tmp_path: Path) -> None:
    update_module = _load_update_module()
    rules = update_module.build_rules_from_maps(
        exact_map={
            "baseline_from_scratch_vanilla_3dgs": "03-19-baseline-2026",
        },
        component_map={
            "baseline_from_scratch_vanilla_3dgs": "03-19-baseline-2026",
            "replica_target_surface_exact_trained_clip": "03-20-target-surface-trained-2026",
            "replica_target_surface_exact_trained_clip_manifest": "03-20-target-surface-trained-2026",
            "replica_target_surface_exact_trained_clip_manifest.json": (
                "03-20-target-surface-trained-2026.json"
            ),
        },
    )

    csv_path = tmp_path / "report.csv"
    csv_path.write_text(
        "experiment_name,run_dir\n"
        "baseline_from_scratch_vanilla_3dgs,"
        "/tmp/outputs/gaussian_direct/experiments/baseline_from_scratch_vanilla_3dgs/room_0\n",
        encoding="utf-8",
    )

    yaml_path = tmp_path / "library.yaml"
    yaml_path.write_text(
        "library:\n"
        "  name: replica_target_surface_exact_trained_clip_manifest\n"
        "  manifest_path: outputs/gaussian_direct/prior_library/"
        "replica_target_surface_exact_trained_clip_manifest.json\n",
        encoding="utf-8",
    )

    original_time = datetime(2026, 3, 20, tzinfo=UTC).timestamp()
    os.utime(csv_path, (original_time, original_time))
    os.utime(yaml_path, (original_time, original_time))

    csv_update = update_module.process_csv_file(csv_path, rules, dry_run=False)
    yaml_update = update_module.process_text_file(yaml_path, rules, dry_run=False)

    assert csv_update is not None
    assert yaml_update is not None
    assert csv_path.stat().st_mtime == original_time
    assert yaml_path.stat().st_mtime == original_time

    csv_text = csv_path.read_text(encoding="utf-8")
    yaml_text = yaml_path.read_text(encoding="utf-8")
    assert "03-19-baseline-2026" in csv_text
    assert "/03-19-baseline-2026/" in csv_text
    assert "03-20-target-surface-trained-2026" in yaml_text
