#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import yaml

from priorprobe.datasets import load_dataset_spec, resolve_dataset_scene, validate_scene_layout
from priorprobe.evaluation.metrics import summarize_run
from priorprobe.insertion.aligner import PriorAligner
from priorprobe.optimization.trainer import PriorProbeTrainer
from priorprobe.optimization.vanilla_3dgs import (
    Vanilla3DGSBackendConfig,
    build_train_command,
    command_to_string,
    run_command,
    write_json,
)
from priorprobe.prior_library.library import PriorLibrary
from priorprobe.retrieval.retriever import PriorRetriever, RetrievalResult


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def resolve_path(path_str: str | None) -> Path | None:
    if path_str is None:
        return None
    path = Path(path_str)
    return path if path.is_absolute() else ROOT / path


def resolve_override(path_value: Path | None) -> Path | None:
    if path_value is None:
        return None
    return path_value if path_value.is_absolute() else ROOT / path_value


def is_placeholder_path(path_value: str | None) -> bool:
    if path_value is None:
        return True
    normalized = str(path_value).strip()
    if not normalized:
        return True
    return normalized.startswith("/path/to/") or normalized.startswith("CHANGE_ME")


def load_dataset_scene(
    config: dict[str, Any],
    *,
    scene_id_override: str | None,
    root_override: Path | None,
) -> Any | None:
    dataset_config_path = resolve_path(config["experiment"].get("dataset_config"))
    if dataset_config_path is None or not dataset_config_path.exists():
        return None

    spec = load_dataset_spec(dataset_config_path, root=ROOT)
    return resolve_dataset_scene(spec, scene_id=scene_id_override, root_override=root_override)


def write_evaluation(experiment_name: str, payload: dict[str, Any]) -> Path:
    output_path = ROOT / "outputs" / "experiments" / experiment_name / "evaluation.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def run_placeholder_experiment(config: dict[str, Any]) -> int:
    experiment = config["experiment"]
    trainer_config = config["trainer"]
    target_quality = trainer_config.get("target_quality", {})

    trainer = PriorProbeTrainer(output_root=ROOT / "outputs")
    retrieval_score = None
    alignment_score = None

    if experiment["initialization"] == "from_scratch":
        run = trainer.run_from_scratch(
            experiment_name=experiment["name"],
            steps=trainer_config["max_steps"],
            target_metric=target_quality.get("metric"),
            target_value=target_quality.get("value"),
        )
    else:
        prior_config = load_yaml(resolve_path(experiment["prior_config"]))
        manifest_path = resolve_path(prior_config["library"]["manifest_path"])
        if manifest_path is None or not manifest_path.exists():
            raise SystemExit("Prior manifest is missing. Run scripts/prepare_prior_library.py first.")

        library = PriorLibrary.load_manifest(manifest_path)
        retriever = PriorRetriever(library)
        oracle_object_id = experiment.get("prior_object_id") if experiment["retrieval_mode"] == "oracle" else None
        retrieval_results = retriever.retrieve(top_k=1, oracle_object_id=oracle_object_id)
        if not retrieval_results:
            raise SystemExit("No prior candidates were found.")

        selected = retrieval_results[0]
        aligner = PriorAligner()
        alignment = aligner.align(
            selected.object_id,
            oracle=experiment["alignment_mode"] == "oracle",
        )
        retrieval_score = selected.score
        alignment_score = alignment.score
        run = trainer.run_with_prior(
            experiment_name=experiment["name"],
            prior_object_id=selected.object_id,
            steps=trainer_config["max_steps"],
            alignment_mode=alignment.mode,
            adaptation=experiment["adaptation"],
            target_metric=target_quality.get("metric"),
            target_value=target_quality.get("value"),
        )

    run_path = trainer.save_run(run)
    evaluation = summarize_run(
        run,
        retrieval_score=retrieval_score,
        alignment_score=alignment_score,
    )
    evaluation_path = write_evaluation(experiment["name"], evaluation.to_dict())
    print(f"Saved run summary to {run_path}")
    print(f"Saved evaluation to {evaluation_path}")
    return 0


def select_prior(config: dict[str, Any]) -> RetrievalResult:
    experiment = config["experiment"]
    prior_config_path = resolve_path(experiment["prior_config"])
    if prior_config_path is None:
        raise SystemExit("experiment.prior_config is required for prior-initialized runs.")

    prior_config = load_yaml(prior_config_path)
    manifest_path = resolve_path(prior_config["library"]["manifest_path"])
    if manifest_path is None or not manifest_path.exists():
        raise SystemExit("Prior manifest is missing. Run scripts/prepare_prior_library.py first.")

    library = PriorLibrary.load_manifest(manifest_path)
    retriever = PriorRetriever(library)
    oracle_object_id = experiment.get("prior_object_id") if experiment.get("retrieval_mode") == "oracle" else None
    retrieval_results = retriever.retrieve(top_k=1, oracle_object_id=oracle_object_id)
    if not retrieval_results:
        raise SystemExit("No prior candidates were found.")
    return retrieval_results[0]


