#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


DEFAULT_EXPERIMENTS = [
    "configs/experiments/gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_15000.yaml",
    "configs/experiments/gaussian_direct_same_scene_exact_clip_15000.yaml",
    "configs/experiments/gaussian_direct_merged_oracle_select_clip_15000.yaml",
    "configs/experiments/gaussian_direct_merged_clip_retrieval_15000.yaml",
    "configs/experiments/gaussian_direct_existing_clip_only_15000.yaml",
]

SMOKE_EXPERIMENTS = [
    "configs/experiments/gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_smoke_1000.yaml",
    "configs/experiments/gaussian_direct_same_scene_exact_clip_smoke_1000.yaml",
    "configs/experiments/gaussian_direct_merged_oracle_select_clip_smoke_1000.yaml",
    "configs/experiments/gaussian_direct_merged_clip_retrieval_smoke_1000.yaml",
    "configs/experiments/gaussian_direct_existing_clip_only_smoke_1000.yaml",
]


def resolve_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


def run_command(command: list[str]) -> None:
    print("$", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare and run the Replica gaussian-direct upper-bound study.")
    parser.add_argument("--scene-id", action="append", dest="scene_ids")
    parser.add_argument("--skip-prepare", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--smoke", action="store_true", help="Run the 1000-iteration smoke experiment set.")
    parser.add_argument("--python", type=Path, default=Path(".venv/bin/python"))
    args = parser.parse_args()

    python_executable = str(resolve_path(args.python))
    scene_ids = list(args.scene_ids or ["room_0", "office_0"])
    experiment_configs = SMOKE_EXPERIMENTS if args.smoke else DEFAULT_EXPERIMENTS

    if not args.skip_prepare:
        prepare_command = [
            python_executable,
            "scripts/prepare_replica_exact_target_priors.py",
        ]
        for scene_id in scene_ids:
            prepare_command.extend(["--scene-id", scene_id])
        run_command(prepare_command)

        run_command(
            [
                python_executable,
                "scripts/merge_prior_manifests.py",
                "--manifest",
                "outputs/gaussian_direct/prior_library/replica_target_exact_clip_manifest.json",
                "--manifest",
                "outputs/gaussian_direct/prior_library/shapesplat_modelnet_bundle_clip_manifest.json",
                "--manifest-out",
                "outputs/gaussian_direct/prior_library/replica_target_exact_plus_shapesplat_clip_manifest.json",
                "--config-out",
                "outputs/gaussian_direct/prior_library/replica_target_exact_plus_shapesplat_clip.yaml",
            ]
        )

    for experiment_config in experiment_configs:
        for scene_id in scene_ids:
            command = [
                python_executable,
                "scripts/run_experiment.py",
                "--config",
                experiment_config,
                "--dataset-scene-id",
                scene_id,
            ]
            if args.dry_run:
                command.append("--dry-run")
            run_command(command)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
