#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

from huggingface_hub.errors import GatedRepoError
from huggingface_hub import snapshot_download


ROOT = Path(__file__).resolve().parents[1]


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download a gated/public ShapeSplat snapshot subset from Hugging Face."
    )
    parser.add_argument("--repo-id", required=True, type=str, help="Hugging Face repo id, e.g. org/dataset_name")
    parser.add_argument("--repo-type", default="dataset", choices=["dataset", "model", "space"])
    parser.add_argument("--output-dir", default=Path("data/_downloads/shapesplat_hf"), type=Path)
    parser.add_argument("--revision", type=str, help="Optional revision or branch.")
    parser.add_argument(
        "--allow-pattern",
        action="append",
        default=[],
        help="Optional glob to restrict download. Repeat for multiple patterns.",
    )
    parser.add_argument(
        "--ignore-pattern",
        action="append",
        default=[],
        help="Optional glob to skip. Repeat for multiple patterns.",
    )
    parser.add_argument(
        "--token-env",
        default="HF_TOKEN",
        type=str,
        help="Environment variable carrying a Hugging Face access token.",
    )
    args = parser.parse_args()

    token = os.environ.get(args.token_env)
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        local_dir = snapshot_download(
            repo_id=args.repo_id,
            repo_type=args.repo_type,
            revision=args.revision,
            allow_patterns=args.allow_pattern or None,
            ignore_patterns=args.ignore_pattern or None,
            token=token,
            local_dir=str(output_dir / args.repo_id.replace("/", "__")),
            local_dir_use_symlinks=False,
        )
    except GatedRepoError as exc:
        message = str(exc)
        if "public gated repositories" in message:
            raise SystemExit(
                "Hugging Face token is valid, but it cannot read public gated repositories. "
                "Enable public-gated access in the token settings or use a token with that permission."
            ) from exc
        raise SystemExit(
            "Hugging Face account/token does not currently have access to this gated ShapeSplat repository."
        ) from exc
    print(local_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
