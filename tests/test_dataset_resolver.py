from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.datasets import load_dataset_spec, resolve_dataset_scene


def test_resolve_dataset_scene_uses_default_scene_and_inherited_fields(tmp_path: Path) -> None:
    config_path = tmp_path / "dataset.yaml"
    config_path.write_text(
        """
dataset:
  name: replica
  root: data/public_datasets/replica_colmap
  format: colmap
  default_scene_id: room_0
  images: images
  depths: ""
  eval: false
  white_background: false
  notes:
    - base note
  scenes:
    room_0:
      relative_path: room_0
      notes:
        - scene note
""".strip(),
        encoding="utf-8",
    )

    spec = load_dataset_spec(config_path, root=ROOT)
    scene = resolve_dataset_scene(spec)

    assert scene.dataset_name == "replica"
    assert scene.scene_id == "room_0"
    assert scene.source_path == (ROOT / "data/public_datasets/replica_colmap/room_0").resolve()
    assert scene.images == "images"
    assert scene.white_background is False
    assert scene.notes == ("base note", "scene note")


def test_resolve_dataset_scene_honors_root_override_for_scene_source_path(tmp_path: Path) -> None:
    config_path = tmp_path / "dataset.yaml"
    config_path.write_text(
        """
dataset:
  name: scannet
  root: data/public_datasets/scannet_colmap
  format: colmap
  default_scene_id: scene0000_00
  scenes:
    scene0000_00:
      source_path: exports/scene0000_00
""".strip(),
        encoding="utf-8",
    )

    spec = load_dataset_spec(config_path, root=ROOT)
    root_override = tmp_path / "mounted_dataset_root"
    scene = resolve_dataset_scene(spec, root_override=root_override)

    assert scene.source_path == (root_override / "exports/scene0000_00").resolve()


def test_resolve_dataset_scene_requires_scene_id_without_default(tmp_path: Path) -> None:
    config_path = tmp_path / "dataset.yaml"
    config_path.write_text(
        """
dataset:
  name: no_default
  root: data/public_datasets/no_default
  format: colmap
""".strip(),
        encoding="utf-8",
    )

    spec = load_dataset_spec(config_path, root=ROOT)

    try:
        resolve_dataset_scene(spec)
    except ValueError as exc:
        assert "requires a scene_id" in str(exc)
    else:
        raise AssertionError("Expected resolve_dataset_scene to require scene_id when default is absent")
