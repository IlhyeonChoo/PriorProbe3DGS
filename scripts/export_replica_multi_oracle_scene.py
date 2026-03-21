#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.replica_export import export_replica_multi_oracle_scene


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a Replica scene to COLMAP layout with scene-centric multi-object oracle metadata.")
    parser.add_argument("--scene-id", required=True, type=str)
    parser.add_argument("--categories", nargs="+", default=["chair", "sofa", "table", "lamp"])
    parser.add_argument("--max-objects", default=4, type=int)
    parser.add_argument("--raw-root", default=Path("data/_downloads/replica_dataset/raw"), type=Path)
    parser.add_argument("--output-root", default=Path("data/public_datasets/replica_colmap_multi"), type=Path)
    parser.add_argument("--width", default=512, type=int)
    parser.add_argument("--height", default=512, type=int)
    parser.add_argument("--hfov-deg", default=60.0, type=float)
    parser.add_argument("--train-views", default=80, type=int)
    parser.add_argument("--test-views", default=16, type=int)
    parser.add_argument("--mesh-point-count", default=100000, type=int)
    parser.add_argument("--seed", default=20260317, type=int)
    parser.add_argument("--radius-min", default=1.0, type=float)
    parser.add_argument("--radius-max", default=2.5, type=float)
    parser.add_argument("--min-visible-ratio", default=0.15, type=float)
    parser.add_argument(
        "--selection-mode",
        choices=["top_visibility", "diverse_azimuth"],
        default="top_visibility",
    )
    parser.add_argument("--azimuth-bin-count", default=8, type=int)
    parser.add_argument("--candidate-pose-count", type=int)
    parser.add_argument("--render-point-count", default=1000000, type=int)
    args = parser.parse_args()

    scene_root = export_replica_multi_oracle_scene(
        raw_root=resolve_path(args.raw_root),
        output_root=resolve_path(args.output_root),
        scene_id=args.scene_id,
        categories=list(args.categories),
        max_objects=args.max_objects,
        width=args.width,
        height=args.height,
        hfov_deg=args.hfov_deg,
        train_views=args.train_views,
        test_views=args.test_views,
        mesh_point_count=args.mesh_point_count,
        seed=args.seed,
        radius_min=args.radius_min,
        radius_max=args.radius_max,
        min_visible_ratio=args.min_visible_ratio,
        selection_mode=args.selection_mode,
        azimuth_bin_count=args.azimuth_bin_count,
        candidate_pose_count=args.candidate_pose_count,
        render_point_count=args.render_point_count,
    )
    print(scene_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
