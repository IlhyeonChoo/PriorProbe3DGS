from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from plyfile import PlyData, PlyElement

from priorprobe.gaussian_affine import detect_asset_format, transform_gaussian_vertex
from priorprobe.replica_export import CameraFrame, _load_mesh_arrays, _sample_mesh_triangles
from priorprobe.replica_export import quaternion_xyzw_to_rotation_matrix


@dataclass(slots=True)
class ColmapCameraModel:
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float


def qvec_wxyz_to_rotation_matrix(qvec_wxyz: np.ndarray) -> np.ndarray:
    qvec = np.asarray(qvec_wxyz, dtype=np.float64).reshape(4)
    qvec /= np.linalg.norm(qvec)
    w, x, y, z = qvec.tolist()
    return np.asarray(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float32,
    )


def colmap_pose_to_world(
    qvec_wxyz: np.ndarray,
    tvec_world2cam: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    rotation_world2cam = qvec_wxyz_to_rotation_matrix(qvec_wxyz)
    rotation_cam2world = rotation_world2cam.T.astype(np.float32)
    position = (-rotation_cam2world @ np.asarray(tvec_world2cam, dtype=np.float32).reshape(3)).astype(np.float32)
    return rotation_cam2world, position


def opencv_cam2world_to_opengl_pose(
    rotation_cam2world: np.ndarray,
    position: np.ndarray,
) -> np.ndarray:
    pose = np.eye(4, dtype=np.float32)
    pose[:3, :3] = np.asarray(rotation_cam2world, dtype=np.float32)
    pose[:3, 3] = np.asarray(position, dtype=np.float32).reshape(3)
    cv_to_gl = np.diag([1.0, -1.0, -1.0, 1.0]).astype(np.float32)
    return pose @ cv_to_gl


def load_colmap_camera_model(scene_root: Path) -> ColmapCameraModel:
    cameras_path = scene_root / "sparse" / "0" / "cameras.txt"
    for raw_line in cameras_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 8 or parts[1] != "PINHOLE":
            raise ValueError(f"Unsupported cameras.txt entry in {cameras_path}: {line}")
        return ColmapCameraModel(
            width=int(parts[2]),
            height=int(parts[3]),
            fx=float(parts[4]),
            fy=float(parts[5]),
            cx=float(parts[6]),
            cy=float(parts[7]),
        )
    raise ValueError(f"No camera entry found in {cameras_path}")


def load_colmap_text_frames(scene_root: Path) -> tuple[ColmapCameraModel, list[CameraFrame]]:
    camera_model = load_colmap_camera_model(scene_root)
    test_names = {
        line.strip()
        for line in (scene_root / "sparse" / "0" / "test.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    images_path = scene_root / "sparse" / "0" / "images.txt"
    frames: list[CameraFrame] = []
    for raw_line in images_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 10:
            continue
        qvec = np.asarray([float(value) for value in parts[1:5]], dtype=np.float32)
        tvec = np.asarray([float(value) for value in parts[5:8]], dtype=np.float32)
        image_name = str(parts[9])
        rotation_cam2world, position = colmap_pose_to_world(qvec, tvec)
        frames.append(
            CameraFrame(
                image_name=image_name,
                position=position,
                rotation_cam2world=rotation_cam2world,
                visible_ratio=0.0,
                split="test" if image_name in test_names else "train",
            )
        )
    if not frames:
        raise ValueError(f"No image frames found in {images_path}")
    return camera_model, frames


def object_mesh_arrays(scene_root: Path, *, object_id: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xyz, rgb, triangles, triangle_object_ids = _load_mesh_arrays(
        scene_root / "habitat" / "mesh_semantic.ply",
        include_object_ids=True,
    )
    assert triangle_object_ids is not None
    selected = triangles[triangle_object_ids == int(object_id)]
    if selected.size == 0:
        raise ValueError(f"No triangles found for object_id={object_id} in {scene_root}")
    unique_vertex_ids, remapped = np.unique(selected.reshape(-1), return_inverse=True)
    object_xyz = xyz[unique_vertex_ids].astype(np.float32)
    object_rgb = rgb[unique_vertex_ids].astype(np.uint8)
    object_faces = remapped.reshape(-1, 3).astype(np.int64)
    return object_xyz, object_rgb, object_faces


def sample_object_mesh_points(
    scene_root: Path,
    *,
    object_id: int,
    num_points: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    xyz, rgb, triangles, triangle_object_ids = _load_mesh_arrays(
        scene_root / "habitat" / "mesh_semantic.ply",
        include_object_ids=True,
    )
    assert triangle_object_ids is not None
    object_triangles = triangles[triangle_object_ids == int(object_id)]
    if object_triangles.size == 0:
        raise ValueError(f"No triangles found for object_id={object_id} in {scene_root}")
    samples, colors, _ = _sample_mesh_triangles(
        xyz,
        rgb,
        object_triangles,
        num_points=num_points,
        seed=seed,
    )
    return samples.astype(np.float32), colors.astype(np.uint8)


def target_payload_anchor_and_rotation(
    target_payload: dict[str, Any],
    *,
    anchor_mode: str,
) -> tuple[np.ndarray, np.ndarray]:
    center = np.asarray(target_payload["center"], dtype=np.float32)
    sizes = np.asarray(target_payload["sizes"], dtype=np.float32)
    rotation_matrix = quaternion_xyzw_to_rotation_matrix(
        np.asarray(target_payload["rotation_xyzw"], dtype=np.float32)
    ).astype(np.float32)
    if anchor_mode == "floor":
        anchor = center + rotation_matrix @ np.asarray(
            [0.0, 0.0, -float(sizes[2]) * 0.5],
            dtype=np.float32,
        )
        return anchor.astype(np.float32), rotation_matrix
    if anchor_mode == "center":
        return center.astype(np.float32), rotation_matrix
    raise ValueError(f"Unsupported anchor_mode: {anchor_mode}")


def canonicalize_gaussian_asset_to_seed_frame(
    source_path: Path,
    output_path: Path,
    *,
    target_payload: dict[str, Any],
    anchor_mode: str,
) -> dict[str, Any]:
    ply = PlyData.read(source_path)
    vertex = np.array(ply["vertex"].data, copy=True)
    if detect_asset_format(vertex) != "gaussian":
        raise ValueError(f"Expected gaussian asset: {source_path}")

    anchor_world, rotation_matrix = target_payload_anchor_and_rotation(
        target_payload,
        anchor_mode=anchor_mode,
    )
    canonical_vertex = transform_gaussian_vertex(
        vertex,
        rotation_matrix=rotation_matrix.T,
        scale=np.ones(3, dtype=np.float32),
        translation=np.asarray((-anchor_world) @ rotation_matrix, dtype=np.float32),
    )

    xyz = np.stack(
        [
            np.asarray(canonical_vertex["x"], dtype=np.float32),
            np.asarray(canonical_vertex["y"], dtype=np.float32),
            np.asarray(canonical_vertex["z"], dtype=np.float32),
        ],
        axis=1,
    )
    bbox_min = xyz.min(axis=0).astype(np.float32)
    bbox_max = xyz.max(axis=0).astype(np.float32)
    bbox_center = ((bbox_min + bbox_max) * 0.5).astype(np.float32)
    if anchor_mode == "floor":
        seed_shift = np.asarray([bbox_center[0], bbox_center[1], bbox_min[2]], dtype=np.float32)
    else:
        seed_shift = bbox_center

    canonical_vertex["x"] = (xyz[:, 0] - seed_shift[0]).astype(np.float32)
    canonical_vertex["y"] = (xyz[:, 1] - seed_shift[1]).astype(np.float32)
    canonical_vertex["z"] = (xyz[:, 2] - seed_shift[2]).astype(np.float32)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    PlyData([PlyElement.describe(canonical_vertex, "vertex")]).write(output_path)

    return {
        "source_path": str(source_path),
        "output_path": str(output_path),
        "anchor_mode": anchor_mode,
        "anchor_world": anchor_world.tolist(),
        "seed_shift": seed_shift.tolist(),
        "canonical_bbox_min_before_shift": bbox_min.tolist(),
        "canonical_bbox_max_before_shift": bbox_max.tolist(),
    }


class ReplicaEGLRenderer:
    def __init__(
        self,
        *,
        width: int,
        height: int,
        fx: float,
        fy: float,
        cx: float,
        cy: float,
        mesh_path: Path | None = None,
        vertices: np.ndarray | None = None,
        faces: np.ndarray | None = None,
        colors: np.ndarray | None = None,
        ambient_light: tuple[float, float, float] = (0.1, 0.1, 0.1),
        directional_intensity: float = 0.5,
        background_rgba: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0),
    ) -> None:
        os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
        import pyrender  # type: ignore
        import trimesh  # type: ignore

        if mesh_path is None and (vertices is None or faces is None or colors is None):
            raise ValueError("Either mesh_path or vertices/faces/colors must be provided")

        if mesh_path is not None:
            trimesh_mesh = trimesh.load(mesh_path, process=False)
        else:
            trimesh_mesh = trimesh.Trimesh(
                vertices=np.asarray(vertices, dtype=np.float32),
                faces=np.asarray(faces, dtype=np.int64),
                vertex_colors=np.asarray(colors, dtype=np.uint8),
                process=False,
            )

        self._pyrender = pyrender
        self.width = int(width)
        self.height = int(height)
        self.scene = pyrender.Scene(
            bg_color=np.asarray(background_rgba, dtype=np.float32),
            ambient_light=np.asarray(ambient_light, dtype=np.float32),
        )
        self.scene.add(pyrender.Mesh.from_trimesh(trimesh_mesh, smooth=False))
        self.camera_node = self.scene.add(
            pyrender.IntrinsicsCamera(
                fx=float(fx),
                fy=float(fy),
                cx=float(cx),
                cy=float(cy),
            ),
            pose=np.eye(4, dtype=np.float32),
        )
        self.light_node = None
        if directional_intensity > 0.0:
            self.light_node = self.scene.add(
                pyrender.DirectionalLight(color=np.ones(3, dtype=np.float32), intensity=float(directional_intensity)),
                pose=np.eye(4, dtype=np.float32),
            )
        self.renderer = pyrender.OffscreenRenderer(self.width, self.height)

    def close(self) -> None:
        self.renderer.delete()

    def render(self, *, position: np.ndarray, rotation_cam2world: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        pose = opencv_cam2world_to_opengl_pose(rotation_cam2world, position)
        self.scene.set_pose(self.camera_node, pose)
        if self.light_node is not None:
            self.scene.set_pose(self.light_node, pose)
        color, depth = self.renderer.render(self.scene)
        return np.asarray(color).copy(), np.asarray(depth).copy()


def build_surface_dataset_config_payload(
    *,
    root: Path,
    scene_ids: list[str],
) -> dict[str, Any]:
    return {
        "dataset": {
            "name": "replica",
            "phase": "A",
            "root": str(root),
            "format": "colmap",
            "default_scene_id": scene_ids[0] if scene_ids else None,
            "source_path_template": "{root}/{scene_id}",
            "images": "images",
            "depths": "",
            "eval": True,
            "white_background": False,
            "scene_type": "controlled_indoor_multi_object_surface_rgb",
            "object_count_range": [2, 4],
            "notes": [
                "Replica multi-object roomwide v2 scenes rerendered from raw vertex-colored mesh with EGL offscreen rendering.",
                "Camera poses and sparse points are reused from the GT-staged roomwide_v2_384 dataset.",
                "Oracle target metadata is copied from the reference dataset; oracle crops are object-only surface renders.",
            ],
            "scenes": {scene_id: {"relative_path": scene_id} for scene_id in scene_ids},
        }
    }
