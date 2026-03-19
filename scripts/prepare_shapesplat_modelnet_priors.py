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

from priorprobe.shapesplat_modelnet import prepare_modelnet_prior_library


def resolve_path(path_value: Path) -> Path:
    return path_value if path_value.is_absolute() else (ROOT / path_value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a staged ShapeSplat ModelNet prior subset from category zip assets.")
    parser.add_argument("--zip-path", required=True, type=Path, help="Path to ModelNet ShapeSplat category zip.")
    parser.add_argument("--extract-root", required=True, type=Path, help="HDD root for extracted source priors.")
    parser.add_argument("--stage-root", required=True, type=Path, help="SSD root for staged priors and features.")
    parser.add_argument("--config-out", required=True, type=Path, help="YAML config path to generate.")
    parser.add_argument("--manifest-out", required=True, type=Path, help="Prior-library manifest path.")
    parser.add_argument("--category", type=str, default="chair")
    parser.add_argument("--split", type=str, default="train")
    parser.add_argument("--max-objects", type=int, default=128)
    parser.add_argument("--num-views", type=int, default=8)
    parser.add_argument("--image-size", type=int, default=256)
    parser.add_argument("--point-limit", type=int, default=12000)
    parser.add_argument("--feature-backend", type=str, default="fallback")
    parser.add_argument("--feature-model-name", type=str, default="ViT-B-32")
    parser.add_argument("--feature-pretrained", type=str, default="laion2b_s34b_b79k")
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--allow-fallback", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    payload = prepare_modelnet_prior_library(
        zip_path=resolve_path(args.zip_path),
        extract_root=resolve_path(args.extract_root),
        stage_root=resolve_path(args.stage_root),
        config_out=resolve_path(args.config_out),
        manifest_out=resolve_path(args.manifest_out),
        category=args.category,
        split=args.split,
        max_objects=args.max_objects,
        num_views=args.num_views,
        image_size=args.image_size,
        point_limit=args.point_limit,
        overwrite=args.overwrite,
        feature_backend=args.feature_backend,
        feature_model_name=args.feature_model_name,
        feature_pretrained=args.feature_pretrained,
        allow_fallback=bool(args.allow_fallback),
        device=args.device,
        root=ROOT,
    )
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
