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

from priorprobe.oracle_features import build_oracle_query_features


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build oracle query features from saved crop directories.")
    parser.add_argument("--scene-root", required=True, type=Path)
    parser.add_argument("--feature-backend", required=True, choices=["mean_rgb", "clip", "clip_geom"])
    parser.add_argument("--model-name", type=str, default="ViT-B-32")
    parser.add_argument("--pretrained", type=str, default="laion2b_s34b_b79k")
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--render-count", type=int, default=8)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    outputs = build_oracle_query_features(
        resolve_path(args.scene_root),
        backend=args.feature_backend,
        model_name=args.model_name,
        pretrained=args.pretrained,
        device=args.device,
        render_count=args.render_count,
        overwrite=args.overwrite,
    )
    print(json.dumps([str(path) for path in outputs], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
