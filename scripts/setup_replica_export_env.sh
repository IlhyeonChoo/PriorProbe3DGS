#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
EXPORT_VENV="${EXPORT_VENV:-$ROOT_DIR/.venv-replica-export310}"

uv python install 3.10
uv venv --python 3.10 "$EXPORT_VENV"
uv pip install \
  --python "$EXPORT_VENV/bin/python" \
  --prerelease=allow \
  numpy \
  Pillow \
  plyfile \
  PyYAML \
  numpy-quaternion \
  habitat-sim

printf 'Replica export env ready at %s\n' "$EXPORT_VENV"
