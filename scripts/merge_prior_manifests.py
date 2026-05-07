#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.prior_library.library import PriorLibrary
from priorprobe.runtime_paths import to_repo_relative_path


def resolve_path(path_value: Path) -> Path:
    return path_value if path_value.is_absolute() else ROOT / path_value


def build_minimal_prior_config(*, manifest_path: Path) -> dict[str, object]:
    return {
        "library": {
            "name": manifest_path.stem,
            "source": "merged_prior_library",
            "manifest_path": to_repo_relative_path(manifest_path, root=ROOT),
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge multiple prior-library manifests.")
    parser.add_argument("--manifest", action="append", required=True, type=Path, help="Input manifest path.")
    parser.add_argument("--manifest-out", required=True, type=Path, help="Merged manifest path.")
    parser.add_argument("--config-out", type=Path, help="Optional minimal prior-config YAML path.")
    args = parser.parse_args()

    merged = PriorLibrary()
    sources: list[str] = []
    for manifest_arg in args.manifest:
        manifest_path = resolve_path(manifest_arg)
        library = PriorLibrary.load_manifest(manifest_path)
        sources.append(str(manifest_path))
        for entry in library.list_entries():
            merged.add_entry(entry)

    manifest_out = resolve_path(args.manifest_out)
    merged.dump_manifest(manifest_out)
    print(f"Merged {len(sources)} manifests into {manifest_out}")
    print(json.dumps({"sources": sources, "entry_count": len(merged.list_entries())}, indent=2))

    if args.config_out is not None:
        config_out = resolve_path(args.config_out)
        config_out.parent.mkdir(parents=True, exist_ok=True)
        config_out.write_text(
            yaml.safe_dump(build_minimal_prior_config(manifest_path=manifest_out), sort_keys=False),
            encoding="utf-8",
        )
        print(f"Wrote prior config to {config_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
