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
    extra_args: tuple[str, ...] = ()

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        *,
        root: Path,
        trainer_payload: dict[str, Any] | None = None,
        source_override: Path | None = None,
        model_override: Path | None = None,
        dry_run_override: bool | None = None,
    ) -> "Vanilla3DGSBackendConfig":
        trainer_payload = trainer_payload or {}

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

    if prior_ply is not None:
        command.extend(["--prior-ply", str(prior_ply)])
    if alignment_json is not None:
        command.extend(["--alignment-json", str(alignment_json)])
    if prior_object_id is not None:
        command.extend(["--prior-object-id", prior_object_id])
    if prior_score is not None:
        command.extend(["--prior-score", str(prior_score)])

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
