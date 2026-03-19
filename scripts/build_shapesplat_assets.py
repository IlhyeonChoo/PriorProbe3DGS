#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.prior_assets import load_yaml, resolve_path, stage_shapesplat_assets, summarize_staged_assets


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage a ShapeSplat asset subset and aggregate render features.")
    parser.add_argument("--config", required=True, type=Path, help="Path to ShapeSplat prior YAML config.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite staged assets and features.")
    args = parser.parse_args()

    config = load_yaml(resolve_path(ROOT, str(args.config)))
    results = stage_shapesplat_assets(config, root=ROOT, overwrite=args.overwrite)
    print(summarize_staged_assets(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
