from __future__ import annotations

import yaml
from pathlib import Path

import numpy as np
from plyfile import PlyData, PlyElement

from priorprobe.replica_surface import (
    build_surface_dataset_config_payload,
    canonicalize_gaussian_asset_to_seed_frame,
    colmap_pose_to_world,
    load_colmap_camera_model,
    load_colmap_text_frames,
    opencv_cam2world_to_opengl_pose,
)


ROOT = Path(__file__).resolve().parents[1]


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


def test_shared_surface_dataset_yaml_matches_generated_payload() -> None:
    config_path = ROOT / "configs" / "datasets" / "replica_multi_roomwide_v2_384_surface_rgb_shared.yaml"
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    dataset = payload["dataset"]

    generated = build_surface_dataset_config_payload(
        root=Path(str(dataset["root"])),
        scene_ids=list(dataset["scenes"].keys()),
    )

    assert payload == generated


def test_canonicalize_gaussian_asset_to_seed_frame_matches_floor_seed_inverse(tmp_path: Path) -> None:
    source_path = tmp_path / "world_gaussian.ply"
    output_path = tmp_path / "canonicalized.ply"
    dtype = [
        ("x", "f4"),
        ("y", "f4"),
        ("z", "f4"),
        ("opacity", "f4"),
        ("scale_0", "f4"),
        ("scale_1", "f4"),
        ("scale_2", "f4"),
        ("rot_0", "f4"),
        ("rot_1", "f4"),
        ("rot_2", "f4"),
        ("rot_3", "f4"),
        ("f_dc_0", "f4"),
        ("f_dc_1", "f4"),
        ("f_dc_2", "f4"),
    ]
    local_seed_xyz = np.asarray(
        [
            [-0.5, -1.0, 0.0],
            [0.5, 1.0, 2.0],
        ],
        dtype=np.float32,
    )
    target_payload = {
        "object_id": 1,
        "category": "lamp",
        "center": [10.0, 20.0, 6.0],
        "sizes": [1.0, 2.0, 2.0],
        "rotation_xyzw": [0.0, 0.0, np.sin(np.pi / 4.0), np.cos(np.pi / 4.0)],
    }
    rotation_matrix = np.asarray(
        [
            [0.0, -1.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )
    target_bottom_anchor = np.asarray([10.0, 20.0, 5.0], dtype=np.float32)
    world_xyz = local_seed_xyz @ rotation_matrix.T + target_bottom_anchor[None, :]

    vertex = np.zeros(local_seed_xyz.shape[0], dtype=dtype)
    vertex["x"] = world_xyz[:, 0]
    vertex["y"] = world_xyz[:, 1]
    vertex["z"] = world_xyz[:, 2]
    vertex["opacity"] = 0.5
    vertex["scale_0"] = np.log(0.1)
    vertex["scale_1"] = np.log(0.2)
    vertex["scale_2"] = np.log(0.3)
    vertex["rot_0"] = 1.0
    vertex["rot_1"] = 0.0
    vertex["rot_2"] = 0.0
    vertex["rot_3"] = 0.0
    PlyData([PlyElement.describe(vertex, "vertex")]).write(source_path)

    canonicalize_gaussian_asset_to_seed_frame(
        source_path,
        output_path,
        target_payload=target_payload,
        anchor_mode="floor",
    )

    output_ply = PlyData.read(output_path)
    output_vertex = output_ply["vertex"].data
    output_xyz = np.stack(
        [
            np.asarray(output_vertex["x"], dtype=np.float32),
            np.asarray(output_vertex["y"], dtype=np.float32),
            np.asarray(output_vertex["z"], dtype=np.float32),
        ],
        axis=1,
    )
    np.testing.assert_allclose(output_xyz, local_seed_xyz, atol=1e-5)
