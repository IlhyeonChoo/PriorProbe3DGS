#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import yaml

from priorprobe.prior_assets import build_prior_library


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize the prior-library manifest.")
    parser.add_argument("--config", required=True, type=Path, help="Path to prior YAML config.")
    args = parser.parse_args()

    config = load_yaml(resolve_path(str(args.config)))
    library = build_prior_library(config, root=ROOT)
    manifest_path = resolve_path(config["library"]["manifest_path"])
    library.dump_manifest(manifest_path)
    print(f"Prepared prior-library manifest at {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
