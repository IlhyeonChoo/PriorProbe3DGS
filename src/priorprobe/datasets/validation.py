from __future__ import annotations

from pathlib import Path


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
COLMAP_REQUIRED_PREFIXES = ("cameras", "images", "points3D")
COLMAP_ALLOWED_SUFFIXES = (".bin", ".txt")


def _has_image_files(images_dir: Path) -> bool:
    return any(path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES for path in images_dir.iterdir())


def _missing_colmap_files(sparse_dir: Path) -> list[str]:
    missing: list[str] = []
    for prefix in COLMAP_REQUIRED_PREFIXES:
        if not any((sparse_dir / f"{prefix}{suffix}").exists() for suffix in COLMAP_ALLOWED_SUFFIXES):
            missing.append(prefix)
    return missing


def validate_scene_layout(scene) -> tuple[bool, list[str]]:
    messages: list[str] = []
    if not scene.source_path.exists():
        messages.append(f"missing scene root: {scene.source_path}")
        return False, messages

    if scene.format == "blender":
        transforms_train = scene.source_path / "transforms_train.json"
        if not transforms_train.exists():
            messages.append(f"missing transforms_train.json: {transforms_train}")
        return not messages, messages

    sparse_dir = scene.source_path / "sparse" / "0"
    if not sparse_dir.exists():
        messages.append(f"missing sparse/0: {sparse_dir}")
    else:
        missing_files = _missing_colmap_files(sparse_dir)
        for prefix in missing_files:
            messages.append(f"missing {prefix}.bin or {prefix}.txt in {sparse_dir}")

    images_dir = scene.source_path / scene.images
    if not images_dir.exists():
        messages.append(f"missing images dir: {images_dir}")
    elif not _has_image_files(images_dir):
        messages.append(f"missing image files in {images_dir}")

    return not messages, messages
