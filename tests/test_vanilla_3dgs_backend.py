from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.optimization.vanilla_3dgs import Vanilla3DGSBackendConfig, build_train_command


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _load_backend_module(fake_repo: Path):
    _write_text(fake_repo / "train.py", "")
    _write_text(fake_repo / "gaussian_renderer.py", "")
    _write_text(fake_repo / "scene" / "__init__.py", "")
    _write_text(fake_repo / "scene" / "dataset_readers.py", "")
    _write_text(
        fake_repo / "arguments.py",
        "\n".join(
            [
                "class ModelParams:",
                "    def __init__(self, parser):",
                "        self.parser = parser",
                "",
                "class OptimizationParams:",
                "    def __init__(self, parser):",
                "        self.parser = parser",
                "",
                "class PipelineParams:",
                "    def __init__(self, parser):",
                "        self.parser = parser",
            ]
        )
        + "\n",
    )
    _write_text(
        fake_repo / "utils" / "general_utils.py",
        "\n".join(
            [
                "def build_rotation(*args, **kwargs):",
                "    raise NotImplementedError",
                "",
                "def inverse_sigmoid(*args, **kwargs):",
                "    raise NotImplementedError",
            ]
        )
        + "\n",
    )
    _write_text(fake_repo / "utils" / "__init__.py", "")

    script_path = ROOT / "scripts" / "train_vanilla_3dgs_backend.py"
    spec = importlib.util.spec_from_file_location("priorprobe_train_backend_runtime_test", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    original_argv = sys.argv[:]
    sys.argv = ["train_vanilla_3dgs_backend.py", "--repo-path", str(fake_repo)]
    try:
        spec.loader.exec_module(module)
    finally:
        sys.argv = original_argv
    return module


def test_build_train_command_without_prior(tmp_path: Path) -> None:
    config = Vanilla3DGSBackendConfig(
        repo_path=tmp_path / "gaussian-splatting",
        source_path=tmp_path / "scene",
        model_path=tmp_path / "output",
        python_executable=tmp_path / "gaussian-splatting" / "venv" / "bin" / "python",
        iterations=123,
        disable_viewer=True,
        quiet=True,
        test_iterations=(123,),
        save_iterations=(123,),
    )

    command = build_train_command(config)

    assert command[0] == str(config.python_executable)
    assert command[1].endswith("scripts/train_vanilla_3dgs_backend.py")
    assert "--prior-ply" not in command
    assert "--disable_viewer" in command
    assert "--quiet" in command
    assert "--seed" in command
    assert "--camera-shuffle" in command
    assert "--deterministic" not in command
    assert "123" in command


def test_build_train_command_with_prior_and_alignment(tmp_path: Path) -> None:
    config = Vanilla3DGSBackendConfig(
        repo_path=tmp_path / "gaussian-splatting",
        source_path=tmp_path / "scene",
        model_path=tmp_path / "output",
        python_executable=tmp_path / "gaussian-splatting" / "venv" / "bin" / "python",
        iterations=456,
        init_mode="merge",
    )
    prior_ply = tmp_path / "prior" / "chair.ply"
    alignment_json = tmp_path / "alignments" / "identity.json"

    command = build_train_command(
        config,
        prior_ply=prior_ply,
        alignment_json=alignment_json,
        prior_object_id="chair_basic",
        prior_score=0.91,
    )

    assert "--prior-ply" in command
    assert str(prior_ply) in command
    assert "--alignment-json" in command
    assert str(alignment_json) in command
    assert "--prior-object-id" in command
    assert "chair_basic" in command
    assert "--init-mode" in command
    assert "merge" in command


def test_build_train_command_with_prior_spec_json(tmp_path: Path) -> None:
    config = Vanilla3DGSBackendConfig(
        repo_path=tmp_path / "gaussian-splatting",
        source_path=tmp_path / "scene",
        model_path=tmp_path / "output",
        python_executable=tmp_path / "gaussian-splatting" / "venv" / "bin" / "python",
        iterations=789,
        init_mode="weighted_merge",
        prior_protection_mode="weak",
        prior_lr_scale=0.02,
        prior_sh_reset_mode="zero_all",
        prior_target_total_gaussians=25000,
        prior_subsample_seed=17,
        sfm_region_replacement_mode="aligned_prior_aabb_union",
        sfm_region_margin_scale=1.1,
        sfm_region_margin_min_m=0.05,
        geometry_validation_outside_scene_proxy_ratio_threshold=0.02,
        geometry_validation_mean_nn_threshold_m=0.25,
        geometry_validation_max_prior_points=1024,
        geometry_validation_max_scene_points=4096,
        protect_prior_from_prune=True,
        protect_prior_from_densify=False,
        save_initial_snapshot=True,
        initial_render_sets=("train", "test"),
        seed=19,
        camera_order_seed=23,
        camera_shuffle_enabled=False,
        deterministic=True,
    )
    prior_spec_json = tmp_path / "priors" / "spec.json"

    command = build_train_command(
        config,
        prior_spec_json=prior_spec_json,
    )

    assert "--prior-spec-json" in command
    assert "--init-mode" in command
    assert "weighted_merge" in command
    assert "--prior-protection-mode" in command
    assert "weak" in command
    assert "--prior-lr-scale" in command
    assert "0.02" in command
    assert "--prior-sh-reset-mode" in command
    assert "zero_all" in command
    assert "--prior-target-total-gaussians" in command
    assert "25000" in command
    assert "--prior-subsample-seed" in command
    assert "17" in command
    assert "--sfm-region-replacement-mode" in command
    assert "aligned_prior_aabb_union" in command
    assert "--sfm-region-margin-scale" in command
    assert "1.1" in command
    assert "--sfm-region-margin-min-m" in command
    assert "0.05" in command
    assert "--geometry-validation-outside-scene-proxy-ratio-threshold" in command
    assert "0.02" in command
    assert "--geometry-validation-mean-nn-threshold-m" in command
    assert "0.25" in command
    assert "--geometry-validation-max-prior-points" in command
    assert "1024" in command
    assert "--geometry-validation-max-scene-points" in command
    assert "4096" in command
    assert "--protect-prior-from-prune" in command
    assert "--no-protect-prior-from-densify" in command
    assert "--save-initial-snapshot" in command
    assert "--initial-render-sets" in command
    assert "--seed" in command
    assert "19" in command
    assert "--camera-order-seed" in command
    assert "23" in command
    assert "--no-camera-shuffle" in command
    assert "--deterministic" in command
    assert str(prior_spec_json) in command


def test_backend_config_from_payload_parses_artifacts(tmp_path: Path) -> None:
    config = Vanilla3DGSBackendConfig.from_payload(
        {
            "repo_path": str(tmp_path / "repo"),
            "source_path": str(tmp_path / "scene"),
            "model_path": str(tmp_path / "output"),
            "prior_protection_mode": "freeze",
            "prior_lr_scale": 0.01,
            "prior_sh_reset_mode": "zero_all",
            "prior_target_total_gaussians": 50000,
            "prior_subsample_seed": 9,
            "sfm_region_replacement_mode": "aligned_prior_aabb_union",
            "sfm_region_margin_scale": 1.2,
            "sfm_region_margin_min_m": 0.03,
            "geometry_validation_outside_scene_proxy_ratio_threshold": 0.015,
            "geometry_validation_mean_nn_threshold_m": 0.35,
            "geometry_validation_max_prior_points": 4096,
            "geometry_validation_max_scene_points": 16384,
            "protect_prior_from_prune": False,
            "protect_prior_from_densify": True,
            "seed": 13,
            "camera_order_seed": 17,
            "camera_shuffle_enabled": False,
            "deterministic": True,
        },
        root=tmp_path,
        trainer_payload={"iterations": 15000},
        artifacts_payload={
            "save_initial_snapshot": True,
            "initial_render_sets": ["test"],
        },
    )

    assert config.iterations == 15000
    assert config.save_initial_snapshot is True
    assert config.initial_render_sets == ("test",)
    assert config.prior_protection_mode == "freeze"
    assert config.prior_lr_scale == 0.01
    assert config.prior_sh_reset_mode == "zero_all"
    assert config.prior_target_total_gaussians == 50000
    assert config.prior_subsample_seed == 9
    assert config.sfm_region_replacement_mode == "aligned_prior_aabb_union"
    assert config.sfm_region_margin_scale == 1.2
    assert config.sfm_region_margin_min_m == 0.03
    assert config.geometry_validation_outside_scene_proxy_ratio_threshold == 0.015
    assert config.geometry_validation_mean_nn_threshold_m == 0.35
    assert config.geometry_validation_max_prior_points == 4096
    assert config.geometry_validation_max_scene_points == 16384
    assert config.protect_prior_from_prune is False
    assert config.protect_prior_from_densify is True
    assert config.seed == 13
    assert config.camera_order_seed == 17
    assert config.camera_shuffle_enabled is False
    assert config.deterministic is True


def test_propagate_prior_runtime_args_copies_diagnostic_controls(tmp_path: Path) -> None:
    backend_module = _load_backend_module(tmp_path / "fake_repo")
    dataset = argparse.Namespace()
    args = argparse.Namespace(
        init_mode="merge",
        seed=31,
        camera_order_seed=37,
        camera_shuffle_enabled=False,
        deterministic=True,
        save_initial_snapshot=True,
        initial_render_sets=("test",),
        initial_snapshot_convert_shs_python=False,
        initial_snapshot_compute_cov3d_python=False,
        initial_snapshot_debug=False,
        initial_snapshot_antialiasing=False,
        prepared_init_plys=["/tmp/a.ply"],
        prepared_init_formats=["gaussian"],
        selected_priors_metadata=[{"aligned_prior": "/tmp/a.ply"}],
        prior_protection_mode="weak",
        prior_lr_scale=0.02,
        prior_sh_reset_mode="zero_all",
        prior_target_total_gaussians=25000,
        prior_subsample_seed=17,
        sfm_region_replacement_mode="aligned_prior_aabb_union",
        sfm_region_margin_scale=1.1,
        sfm_region_margin_min_m=0.05,
        geometry_validation_outside_scene_proxy_ratio_threshold=0.0125,
        geometry_validation_mean_nn_threshold_m=0.45,
        geometry_validation_max_prior_points=2048,
        geometry_validation_max_scene_points=8192,
        protect_prior_from_prune=True,
        protect_prior_from_densify=False,
    )

    backend_module.propagate_prior_runtime_args(dataset, args)

    assert dataset.seed == 31
    assert dataset.camera_order_seed == 37
    assert dataset.camera_shuffle_enabled is False
    assert dataset.deterministic is True
    assert dataset.prior_protection_mode == "weak"
    assert dataset.prior_lr_scale == 0.02
    assert dataset.prior_sh_reset_mode == "zero_all"
    assert dataset.prior_target_total_gaussians == 25000
    assert dataset.prior_subsample_seed == 17
    assert dataset.sfm_region_replacement_mode == "aligned_prior_aabb_union"
    assert dataset.sfm_region_margin_scale == 1.1
    assert dataset.sfm_region_margin_min_m == 0.05
    assert dataset.geometry_validation_outside_scene_proxy_ratio_threshold == 0.0125
    assert dataset.geometry_validation_mean_nn_threshold_m == 0.45
    assert dataset.geometry_validation_max_prior_points == 2048
    assert dataset.geometry_validation_max_scene_points == 8192
    assert dataset.protect_prior_from_prune is True
    assert dataset.protect_prior_from_densify is False


def test_resolve_determinism_settings_defaults_camera_order_seed_to_seed(tmp_path: Path) -> None:
    backend_module = _load_backend_module(tmp_path / "fake_repo")
    args = argparse.Namespace(seed=29, camera_order_seed=None, camera_shuffle_enabled=True, deterministic=False)

    resolved = backend_module.resolve_determinism_settings(args)

    assert resolved["seed"] == 29
    assert resolved["camera_order_seed"] == 29
    assert resolved["camera_shuffle_enabled"] is True
    assert resolved["deterministic"] is False


def test_shuffle_camera_infos_is_reproducible_and_locally_seeded(tmp_path: Path) -> None:
    backend_module = _load_backend_module(tmp_path / "fake_repo")
    train = list(range(8))
    test = list(range(4))

    first_train, first_test = backend_module.shuffle_camera_infos(
        train,
        test,
        enabled=True,
        camera_order_seed=11,
    )
    second_train, second_test = backend_module.shuffle_camera_infos(
        train,
        test,
        enabled=True,
        camera_order_seed=11,
    )
    disabled_train, disabled_test = backend_module.shuffle_camera_infos(
        train,
        test,
        enabled=False,
        camera_order_seed=11,
    )

    assert first_train == second_train
    assert first_test == second_test
    assert first_train != train
    assert disabled_train == train
    assert disabled_test == test


def test_resolve_selected_prior_metadata_items_preserves_gaussian_entry_order(tmp_path: Path) -> None:
    backend_module = _load_backend_module(tmp_path / "fake_repo")

    prepared_init_plys = ["/tmp/aligned_prior_00.ply", "/tmp/aligned_prior_01.ply", "/tmp/aligned_prior_02.ply"]
    prepared_init_formats = ["gaussian", "gaussian", "gaussian"]
    selected_priors_metadata = [
        {"prior_object_id": "replica_room_0_obj_6", "target_object_id": 6},
        {"prior_object_id": "replica_room_0_obj_9", "target_object_id": 9},
        {"prior_object_id": "replica_room_0_obj_74", "target_object_id": 74},
    ]

    resolved = backend_module.resolve_selected_prior_metadata_items(
        prepared_init_plys,
        prepared_init_formats,
        selected_priors_metadata,
    )

    assert [item["prior_object_id"] for item in resolved] == [
        "replica_room_0_obj_6",
        "replica_room_0_obj_9",
        "replica_room_0_obj_74",
    ]
    assert [item["target_object_id"] for item in resolved] == [6, 9, 74]


def test_resolve_selected_prior_metadata_items_falls_back_for_missing_entries(tmp_path: Path) -> None:
    backend_module = _load_backend_module(tmp_path / "fake_repo")

    prepared_init_plys = ["/tmp/aligned_prior_00.ply", "/tmp/aligned_prior_01.ply"]
    prepared_init_formats = ["gaussian", "pointcloud"]
    selected_priors_metadata = [{"prior_object_id": "replica_room_0_obj_6", "target_object_id": 6}]

    resolved = backend_module.resolve_selected_prior_metadata_items(
        prepared_init_plys,
        prepared_init_formats,
        selected_priors_metadata,
    )

    assert resolved[0]["prior_object_id"] == "replica_room_0_obj_6"
    assert resolved[1]["aligned_prior"] == "/tmp/aligned_prior_01.ply"
    assert resolved[1]["asset_format"] == "pointcloud"


def test_build_prior_group_summaries_tracks_survival_by_object(tmp_path: Path) -> None:
    backend_module = _load_backend_module(tmp_path / "fake_repo")

    gaussians = argparse.Namespace()
    gaussians._prior_point_mask = torch.tensor([True, True, False, True, False, False], dtype=torch.bool)
    gaussians._prior_group_ids = torch.tensor([0, 0, -1, 1, -1, -1], dtype=torch.int32)
    gaussians._prior_group_metadata = [
        {
            "prior_object_id": "replica_room_0_obj_6",
            "target_object_id": 6,
            "target_category": "lamp",
            "inserted_point_count": 3,
            "kept_point_count": 3,
        },
        {
            "prior_object_id": "replica_room_0_obj_9",
            "target_object_id": 9,
            "target_category": "sofa",
            "inserted_point_count": 2,
            "kept_point_count": 2,
        },
    ]

    summaries = backend_module.build_prior_group_summaries(gaussians)

    assert len(summaries) == 2
    assert summaries[0]["prior_object_id"] == "replica_room_0_obj_6"
    assert summaries[0]["inserted_point_count"] == 3
    assert summaries[0]["survived_point_count"] == 2
    assert summaries[0]["survival_ratio"] == 2 / 3
    assert summaries[1]["prior_object_id"] == "replica_room_0_obj_9"
    assert summaries[1]["inserted_point_count"] == 2
    assert summaries[1]["survived_point_count"] == 1
    assert summaries[1]["survival_ratio"] == 0.5


def test_validate_prior_geometry_against_scene_proxy_flags_floating_and_outside(tmp_path: Path) -> None:
    backend_module = _load_backend_module(tmp_path / "fake_repo")

    scene_xyz = np.asarray(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.5, 0.5, 1.0],
        ],
        dtype=np.float64,
    )
    prior_xyz = scene_xyz + np.asarray([0.0, 3.0, 0.0], dtype=np.float64)
    metadata_item = {
        "prior_object_id": "lamp_1",
        "target_object_id": 6,
        "alignment_debug": {
            "target_center": [0.5, 0.5, 0.5],
            "target_bottom_anchor": [0.5, 0.5, 0.0],
            "target_sizes": [1.0, 1.0, 1.0],
        },
    }

    validation = backend_module.validate_prior_geometry_against_scene_proxy(
        prior_xyz,
        scene_xyz,
        metadata_item,
        outside_ratio_threshold=0.01,
        mean_nn_threshold_m=0.5,
        max_prior_points=32,
        max_scene_points=32,
        seed=0,
    )

    assert validation["passed"] is False
    assert "outside_scene_proxy" in validation["fail_reasons"]
    assert "floating_from_scene_proxy" in validation["fail_reasons"]
    assert validation["outside_scene_proxy_ratio"] == 1.0
    assert validation["scene_proxy_mean_nn_distance_m"] > 2.0


