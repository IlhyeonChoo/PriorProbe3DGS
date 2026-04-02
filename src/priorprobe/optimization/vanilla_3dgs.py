from __future__ import annotations

import json
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[3]
WRAPPER_SCRIPT = PROJECT_ROOT / "scripts" / "train_vanilla_3dgs_backend.py"


def _as_tuple(values: Sequence[int] | None) -> tuple[int, ...]:
    if not values:
        return ()
    return tuple(int(value) for value in values)


def _as_str_tuple(values: Sequence[str] | None) -> tuple[str, ...]:
    if not values:
        return ()
    return tuple(str(value) for value in values)


@dataclass(slots=True)
class Vanilla3DGSBackendConfig:
    repo_path: Path
    source_path: Path
    model_path: Path
    python_executable: Path | None = None
    images: str = "images"
    depths: str = ""
    sh_degree: int = 3
    iterations: int = 30_000
    test_iterations: tuple[int, ...] = ()
    save_iterations: tuple[int, ...] = ()
    checkpoint_iterations: tuple[int, ...] = ()
    disable_viewer: bool = True
    white_background: bool = False
    eval: bool = False
    quiet: bool = False
    dry_run: bool = False
    init_mode: str = "merge"
    prior_protection_mode: str = "none"
    prior_lr_scale: float = 0.05
    protect_prior_from_prune: bool = True
    protect_prior_from_densify: bool = True
    prior_sh_reset_mode: str = "none"
    prior_target_total_gaussians: int = 0
    prior_subsample_seed: int = 42
    sfm_region_replacement_mode: str = "none"
    sfm_region_margin_scale: float = 1.05
    sfm_region_margin_min_m: float = 0.02
    save_initial_snapshot: bool = False
    initial_render_sets: tuple[str, ...] = ()
    seed: int = 42
    camera_order_seed: int | None = None
    camera_shuffle_enabled: bool = True
    deterministic: bool = False
    extra_args: tuple[str, ...] = ()

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        *,
        root: Path,
        trainer_payload: dict[str, Any] | None = None,
        artifacts_payload: dict[str, Any] | None = None,
        source_override: Path | None = None,
        model_override: Path | None = None,
        dry_run_override: bool | None = None,
    ) -> "Vanilla3DGSBackendConfig":
        trainer_payload = trainer_payload or {}
        artifacts_payload = artifacts_payload or {}

        def resolve_path(path_value: str | None) -> Path | None:
            if path_value is None:
                return None
            path = Path(path_value)
            return path if path.is_absolute() else root / path

        repo_path = resolve_path(payload.get("repo_path")) or (root / ".." / "3DGS" / "gaussian-splatting").resolve()
        source_path = source_override or resolve_path(payload.get("source_path"))
        model_path = model_override or resolve_path(payload.get("model_path"))
        if source_path is None:
            raise ValueError("backend.source_path is required for vanilla_3dgs experiments")
        if model_path is None:
            raise ValueError("backend.model_path is required for vanilla_3dgs experiments")

        python_executable = resolve_path(payload.get("python_executable"))
        iterations = int(trainer_payload.get("iterations", trainer_payload.get("max_steps", payload.get("iterations", 30_000))))
        sh_degree = int(trainer_payload.get("sh_degree", payload.get("sh_degree", 3)))
        test_iterations = _as_tuple(trainer_payload.get("test_iterations", payload.get("test_iterations")))
        save_iterations = _as_tuple(trainer_payload.get("save_iterations", payload.get("save_iterations")))
        checkpoint_iterations = _as_tuple(
            trainer_payload.get("checkpoint_iterations", payload.get("checkpoint_iterations"))
        )

        dry_run = bool(payload.get("dry_run", False))
        if dry_run_override is not None:
            dry_run = dry_run_override

        return cls(
            repo_path=repo_path.resolve(),
            source_path=source_path.resolve(),
            model_path=model_path.resolve(),
            python_executable=python_executable if python_executable else None,
            images=str(payload.get("images", "images")),
            depths=str(payload.get("depths", "")),
            sh_degree=sh_degree,
            iterations=iterations,
            test_iterations=test_iterations,
            save_iterations=save_iterations,
            checkpoint_iterations=checkpoint_iterations,
            disable_viewer=bool(payload.get("disable_viewer", True)),
            white_background=bool(payload.get("white_background", False)),
            eval=bool(payload.get("eval", False)),
            quiet=bool(payload.get("quiet", False)),
            dry_run=dry_run,
            init_mode=str(payload.get("init_mode", "merge")),
            prior_protection_mode=str(payload.get("prior_protection_mode", "none")),
            prior_lr_scale=float(payload.get("prior_lr_scale", 0.05)),
            protect_prior_from_prune=bool(payload.get("protect_prior_from_prune", True)),
            protect_prior_from_densify=bool(payload.get("protect_prior_from_densify", True)),
            prior_sh_reset_mode=str(payload.get("prior_sh_reset_mode", "none")),
            prior_target_total_gaussians=int(payload.get("prior_target_total_gaussians", 0)),
            prior_subsample_seed=int(payload.get("prior_subsample_seed", 42)),
            sfm_region_replacement_mode=str(payload.get("sfm_region_replacement_mode", "none")),
            sfm_region_margin_scale=float(payload.get("sfm_region_margin_scale", 1.05)),
            sfm_region_margin_min_m=float(payload.get("sfm_region_margin_min_m", 0.02)),
            save_initial_snapshot=bool(artifacts_payload.get("save_initial_snapshot", False)),
            initial_render_sets=_as_str_tuple(artifacts_payload.get("initial_render_sets")),
            seed=int(payload.get("seed", 42)),
            camera_order_seed=(
                int(payload["camera_order_seed"])
                if payload.get("camera_order_seed") is not None
                else None
            ),
            camera_shuffle_enabled=bool(payload.get("camera_shuffle_enabled", True)),
            deterministic=bool(payload.get("deterministic", False)),
            extra_args=_as_str_tuple(payload.get("extra_args")),
        )


