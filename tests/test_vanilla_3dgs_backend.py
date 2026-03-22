from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

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
        protect_prior_from_prune=True,
        protect_prior_from_densify=False,
        save_initial_snapshot=True,
        initial_render_sets=("train", "test"),
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
    assert "--protect-prior-from-prune" in command
    assert "--no-protect-prior-from-densify" in command
    assert "--save-initial-snapshot" in command
    assert "--initial-render-sets" in command
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
            "protect_prior_from_prune": False,
            "protect_prior_from_densify": True,
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
    assert config.protect_prior_from_prune is False
    assert config.protect_prior_from_densify is True


def test_propagate_prior_runtime_args_copies_diagnostic_controls(tmp_path: Path) -> None:
    backend_module = _load_backend_module(tmp_path / "fake_repo")
    dataset = argparse.Namespace()
    args = argparse.Namespace(
        init_mode="merge",
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
        protect_prior_from_prune=True,
        protect_prior_from_densify=False,
    )

    backend_module.propagate_prior_runtime_args(dataset, args)

    assert dataset.prior_protection_mode == "weak"
    assert dataset.prior_lr_scale == 0.02
    assert dataset.prior_sh_reset_mode == "zero_all"
    assert dataset.prior_target_total_gaussians == 25000
    assert dataset.prior_subsample_seed == 17
    assert dataset.sfm_region_replacement_mode == "aligned_prior_aabb_union"
    assert dataset.sfm_region_margin_scale == 1.1
    assert dataset.sfm_region_margin_min_m == 0.05
    assert dataset.protect_prior_from_prune is True
    assert dataset.protect_prior_from_densify is False
