from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.datasets import validate_scene_layout


class SceneStub:
    def __init__(self, source_path: Path, images: str = "images", fmt: str = "colmap") -> None:
        self.source_path = source_path
        self.images = images
        self.format = fmt


def test_validate_scene_layout_requires_actual_images_and_sparse_files(tmp_path: Path) -> None:
    scene_root = tmp_path / "scene"
    (scene_root / "images").mkdir(parents=True)
    (scene_root / "sparse" / "0").mkdir(parents=True)

    valid, messages = validate_scene_layout(SceneStub(scene_root))

    assert valid is False
    assert any("missing image files" in message for message in messages)
    assert any("missing cameras.bin or cameras.txt" in message for message in messages)


def test_validate_scene_layout_accepts_minimal_colmap_scene(tmp_path: Path) -> None:
    scene_root = tmp_path / "scene"
    images_dir = scene_root / "images"
    sparse_dir = scene_root / "sparse" / "0"
    images_dir.mkdir(parents=True)
    sparse_dir.mkdir(parents=True)
    (images_dir / "0001.png").write_bytes(b"not-a-real-png")
    for filename in ("cameras.txt", "images.txt", "points3D.txt"):
        (sparse_dir / filename).write_text("# placeholder", encoding="utf-8")

    valid, messages = validate_scene_layout(SceneStub(scene_root))

    assert valid is True
    assert messages == []
