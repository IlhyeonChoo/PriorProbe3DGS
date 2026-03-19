from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.readiness import check_dataset_scene, check_prior_assets


def test_check_prior_assets_uses_asset_completeness_instead_of_placeholder(tmp_path: Path) -> None:
    prior_root = tmp_path / "data" / "priors" / "shapesplat"
    render_dir = prior_root / "renders" / "chair_basic"
    render_dir.mkdir(parents=True)
    (prior_root / "chair_basic.ply").write_text("ply\nformat ascii 1.0\nend_header\n", encoding="utf-8")
    (render_dir / "000.png").write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfeA\x8d\xb6\x89\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    config_path = tmp_path / "prior.yaml"
    config_path.write_text(
        """
asset_prep:
  min_render_count: 1
library:
  default_objects:
    - object_id: chair_basic
      category: chair
      gaussian_path: data/priors/shapesplat/chair_basic.ply
      feature_path: data/priors/shapesplat/chair_basic.npy
      render_dir: data/priors/shapesplat/renders/chair_basic
      placeholder: true
""".strip(),
        encoding="utf-8",
    )

    checks = check_prior_assets(config_path, root=tmp_path)

    assert len(checks) == 1
    assert checks[0].ready is True
    assert checks[0].render_count == 1
    assert any("placeholder prior" in warning for warning in checks[0].warnings)


def test_check_prior_assets_blocks_when_renders_are_missing(tmp_path: Path) -> None:
    prior_root = tmp_path / "data" / "priors" / "shapesplat"
    prior_root.mkdir(parents=True)
    (prior_root / "chair_basic.ply").write_text("ply\nformat ascii 1.0\nend_header\n", encoding="utf-8")
    config_path = tmp_path / "prior.yaml"
    config_path.write_text(
        """
asset_prep:
  min_render_count: 2
library:
  default_objects:
    - object_id: chair_basic
      category: chair
      gaussian_path: data/priors/shapesplat/chair_basic.ply
      render_dir: data/priors/shapesplat/renders/chair_basic
""".strip(),
        encoding="utf-8",
    )

    checks = check_prior_assets(config_path, root=tmp_path)

    assert len(checks) == 1
    assert checks[0].ready is False
    assert any("insufficient renders" in issue for issue in checks[0].blocking_issues)


def test_check_dataset_scene_warns_on_missing_scene_meta(tmp_path: Path) -> None:
    scene_root = tmp_path / "datasets" / "replica_colmap" / "room_0"
    images_dir = scene_root / "images"
    sparse_dir = scene_root / "sparse" / "0"
    images_dir.mkdir(parents=True)
    sparse_dir.mkdir(parents=True)
    (images_dir / "0001.png").write_bytes(b"placeholder")
    for filename in ("cameras.txt", "images.txt", "points3D.txt"):
        (sparse_dir / filename).write_text("# placeholder", encoding="utf-8")

    config_path = tmp_path / "dataset.yaml"
    config_path.write_text(
        """
dataset:
  name: replica
  root: datasets/replica_colmap
  format: colmap
  default_scene_id: room_0
  scenes:
    room_0:
      relative_path: room_0
""".strip(),
        encoding="utf-8",
    )

    check = check_dataset_scene(config_path, root=tmp_path)

    assert check.ready is False
    assert check.blocking_issues == ()
    assert any("missing scene_meta.json" in warning for warning in check.warnings)
