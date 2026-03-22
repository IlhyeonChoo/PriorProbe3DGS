from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.replica_export import (
    CameraFrame,
    accepted_azimuth_histogram,
    accepted_axis_counts,
    accepted_forward_histogram,
    assign_test_indices_stratified_azimuth,
    select_largest_target,
    select_multi_object_candidate_infos,
    select_top_targets,
    write_colmap_text_scene,
)


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


def test_select_multi_object_candidate_infos_diverse_azimuth_spreads_views() -> None:
    focus_center = np.asarray([0.0, 0.0, 0.0], dtype=np.float32)
    candidate_infos = []
    # Create many high-score candidates from bin 0 and lower-score candidates from other bins.
    for index, position in enumerate(
        [
            [2.0, 0.0, 0.0],
            [1.8, 0.2, 0.0],
            [1.7, -0.1, 0.0],
            [0.0, 2.0, 0.0],
            [-2.0, 0.0, 0.0],
            [0.0, -2.0, 0.0],
        ]
    ):
        candidate_infos.append(
            {
                "position": np.asarray(position, dtype=np.float32),
                "rotation": np.eye(3, dtype=np.float32),
                "visible_ratios": {9: 0.01 if index else 0.05},
                "union_visible_ratio": [0.95, 0.92, 0.90, 0.40, 0.35, 0.30][index],
            }
        )

    selected = select_multi_object_candidate_infos(
        candidate_infos,
        total_views=4,
        target_ids=[9],
        focus_center=focus_center,
        selection_mode="diverse_azimuth",
        azimuth_bin_count=4,
    )

    frames = [
        CameraFrame(
            image_name=f"{index:05d}.png",
            position=np.asarray(item["position"], dtype=np.float32),
            rotation_cam2world=np.asarray(item["rotation"], dtype=np.float32),
            visible_ratio=float(item["union_visible_ratio"]),
            split="train",
        )
        for index, item in enumerate(selected)
    ]
    histogram = accepted_azimuth_histogram(frames, focus_center, bin_count=4)

    assert len(selected) == 4
    assert sum(1 for count in histogram if count > 0) >= 3


def test_select_multi_object_candidate_infos_roomwide_v2_limits_bin_bias() -> None:
    focus_center = np.asarray([0.0, 0.0, 0.0], dtype=np.float32)
    candidate_infos = []
    # Heavily biased score distribution toward +X / -X bins.
    for index, position in enumerate(
        [
            [2.0, 0.0, 0.0],
            [1.8, 0.1, 0.0],
            [1.7, -0.1, 0.0],
            [0.0, 2.0, 0.0],
            [-2.0, 0.0, 0.0],
            [-1.8, 0.1, 0.0],
            [0.0, -2.0, 0.0],
            [1.4, 1.4, 0.0],
        ]
    ):
        candidate_infos.append(
            {
                "position": np.asarray(position, dtype=np.float32),
                "rotation": np.eye(3, dtype=np.float32),
                "visible_ratios": {9: 0.02 if index < 2 else 0.0},
                "union_visible_ratio": 0.0,
                "scene_visible_ratio": [0.99, 0.98, 0.97, 0.45, 0.50, 0.49, 0.44, 0.43][index],
            }
        )

    selected = select_multi_object_candidate_infos(
        candidate_infos,
        total_views=6,
        target_ids=[9],
        focus_center=focus_center,
        selection_mode="room_wide_balanced_azimuth_v2",
        azimuth_bin_count=8,
    )
    frames = [
        CameraFrame(
            image_name=f"{index:05d}.png",
            position=np.asarray(item["position"], dtype=np.float32),
            rotation_cam2world=np.asarray(item["rotation"], dtype=np.float32),
            visible_ratio=float(item["scene_visible_ratio"]),
            split="train",
        )
        for index, item in enumerate(selected)
    ]
    histogram = accepted_azimuth_histogram(frames, focus_center, bin_count=8)

    assert len(selected) == 6
    assert max(histogram) <= 2
    assert sum(1 for count in histogram if count > 0) >= 4


def test_assign_test_indices_stratified_azimuth_preserves_bins() -> None:
    focus_center = np.asarray([0.0, 0.0, 0.0], dtype=np.float32)
    frames = []
    positions = (
        [[2.0, 0.0, 0.0]] * 4
        + [[0.0, 2.0, 0.0]] * 4
        + [[-2.0, 0.0, 0.0]] * 4
        + [[0.0, -2.0, 0.0]] * 4
    )
    rotations = [
        np.asarray(
            [
                [0.0, 0.0, -1.0],
                [1.0, 0.0, 0.0],
                [0.0, -1.0, 0.0],
            ],
            dtype=np.float32,
        )
    ] * len(positions)
    for index, (position, rotation) in enumerate(zip(positions, rotations, strict=True)):
        frames.append(
            CameraFrame(
                image_name=f"{index:05d}.png",
                position=np.asarray(position, dtype=np.float32),
                rotation_cam2world=rotation,
                visible_ratio=1.0,
                split="train",
            )
        )

    test_indices = assign_test_indices_stratified_azimuth(
        frames,
        test_views=4,
        focus_center=focus_center,
        azimuth_bin_count=4,
    )

    test_frames = [frame for index, frame in enumerate(frames) if index in test_indices]
    train_frames = [frame for index, frame in enumerate(frames) if index not in test_indices]
    assert len(test_frames) == 4
    assert accepted_azimuth_histogram(test_frames, focus_center, bin_count=4) == [1, 1, 1, 1]
    assert accepted_azimuth_histogram(train_frames, focus_center, bin_count=4) == [3, 3, 3, 3]


def test_camera_distribution_helpers_count_forward_and_axis() -> None:
    frames = [
        CameraFrame(
            image_name="00000.png",
            position=np.asarray([1.0, 0.0, 0.0], dtype=np.float32),
            rotation_cam2world=np.asarray(
                [
                    [0.0, 0.0, 1.0],
                    [1.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0],
                ],
                dtype=np.float32,
            ),
            visible_ratio=1.0,
            split="train",
        ),
        CameraFrame(
            image_name="00001.png",
            position=np.asarray([0.0, 1.0, 0.0], dtype=np.float32),
            rotation_cam2world=np.asarray(
                [
                    [1.0, 0.0, 0.0],
                    [0.0, 0.0, 1.0],
                    [0.0, -1.0, 0.0],
                ],
                dtype=np.float32,
            ),
            visible_ratio=1.0,
            split="train",
        ),
    ]

    assert sum(accepted_forward_histogram(frames, bin_count=8)) == 2
    axis_counts = accepted_axis_counts(frames)
    assert axis_counts["ew"] == 1
    assert axis_counts["ns"] == 1
