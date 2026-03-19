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

from priorprobe.datasets import load_dataset_spec, resolve_dataset_scene, validate_scene_layout


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve and optionally validate a dataset scene config.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--scene-id", type=str)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    spec = load_dataset_spec(config_path, root=ROOT)
    scene = resolve_dataset_scene(
        spec,
        scene_id=args.scene_id,
        root_override=(args.root if args.root is None or args.root.is_absolute() else ROOT / args.root),
    )

    payload = {
        "dataset_name": scene.dataset_name,
        "scene_id": scene.scene_id,
        "format": scene.format,
        "source_path": str(scene.source_path),
        "images": scene.images,
        "depths": scene.depths,
        "eval": scene.eval,
        "white_background": scene.white_background,
        "notes": list(scene.notes),
    }

    if args.check:
        ok, messages = validate_scene_layout(scene)
        payload["valid"] = ok
        payload["messages"] = messages
        print(json.dumps(payload, indent=2))
        return 0 if ok else 1

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
