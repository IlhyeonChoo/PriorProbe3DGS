from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_viewer_script_module():
    script_path = ROOT / "scripts" / "build_initial_snapshot_viewer.py"
    spec = importlib.util.spec_from_file_location("build_initial_snapshot_viewer", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_resolve_aligned_prior_path_falls_back_to_current_backend_run_dir(tmp_path: Path) -> None:
    script = _load_viewer_script_module()
    backend_run_dir = tmp_path / "same_scene_exact_clip_roomwide_v2_384_prior_25k_15000" / "room_0"
    prior_init_dir = backend_run_dir / "prior_init"
    prior_init_dir.mkdir(parents=True)
    actual_aligned = prior_init_dir / "aligned_prior_00.ply"
    actual_aligned.write_text("ply", encoding="utf-8")

    stale_path = tmp_path / "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_prior_25k_15000" / "room_0" / "prior_init" / "aligned_prior_00.ply"

    resolved = script.resolve_aligned_prior_path(stale_path, backend_run_dir)

    assert resolved == actual_aligned


def test_normalize_prior_entries_rewrites_stale_aligned_prior_path(tmp_path: Path) -> None:
    script = _load_viewer_script_module()
    backend_run_dir = tmp_path / "same_scene_exact_clip_roomwide_v2_384_prior_25k_15000" / "room_0"
    prior_init_dir = backend_run_dir / "prior_init"
    prior_init_dir.mkdir(parents=True)
    actual_aligned = prior_init_dir / "aligned_prior_00.ply"
    actual_aligned.write_text("ply", encoding="utf-8")

    entries = [
        {
            "aligned_prior": str(
                tmp_path
                / "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_prior_25k_15000"
                / "room_0"
                / "prior_init"
                / "aligned_prior_00.ply"
            ),
            "prior_object_id": "chair_0001",
            "target_object_id": 6,
            "target_category": "chair",
            "prior_score": 0.9,
        }
    ]

    normalized = script.normalize_prior_entries(entries, backend_run_dir)

    assert normalized[0]["aligned_prior"] == str(actual_aligned.resolve())
