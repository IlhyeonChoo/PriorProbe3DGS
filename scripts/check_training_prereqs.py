#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.readiness import check_dataset_scene, check_prior_assets


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether priors and dataset scenes are ready for actual training.")
    parser.add_argument(
        "--prior-config",
        type=Path,
        default=Path("configs/priors/shapesplat.yaml"),
        help="Prior config to validate.",
    )
    parser.add_argument(
        "--dataset-config",
        action="append",
        type=Path,
        default=[],
        help="Dataset config(s) to validate. Defaults to Replica and ScanNet.",
    )
    parser.add_argument("--scene-id", type=str, help="Optional scene override. Use only with a single dataset-config.")
    parser.add_argument("--dataset-root", type=Path, help="Optional dataset root override for a single dataset-config.")
    parser.add_argument("--require-features", action="store_true", help="Treat missing retrieval features as blocking.")
    args = parser.parse_args()

    dataset_configs = args.dataset_config or [
        Path("configs/datasets/replica.yaml"),
        Path("configs/datasets/scannet.yaml"),
    ]
    if (args.scene_id is not None or args.dataset_root is not None) and len(dataset_configs) != 1:
        raise SystemExit("--scene-id and --dataset-root can only be used with a single --dataset-config.")

    prior_checks = check_prior_assets(
        resolve_path(args.prior_config),
        root=ROOT,
        require_features=args.require_features,
    )
    dataset_checks = [
        check_dataset_scene(
            resolve_path(config_path),
            root=ROOT,
            scene_id=args.scene_id,
            root_override=(resolve_path(args.dataset_root) if args.dataset_root else None),
        )
        for config_path in dataset_configs
    ]

    payload = {
        "ready": all(check.ready for check in prior_checks) and all(check.ready for check in dataset_checks),
        "prior_checks": [check.to_dict() for check in prior_checks],
        "dataset_checks": [check.to_dict() for check in dataset_checks],
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
