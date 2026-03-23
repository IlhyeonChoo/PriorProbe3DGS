from __future__ import annotations

from pathlib import Path

from priorprobe.experiment_storage import (
    experiment_storage_dir,
    resolve_experiment_storage_dir,
    storage_experiment_name,
)


def test_storage_experiment_name_strips_gaussian_direct_prefix_for_branch_outputs() -> None:
    outputs_root = Path("outputs/gaussian_direct")
    assert (
        storage_experiment_name(
            "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_15000",
            outputs_root=outputs_root,
        )
        == "same_scene_exact_clip_roomwide_v2_384_15000"
    )


def test_storage_experiment_name_keeps_name_for_other_output_roots() -> None:
    outputs_root = Path("outputs/pointcloud")
    assert (
        storage_experiment_name(
            "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_15000",
            outputs_root=outputs_root,
        )
        == "gaussian_direct_same_scene_exact_clip_roomwide_v2_384_15000"
    )


def test_resolve_experiment_storage_dir_prefers_shortened_directory(tmp_path: Path) -> None:
    outputs_root = tmp_path / "gaussian_direct"
    shortened = experiment_storage_dir(outputs_root, "experiments", "gaussian_direct_demo_run")
    shortened.mkdir(parents=True)

    resolved = resolve_experiment_storage_dir(outputs_root, "experiments", "gaussian_direct_demo_run")

    assert resolved == shortened


def test_resolve_experiment_storage_dir_falls_back_to_prefixed_directory(tmp_path: Path) -> None:
    outputs_root = tmp_path / "gaussian_direct"
    prefixed = outputs_root / "experiments" / "gaussian_direct_demo_run"
    prefixed.mkdir(parents=True)

    resolved = resolve_experiment_storage_dir(outputs_root, "experiments", "gaussian_direct_demo_run")

    assert resolved == prefixed
