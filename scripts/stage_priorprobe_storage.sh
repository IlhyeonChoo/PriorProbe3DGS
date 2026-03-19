#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HDD_ROOT="${1:-/mnt/hddg1/3dgs-data/priorprobe3dgs}"
SSD_ROOT="${2:-/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs}"

mkdir -p \
  "$HDD_ROOT/replica_dataset/raw" \
  "$HDD_ROOT/shapesplat_hf" \
  "$HDD_ROOT/shapesplat_extract" \
  "$SSD_ROOT/replica_colmap" \
  "$SSD_ROOT/shapesplat_stage"

if [ -d "$ROOT_DIR/data/_downloads/replica_dataset/raw" ]; then
  rsync -a "$ROOT_DIR/data/_downloads/replica_dataset/raw/" "$HDD_ROOT/replica_dataset/raw/"
fi

if [ -d "$ROOT_DIR/data/public_datasets/replica_colmap" ]; then
  rsync -a "$ROOT_DIR/data/public_datasets/replica_colmap/" "$SSD_ROOT/replica_colmap/"
fi

printf 'HDD root: %s\n' "$HDD_ROOT"
printf 'SSD root: %s\n' "$SSD_ROOT"
