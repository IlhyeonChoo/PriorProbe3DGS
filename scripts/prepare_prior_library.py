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


def build_library(config: dict) -> PriorLibrary:
    library = PriorLibrary()
    library_config = config["library"]
    for item in library_config.get("default_objects", []):
        metadata = PriorMetadata(
            category=item["category"],
            source=library_config.get("source", "unknown"),
            scale_meters=tuple(item["scale_meters"]) if item.get("scale_meters") else None,
            tags=tuple(item.get("tags", [])),
        )
        library.add_entry(
            PriorEntry(
                object_id=item["object_id"],
                category=item["category"],
                gaussian_path=Path(item["gaussian_path"]),
                feature_path=Path(item["feature_path"]) if item.get("feature_path") else None,
                metadata=metadata,
            )
        )
    return library


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize the prior-library manifest.")
    parser.add_argument("--config", required=True, type=Path, help="Path to prior YAML config.")
    args = parser.parse_args()

    config = load_yaml(resolve_path(str(args.config)))
    library = build_library(config)
    manifest_path = resolve_path(config["library"]["manifest_path"])
    library.dump_manifest(manifest_path)
    print(f"Prepared prior-library manifest at {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
