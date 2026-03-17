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

from priorprobe.prior_library.library import PriorEntry, PriorLibrary
from priorprobe.prior_library.metadata import PriorMetadata


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description="Add a domain object to the prior-library manifest.")
    parser.add_argument("--config", required=True, type=Path, help="Path to prior YAML config.")
    parser.add_argument("--object-id", required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("--gaussian-path", required=True)
    parser.add_argument("--feature-path")
    parser.add_argument("--scale", nargs=3, type=float, metavar=("SX", "SY", "SZ"))
    parser.add_argument("--tag", action="append", dest="tags", default=[])
    parser.add_argument("--source", default="domain_incremental")
    args = parser.parse_args()

    config = load_yaml(resolve_path(str(args.config)))
    manifest_path = resolve_path(config["library"]["manifest_path"])
    library = PriorLibrary.load_manifest(manifest_path) if manifest_path.exists() else PriorLibrary()
    metadata = PriorMetadata(
        category=args.category,
        source=args.source,
        scale_meters=tuple(args.scale) if args.scale else None,
        tags=tuple(args.tags),
    )
    library.add_entry(
        PriorEntry(
            object_id=args.object_id,
            category=args.category,
            gaussian_path=Path(args.gaussian_path),
            feature_path=Path(args.feature_path) if args.feature_path else None,
            metadata=metadata,
        )
    )
    library.dump_manifest(manifest_path)
    print(f"Added {args.object_id} to {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