def run_vanilla_3dgs_experiment(config: dict[str, Any], args: argparse.Namespace) -> int:
    experiment = config["experiment"]
    trainer_config = config.get("trainer", {})
    dataset_scene = load_dataset_scene(
        config,
        scene_id_override=args.dataset_scene_id,
        root_override=resolve_override(args.dataset_root),
    )
    backend_payload = dict(config.get("backend", {}))
    if dataset_scene is not None:
        if is_placeholder_path(backend_payload.get("source_path")) and args.backend_source_path is None:
            backend_payload["source_path"] = str(dataset_scene.source_path)
        backend_payload["images"] = dataset_scene.images
        backend_payload["depths"] = dataset_scene.depths
        backend_payload["eval"] = dataset_scene.eval
        backend_payload["white_background"] = dataset_scene.white_background
        if is_placeholder_path(backend_payload.get("model_path")) and args.backend_model_path is None:
            backend_payload["model_path"] = str(
                ROOT / "outputs" / "backend_runs" / experiment["name"] / dataset_scene.scene_id
            )

    backend_config = Vanilla3DGSBackendConfig.from_payload(
        backend_payload,
        root=ROOT,
        trainer_payload=trainer_config,
        source_override=resolve_override(args.backend_source_path),
        model_override=resolve_override(args.backend_model_path),
        dry_run_override=True if args.dry_run else None,
    )

    output_dir = ROOT / "outputs" / "experiments" / experiment["name"]
    output_dir.mkdir(parents=True, exist_ok=True)

    prior_alignment = config.get("prior_alignment", {})
    alignment_path = resolve_override(args.alignment_transform_path) or resolve_path(
        prior_alignment.get("transform_path")
    )
    selected_prior: RetrievalResult | None = None
    prior_ply: Path | None = None

    if experiment["initialization"] != "from_scratch":
        selected_prior = select_prior(config)
        prior_ply = resolve_path(str(selected_prior.gaussian_path))
        if prior_ply is None or not prior_ply.exists():
            raise SystemExit(f"Selected prior asset is missing: {selected_prior.gaussian_path}")
        if alignment_path is None:
            raise SystemExit("prior_alignment.transform_path is required for prior-initialized vanilla_3dgs runs.")
    if not backend_config.dry_run:
        if dataset_scene is not None:
            valid, messages = validate_scene_layout(dataset_scene)
            if not valid:
                formatted = "\n".join(f"- {message}" for message in messages)
                raise SystemExit(f"Dataset scene is not ready for vanilla_3dgs training:\n{formatted}")
        elif not backend_config.source_path.exists():
            raise SystemExit(f"Backend source_path does not exist: {backend_config.source_path}")

    command = build_train_command(
        backend_config,
        prior_ply=prior_ply,
        alignment_json=alignment_path,
        prior_object_id=selected_prior.object_id if selected_prior else None,
        prior_score=selected_prior.score if selected_prior else None,
    )

    metadata_path = output_dir / "backend_run.json"
    metadata = {
        "experiment_name": experiment["name"],
        "backend": "vanilla_3dgs",
        "initialization": experiment["initialization"],
        "status": "dry_run" if backend_config.dry_run else "pending",
        "repo_path": str(backend_config.repo_path),
        "source_path": str(backend_config.source_path),
        "model_path": str(backend_config.model_path),
        "dataset_scene": None,
        "command": command,
        "command_string": command_to_string(command),
        "alignment_json": str(alignment_path) if alignment_path else None,
        "selected_prior": None,
    }
    if dataset_scene is not None:
        metadata["dataset_scene"] = {
            "dataset_name": dataset_scene.dataset_name,
            "scene_id": dataset_scene.scene_id,
            "format": dataset_scene.format,
            "images": dataset_scene.images,
            "depths": dataset_scene.depths,
            "eval": dataset_scene.eval,
            "white_background": dataset_scene.white_background,
            "notes": list(dataset_scene.notes),
        }
    if selected_prior is not None:
        metadata["selected_prior"] = {
            "object_id": selected_prior.object_id,
            "score": selected_prior.score,
            "mode": selected_prior.mode,
            "gaussian_path": str(prior_ply),
            "category": selected_prior.category,
        }
    write_json(metadata_path, metadata)

    if backend_config.dry_run:
        print(f"Saved backend launch metadata to {metadata_path}")
        print(command_to_string(command))
        return 0

    stdout_path = output_dir / "backend_stdout.log"
    stderr_path = output_dir / "backend_stderr.log"
    return_code, elapsed = run_command(
        command,
        workdir=ROOT,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
    metadata.update(
        {
            "status": "completed" if return_code == 0 else "failed",
            "return_code": return_code,
            "elapsed_sec": elapsed,
            "stdout_log": str(stdout_path),
            "stderr_log": str(stderr_path),
        }
    )
    write_json(metadata_path, metadata)

    if return_code != 0:
        raise SystemExit(
            f"vanilla_3dgs backend failed with return code {return_code}. See {stderr_path}."
        )

    print(f"Saved backend launch metadata to {metadata_path}")
    print(f"Backend stdout log: {stdout_path}")
    print(f"Backend stderr log: {stderr_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a scaffold or backend-backed experiment.")
    parser.add_argument("--config", required=True, type=Path, help="Path to experiment YAML config.")
    parser.add_argument("--dataset-scene-id", type=str, help="Optional override for dataset scene_id.")
    parser.add_argument("--dataset-root", type=Path, help="Optional override for dataset root.")
    parser.add_argument("--backend-source-path", type=Path, help="Optional override for backend.source_path.")
    parser.add_argument("--backend-model-path", type=Path, help="Optional override for backend.model_path.")
    parser.add_argument(
        "--alignment-transform-path",
        type=Path,
        help="Optional override for prior_alignment.transform_path.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Build artifacts and commands without launching training.")
    args = parser.parse_args()

    config = load_yaml(resolve_path(str(args.config)))
    if config["experiment"].get("reconstruction_backend") == "vanilla_3dgs":
        return run_vanilla_3dgs_experiment(config, args)
    return run_placeholder_experiment(config)


if __name__ == "__main__":
    raise SystemExit(main())
