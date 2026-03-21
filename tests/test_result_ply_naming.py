from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.result_ply_naming import (
    ensure_named_point_cloud,
    experiment_result_label,
    infer_experiment_name,
    result_ply_filename,
)


def test_result_ply_filename_encodes_experiment_and_protection() -> None:
    assert experiment_result_label("gaussian_direct_same_scene_exact_clip_diverse_384_weak_15000") == "same_scene_exact"
    assert experiment_result_label("gaussian_direct_same_scene_exact_clip_diverse_384_freeze_smoke_1000") == "same_scene_exact"
    assert (
        result_ply_filename(
            experiment_name="gaussian_direct_same_scene_exact_clip_diverse_384_weak_15000",
            iteration=3000,
            protection_mode="weak",
            protect_from_prune=True,
            protect_from_densify=True,
        )
        == "same_scene_exact_weak_protect_prune_densify_iter_3000.ply"
    )


def test_infer_experiment_name_handles_scene_and_non_scene_model_paths(tmp_path: Path) -> None:
    scene_model_path = tmp_path / "backend_runs" / "gaussian_direct_same_scene_exact_clip_15000" / "room_0"
    bare_model_path = tmp_path / "backend_runs" / "gaussian_direct_merge_tiny_room_0"
    assert infer_experiment_name(scene_model_path) == "gaussian_direct_same_scene_exact_clip_15000"
    assert infer_experiment_name(bare_model_path) == "gaussian_direct_merge_tiny_room_0"


def test_ensure_named_point_cloud_renames_file_and_keeps_compatibility_symlink(tmp_path: Path) -> None:
    iteration_dir = tmp_path / "point_cloud" / "iteration_3000"
    iteration_dir.mkdir(parents=True)
    canonical = iteration_dir / "point_cloud.ply"
    canonical.write_text("ply-data", encoding="utf-8")

    target = ensure_named_point_cloud(
        iteration_dir=iteration_dir,
        experiment_name="gaussian_direct_same_scene_exact_clip_diverse_384_weak_15000",
        iteration=3000,
        protection_mode="weak",
        protect_from_prune=True,
        protect_from_densify=True,
    )

    assert target.name == "same_scene_exact_weak_protect_prune_densify_iter_3000.ply"
    assert target.read_text(encoding="utf-8") == "ply-data"
    assert canonical.is_symlink()
    assert os.readlink(canonical) == target.name
