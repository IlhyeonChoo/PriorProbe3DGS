from __future__ import annotations

from pathlib import Path

import numpy as np

from priorprobe.replica_surface import (
    build_surface_dataset_config_payload,
    colmap_pose_to_world,
    load_colmap_camera_model,
    load_colmap_text_frames,
    opencv_cam2world_to_opengl_pose,
)


def test_colmap_pose_to_world_identity_rotation() -> None:
    rotation_cam2world, position = colmap_pose_to_world(
        np.asarray([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
        np.asarray([1.0, 2.0, 3.0], dtype=np.float32),
    )
    np.testing.assert_allclose(rotation_cam2world, np.eye(3, dtype=np.float32))
    np.testing.assert_allclose(position, np.asarray([-1.0, -2.0, -3.0], dtype=np.float32))


def test_opencv_cam2world_to_opengl_pose_flips_camera_axes() -> None:
    pose = opencv_cam2world_to_opengl_pose(
        np.eye(3, dtype=np.float32),
        np.asarray([1.0, 2.0, 3.0], dtype=np.float32),
    )
    expected = np.asarray(
        [
            [1.0, 0.0, 0.0, 1.0],
            [0.0, -1.0, 0.0, 2.0],
            [0.0, 0.0, -1.0, 3.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )
    np.testing.assert_allclose(pose, expected)


def test_load_colmap_text_frames_reads_camera_and_split(tmp_path: Path) -> None:
    sparse_dir = tmp_path / "sparse" / "0"
    sparse_dir.mkdir(parents=True)
    (sparse_dir / "cameras.txt").write_text(
        "# Camera list\n1 PINHOLE 640 480 500 501 320 240\n",
        encoding="utf-8",
    )
    (sparse_dir / "test.txt").write_text("00001.png\n", encoding="utf-8")
    (sparse_dir / "images.txt").write_text(
        "\n".join(
            [
                "# Images list",
                "1 1 0 0 0 1 2 3 1 00000.png",
                "0 0 0",
                "2 1 0 0 0 4 5 6 1 00001.png",
                "0 0 0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    camera_model = load_colmap_camera_model(tmp_path)
    assert camera_model.width == 640
    assert camera_model.height == 480
    assert camera_model.fx == 500.0
    assert camera_model.fy == 501.0

    loaded_camera_model, frames = load_colmap_text_frames(tmp_path)
    assert loaded_camera_model == camera_model
    assert [frame.image_name for frame in frames] == ["00000.png", "00001.png"]
    assert [frame.split for frame in frames] == ["train", "test"]
    np.testing.assert_allclose(frames[0].position, np.asarray([-1.0, -2.0, -3.0], dtype=np.float32))
    np.testing.assert_allclose(frames[1].position, np.asarray([-4.0, -5.0, -6.0], dtype=np.float32))


def test_build_surface_dataset_config_payload_includes_surface_scene_type(tmp_path: Path) -> None:
    payload = build_surface_dataset_config_payload(
        root=tmp_path / "surface_root",
        scene_ids=["room_0", "office_0"],
    )
    dataset = payload["dataset"]
    assert dataset["scene_type"] == "controlled_indoor_multi_object_surface_rgb"
    assert dataset["default_scene_id"] == "room_0"
    assert dataset["scenes"] == {
        "room_0": {"relative_path": "room_0"},
        "office_0": {"relative_path": "office_0"},
    }
    assert any("vertex-colored mesh" in note for note in dataset["notes"])
