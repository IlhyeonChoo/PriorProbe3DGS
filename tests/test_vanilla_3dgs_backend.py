from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.optimization.vanilla_3dgs import Vanilla3DGSBackendConfig, build_train_command


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
    assert "--save-initial-snapshot" in command
    assert "--initial-render-sets" in command
    assert str(prior_spec_json) in command


def test_backend_config_from_payload_parses_artifacts(tmp_path: Path) -> None:
    config = Vanilla3DGSBackendConfig.from_payload(
        {
            "repo_path": str(tmp_path / "repo"),
            "source_path": str(tmp_path / "scene"),
            "model_path": str(tmp_path / "output"),
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