def test_validate_prior_geometry_against_scene_proxy_accepts_nearby_prior(tmp_path: Path) -> None:
    backend_module = _load_backend_module(tmp_path / "fake_repo")

    scene_xyz = np.asarray(
        [
            [0.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [0.0, 2.0, 0.0],
            [2.0, 2.0, 0.0],
            [1.0, 1.0, 1.0],
            [1.0, 1.0, 2.0],
            [0.9, 0.9, 0.0],
            [1.1, 0.9, 0.0],
            [0.9, 1.1, 0.5],
            [1.1, 1.1, 0.5],
        ],
        dtype=np.float64,
    )
    prior_xyz = np.asarray(
        [
            [0.9, 0.9, 0.0],
            [1.1, 0.9, 0.0],
            [0.9, 1.1, 0.5],
            [1.1, 1.1, 0.5],
        ],
        dtype=np.float64,
    )
    metadata_item = {
        "prior_object_id": "chair_1",
        "target_object_id": 74,
        "alignment_debug": {
            "target_center": [1.0, 1.0, 0.25],
            "target_bottom_anchor": [1.0, 1.0, 0.0],
            "target_sizes": [0.2, 0.2, 0.5],
        },
    }

    validation = backend_module.validate_prior_geometry_against_scene_proxy(
        prior_xyz,
        scene_xyz,
        metadata_item,
        outside_ratio_threshold=0.01,
        mean_nn_threshold_m=0.5,
        max_prior_points=32,
        max_scene_points=32,
        seed=7,
    )

    assert validation["passed"] is True
    assert validation["fail_reasons"] == []
    assert validation["outside_scene_proxy_ratio"] == 0.0
    assert validation["scene_proxy_mean_nn_distance_m"] < 0.5
    assert validation["target_center_error_m"] < 0.3


def test_validate_prior_geometry_against_scene_proxy_flags_center_outside_with_low_outside_ratio(
    tmp_path: Path,
) -> None:
    backend_module = _load_backend_module(tmp_path / "fake_repo")

    scene_xyz = np.asarray(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
        ],
        dtype=np.float64,
    )
    mostly_inside = np.tile(np.asarray([[0.9, 0.5, 0.2]], dtype=np.float64), (100, 1))
    prior_xyz = np.concatenate(
        [
            mostly_inside,
            np.asarray([[1.2, 0.5, 0.2]], dtype=np.float64),
        ],
        axis=0,
    )
    metadata_item = {
        "alignment_debug": {
            "target_center": [1.05, 0.5, 0.2],
            "target_bottom_anchor": [1.05, 0.5, 0.2],
            "target_sizes": [0.3, 0.0, 0.0],
        }
    }

    validation = backend_module.validate_prior_geometry_against_scene_proxy(
        prior_xyz,
        scene_xyz,
        metadata_item,
        outside_ratio_threshold=0.01,
        mean_nn_threshold_m=0.5,
        max_prior_points=128,
        max_scene_points=128,
        seed=3,
    )

    assert validation["outside_scene_proxy_ratio"] < 0.01
    assert "outside_scene_proxy" not in validation["fail_reasons"]
    assert "outside_scene_proxy_center" in validation["fail_reasons"]
    assert "outside_scene_proxy_bottom" in validation["fail_reasons"]


