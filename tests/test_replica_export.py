from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.replica_export import CameraFrame, select_largest_target, select_top_targets, write_colmap_text_scene


def test_select_largest_target_picks_largest_category_instance(tmp_path: Path) -> None:
    scene_root = tmp_path / "room_0"
    habitat_dir = scene_root / "habitat"
    habitat_dir.mkdir(parents=True)
    (habitat_dir / "info_semantic.json").write_text(
        json.dumps(
            {
                "objects": [
                    {
                        "id": 10,
                        "class_name": "chair",
                        "oriented_bbox": {
                            "abb": {"center": [0.0, 0.0, 0.0], "sizes": [0.5, 0.5, 0.5]},
                            "orientation": {"rotation": [0.0, 0.0, 0.0, 1.0]},
                        },
                    },
                    {
                        "id": 74,
                        "class_name": "chair",
                        "oriented_bbox": {
                            "abb": {"center": [1.0, 2.0, 3.0], "sizes": [1.0, 0.8, 1.2]},
                            "orientation": {"rotation": [0.0, 0.0, 0.0, 1.0]},
                        },
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    target = select_largest_target(scene_root, category="chair")

    assert target.object_id == 74
    assert np.allclose(target.center, np.asarray([1.0, 2.0, 3.0], dtype=np.float32))


def test_write_colmap_text_scene_writes_required_files_and_test_split(tmp_path: Path) -> None:
    frames = [
        CameraFrame(
            image_name="00000.png",
            position=np.asarray([1.0, 0.0, 0.0], dtype=np.float32),
            rotation_cam2world=np.eye(3, dtype=np.float32),
            visible_ratio=0.5,
            split="train",
        ),
        CameraFrame(
            image_name="00001.png",
            position=np.asarray([0.0, 1.0, 0.0], dtype=np.float32),
            rotation_cam2world=np.eye(3, dtype=np.float32),
            visible_ratio=0.5,
            split="test",
        ),
    ]
    points_xyz = np.asarray([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]], dtype=np.float32)
    points_rgb = np.asarray([[255, 0, 0], [0, 255, 0]], dtype=np.uint8)

    write_colmap_text_scene(
        tmp_path,
        frames=frames,
        width=512,
        height=512,
        hfov_deg=60.0,
        points_xyz=points_xyz,
        points_rgb=points_rgb,
    )

    sparse_dir = tmp_path / "sparse" / "0"
    assert (sparse_dir / "cameras.txt").exists()
    assert (sparse_dir / "images.txt").exists()
    assert (sparse_dir / "points3D.txt").exists()
    assert (sparse_dir / "test.txt").read_text(encoding="utf-8").strip() == "00001.png"


def test_select_top_targets_filters_categories_and_limits_count(tmp_path: Path) -> None:
    scene_root = tmp_path / "office_0"
    habitat_dir = scene_root / "habitat"
    habitat_dir.mkdir(parents=True)
    (habitat_dir / "info_semantic.json").write_text(
        json.dumps(
            {
                "objects": [
                    {
                        "id": 74,
                        "class_name": "chair",
                        "oriented_bbox": {
                            "abb": {"center": [0.0, 0.0, 0.0], "sizes": [1.0, 0.7, 0.8]},
                            "orientation": {"rotation": [0.0, 0.0, 0.0, 1.0]},
                        },
                    },
                    {
                        "id": 9,
                        "class_name": "sofa",
                        "oriented_bbox": {
                            "abb": {"center": [1.0, 0.0, 0.0], "sizes": [2.0, 1.0, 1.0]},
                            "orientation": {"rotation": [0.0, 0.0, 0.0, 1.0]},
                        },
                    },
                    {
                        "id": 11,
                        "class_name": "table",
                        "oriented_bbox": {
                            "abb": {"center": [2.0, 0.0, 0.0], "sizes": [1.2, 1.0, 0.8]},
                            "orientation": {"rotation": [0.0, 0.0, 0.0, 1.0]},
                        },
                    },
                    {
                        "id": 57,
                        "class_name": "wall",
                        "oriented_bbox": {
                            "abb": {"center": [3.0, 0.0, 0.0], "sizes": [3.0, 3.0, 0.1]},
                            "orientation": {"rotation": [0.0, 0.0, 0.0, 1.0]},
                        },
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    targets = select_top_targets(scene_root, categories=["chair", "sofa", "table", "lamp"], max_objects=2)

    assert [target.category for target in targets] == ["sofa", "table"]
    assert [target.object_id for target in targets] == [9, 11]