def resolve_backend_python(config: Vanilla3DGSBackendConfig) -> Path:
    if config.python_executable is not None:
        return config.python_executable

    candidate = config.repo_path / "venv" / "bin" / "python"
    if candidate.exists():
        return candidate
    return Path(sys.executable)


def build_train_command(
    config: Vanilla3DGSBackendConfig,
    *,
    prior_ply: Path | None = None,
    alignment_json: Path | None = None,
    prior_object_id: str | None = None,
    prior_score: float | None = None,
    prior_spec_json: Path | None = None,
) -> list[str]:
    command = [
        str(resolve_backend_python(config)),
        str(WRAPPER_SCRIPT),
        "--repo-path",
        str(config.repo_path),
        "--source_path",
        str(config.source_path),
        "--model_path",
        str(config.model_path),
        "--images",
        config.images,
        "--sh_degree",
        str(config.sh_degree),
        "--iterations",
        str(config.iterations),
    ]

    if config.depths:
        command.extend(["--depths", config.depths])

    for flag, values in (
        ("--test_iterations", config.test_iterations),
        ("--save_iterations", config.save_iterations),
        ("--checkpoint_iterations", config.checkpoint_iterations),
    ):
        if values:
            command.append(flag)
            command.extend(str(value) for value in values)

    if config.disable_viewer:
        command.append("--disable_viewer")
    if config.white_background:
        command.append("--white_background")
    if config.eval:
        command.append("--eval")
    if config.quiet:
        command.append("--quiet")
    if config.save_initial_snapshot:
        command.append("--save-initial-snapshot")
    if config.initial_render_sets:
        command.append("--initial-render-sets")
        command.extend(config.initial_render_sets)
    command.extend(["--seed", str(config.seed)])
    if config.camera_order_seed is not None:
        command.extend(["--camera-order-seed", str(config.camera_order_seed)])
    command.append("--camera-shuffle" if config.camera_shuffle_enabled else "--no-camera-shuffle")
    if config.deterministic:
        command.append("--deterministic")

    if prior_ply is not None:
        command.extend(["--prior-ply", str(prior_ply)])
        command.extend(["--init-mode", config.init_mode])
    elif prior_spec_json is not None:
        command.extend(["--init-mode", config.init_mode])
    if prior_ply is not None or prior_spec_json is not None:
        command.extend(["--prior-protection-mode", config.prior_protection_mode])
        command.extend(["--prior-lr-scale", str(config.prior_lr_scale)])
        command.extend(["--prior-sh-reset-mode", config.prior_sh_reset_mode])
        command.extend(["--prior-target-total-gaussians", str(config.prior_target_total_gaussians)])
        command.extend(["--prior-subsample-seed", str(config.prior_subsample_seed)])
        command.extend(["--sfm-region-replacement-mode", config.sfm_region_replacement_mode])
        command.extend(["--sfm-region-margin-scale", str(config.sfm_region_margin_scale)])
        command.extend(["--sfm-region-margin-min-m", str(config.sfm_region_margin_min_m)])
        command.append(
            "--protect-prior-from-prune"
            if config.protect_prior_from_prune
            else "--no-protect-prior-from-prune"
        )
        command.append(
            "--protect-prior-from-densify"
            if config.protect_prior_from_densify
            else "--no-protect-prior-from-densify"
        )
    if alignment_json is not None:
        command.extend(["--alignment-json", str(alignment_json)])
    if prior_object_id is not None:
        command.extend(["--prior-object-id", prior_object_id])
    if prior_score is not None:
        command.extend(["--prior-score", str(prior_score)])
    if prior_spec_json is not None:
        command.extend(["--prior-spec-json", str(prior_spec_json)])

    command.extend(config.extra_args)
    return command


def command_to_string(command: Sequence[str]) -> str:
    return shlex.join(str(part) for part in command)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def run_command(
    command: Sequence[str],
    *,
    workdir: Path,
    stdout_path: Path,
    stderr_path: Path,
) -> tuple[int, float]:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    start_time = time.perf_counter()
    with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open("w", encoding="utf-8") as stderr_file:
        completed = subprocess.run(
            list(command),
            cwd=str(workdir),
            stdout=stdout_file,
            stderr=stderr_file,
            check=False,
        )
    elapsed = time.perf_counter() - start_time
    return completed.returncode, elapsed