def test_validate_prior_geometry_against_scene_proxy_flags_metadata_contradiction(tmp_path: Path) -> None:
    backend_module = _load_backend_module(tmp_path / "fake_repo")

    scene_xyz = np.asarray(
        [
            [0.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [0.0, 2.0, 0.0],
            [2.0, 2.0, 0.0],
            [1.0, 1.0, 2.0],
            [0.9, 0.9, 0.0],
            [1.1, 0.9, 0.0],
            [0.9, 1.1, 0.4],
            [1.1, 1.1, 0.4],
        ],
        dtype=np.float64,
    )
    prior_xyz = np.asarray(
        [
            [0.9, 0.9, 0.0],
            [1.1, 0.9, 0.0],
            [0.9, 1.1, 0.4],
            [1.1, 1.1, 0.4],
        ],
        dtype=np.float64,
    )
    metadata_item = {
        "alignment_debug": {
            "target_center": [1.3, 1.3, 0.4],
            "target_bottom_anchor": [1.3, 1.3, 0.1],
            "target_sizes": [0.5, 0.5, 0.7],
        }
    }

    validation = backend_module.validate_prior_geometry_against_scene_proxy(
        prior_xyz,
        scene_xyz,
        metadata_item,
        outside_ratio_threshold=0.05,
        mean_nn_threshold_m=0.5,
        max_prior_points=64,
        max_scene_points=64,
        seed=11,
    )

    assert validation["passed"] is False
    assert validation["fail_reasons"] == ["metadata_contradiction"]
    assert validation["target_center_error_m"] > 0.05
    assert validation["target_bottom_error_m"] > 0.05
    assert any(abs(delta) > 0.05 for delta in validation["target_size_delta"])
