from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from priorprobe.features import FeatureExtractorConfig, extract_image_features


@dataclass(slots=True)
class ReplicaOracleTarget:
    scene_id: str
    object_id: int
    category: str
    center: np.ndarray
    sizes: np.ndarray
    rotation_xyzw: np.ndarray
    volume: float


@dataclass(slots=True)
class CameraFrame:
    image_name: str
    position: np.ndarray
    rotation_cam2world: np.ndarray
    visible_ratio: float
    split: str
    visible_ratios: dict[int, float] | None = None


def load_replica_semantic_info(scene_root: Path) -> dict[str, Any]:
    info_path = scene_root / "habitat" / "info_semantic.json"
    return json.loads(info_path.read_text(encoding="utf-8"))


def select_largest_target(scene_root: Path, *, category: str) -> ReplicaOracleTarget:
    payload = load_replica_semantic_info(scene_root)
    scene_id = scene_root.name
    candidates = []
    for item in payload.get("objects", []):
        if item.get("class_name") != category:
            continue
        bbox = item["oriented_bbox"]["abb"]
        sizes = np.asarray(bbox["sizes"], dtype=np.float32)
        center = np.asarray(bbox["center"], dtype=np.float32)
        rotation = np.asarray(item["oriented_bbox"]["orientation"]["rotation"], dtype=np.float32)
        candidates.append(
            ReplicaOracleTarget(
                scene_id=scene_id,
                object_id=int(item["id"]),
                category=category,
                center=center,
                sizes=sizes,
                rotation_xyzw=rotation,
                volume=float(np.prod(sizes)),
            )
        )
    if not candidates:
        raise ValueError(f"No Replica semantic object with category={category!r} found in {scene_root}")
    candidates.sort(key=lambda item: item.volume, reverse=True)
    return candidates[0]


def select_top_targets(
    scene_root: Path,
    *,
    categories: list[str] | tuple[str, ...],
    max_objects: int,
) -> list[ReplicaOracleTarget]:
    payload = load_replica_semantic_info(scene_root)
    scene_id = scene_root.name
    allowed_categories = {str(category) for category in categories}
    candidates: list[ReplicaOracleTarget] = []
    for item in payload.get("objects", []):
        category = str(item.get("class_name"))
        if category not in allowed_categories:
            continue
        bbox = item["oriented_bbox"]["abb"]
        sizes = np.asarray(bbox["sizes"], dtype=np.float32)
        center = np.asarray(bbox["center"], dtype=np.float32)
        rotation = np.asarray(item["oriented_bbox"]["orientation"]["rotation"], dtype=np.float32)
        candidates.append(
            ReplicaOracleTarget(
                scene_id=scene_id,
                object_id=int(item["id"]),
                category=category,
                center=center,
                sizes=sizes,
                rotation_xyzw=rotation,
                volume=float(np.prod(sizes)),
            )
        )
    candidates.sort(key=lambda item: item.volume, reverse=True)
    if max_objects > 0:
        candidates = candidates[:max_objects]
    if not candidates:
        joined = ", ".join(sorted(allowed_categories))
        raise ValueError(f"No Replica semantic objects with categories in [{joined}] found in {scene_root}")
    return candidates


def quaternion_xyzw_to_rotation_matrix(quaternion_xyzw: np.ndarray) -> np.ndarray:
    x, y, z, w = quaternion_xyzw.tolist()
    norm = math.sqrt(w * w + x * x + y * y + z * z)
    if norm == 0.0:
        return np.eye(3, dtype=np.float32)
    w, x, y, z = w / norm, x / norm, y / norm, z / norm
    return np.asarray(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float32,
    )


def quaternion_wxyz_from_rotation_matrix(rotation_matrix: np.ndarray) -> np.ndarray:
    m = rotation_matrix.astype(np.float64)
    trace = float(np.trace(m))
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        w = 0.25 * s
        x = (m[2, 1] - m[1, 2]) / s
        y = (m[0, 2] - m[2, 0]) / s
        z = (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2.0
        w = (m[2, 1] - m[1, 2]) / s
        x = 0.25 * s
        y = (m[0, 1] + m[1, 0]) / s
        z = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2.0
        w = (m[0, 2] - m[2, 0]) / s
        x = (m[0, 1] + m[1, 0]) / s
        y = 0.25 * s
        z = (m[1, 2] + m[2, 1]) / s
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2.0
        w = (m[1, 0] - m[0, 1]) / s
        x = (m[0, 2] + m[2, 0]) / s
        y = (m[1, 2] + m[2, 1]) / s
        z = 0.25 * s
    quat = np.asarray([w, x, y, z], dtype=np.float64)
    quat /= np.linalg.norm(quat)
    return quat.astype(np.float32)


def look_at_opencv(eye: np.ndarray, center: np.ndarray, up: np.ndarray) -> np.ndarray:
    z_axis = center - eye
    z_axis = z_axis / np.linalg.norm(z_axis)
    y_axis = -up
    y_axis = y_axis - np.dot(y_axis, z_axis) * z_axis
    y_axis = y_axis / np.linalg.norm(y_axis)
    x_axis = np.cross(y_axis, z_axis)
    return np.stack((x_axis, y_axis, z_axis), axis=-1).astype(np.float32)


def camera_intrinsics(width: int, height: int, hfov_deg: float) -> tuple[float, float, float, float]:
    focal = (width / 2.0) / math.tan(math.radians(hfov_deg) / 2.0)
    return focal, focal, width / 2.0, height / 2.0


def world_to_colmap_pose(rotation_cam2world: np.ndarray, translation_cam2world: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rotation_world2cam = rotation_cam2world.T
    translation_world2cam = -rotation_world2cam @ translation_cam2world
    return quaternion_wxyz_from_rotation_matrix(rotation_world2cam), translation_world2cam.astype(np.float32)


def generate_orbit_camera_poses(
    target: ReplicaOracleTarget,
    *,
    count: int,
    seed: int,
    radius_min: float,
    radius_max: float,
) -> list[tuple[np.ndarray, np.ndarray]]:
    rng = np.random.default_rng(seed)
    up = np.asarray([0.0, 0.0, 1.0], dtype=np.float32)
    base_radius = float(np.clip(max(target.sizes[0], target.sizes[1]) * 2.5, radius_min, radius_max))
    poses: list[tuple[np.ndarray, np.ndarray]] = []
    for index in range(count):
        yaw = (2.0 * math.pi * index / max(count, 1)) + rng.normal(0.0, 0.05)
        radius = float(np.clip(base_radius + rng.normal(0.0, 0.12), radius_min, radius_max))
        z_offset = (0.25 * float(target.sizes[2])) + rng.uniform(-0.2, 0.35)
        eye = target.center + np.asarray(
            [radius * math.cos(yaw), radius * math.sin(yaw), z_offset],
            dtype=np.float32,
        )
        rotation = look_at_opencv(eye, target.center, up)
        poses.append((eye, rotation))
    return poses


def compute_scene_focus(targets: list[ReplicaOracleTarget]) -> tuple[np.ndarray, float]:
    if not targets:
        raise ValueError("At least one target is required to compute scene focus")
    centers = np.stack([target.center for target in targets], axis=0).astype(np.float32)
    weights = np.asarray([max(target.volume, 1e-6) ** 0.5 for target in targets], dtype=np.float32)
    weights = weights / weights.sum()
    focus_center = np.sum(centers * weights[:, None], axis=0)
    scene_radius = max(
        float(np.linalg.norm(target.center - focus_center) + 0.5 * max(target.sizes.tolist()))
        for target in targets
    )
    return focus_center.astype(np.float32), max(scene_radius, 0.25)


def camera_pose_key(position: np.ndarray) -> tuple[float, ...]:
    return tuple(np.round(np.asarray(position, dtype=np.float32), 4).tolist())


def azimuth_bin_index(
    position: np.ndarray,
    focus_center: np.ndarray,
    *,
    bin_count: int,
) -> int:
    count = max(int(bin_count), 1)
    rel_xy = np.asarray(position, dtype=np.float32)[:2] - np.asarray(focus_center, dtype=np.float32)[:2]
    angle = math.atan2(float(rel_xy[1]), float(rel_xy[0]))
    normalized = (angle + math.pi) / (2.0 * math.pi)
    return int(math.floor(normalized * count)) % count


def accepted_azimuth_histogram(
    frames: list[CameraFrame],
    focus_center: np.ndarray,
    *,
    bin_count: int,
) -> list[int]:
    counts = [0] * max(int(bin_count), 1)
    for frame in frames:
        counts[azimuth_bin_index(frame.position, focus_center, bin_count=bin_count)] += 1
    return counts


def generate_scene_orbit_camera_poses(
    targets: list[ReplicaOracleTarget],
    *,
    count: int,
    seed: int,
    radius_min: float,
    radius_max: float,
) -> list[tuple[np.ndarray, np.ndarray]]:
    focus_center, focus_radius = compute_scene_focus(targets)
    up = np.asarray([0.0, 0.0, 1.0], dtype=np.float32)
    rng = np.random.default_rng(seed)
    base_radius = float(np.clip(focus_radius * 2.8, radius_min, radius_max))
    max_height = max(float(target.sizes[2]) for target in targets)
    poses: list[tuple[np.ndarray, np.ndarray]] = []
    for index in range(count):
        yaw = (2.0 * math.pi * index / max(count, 1)) + rng.normal(0.0, 0.05)
        radius = float(np.clip(base_radius + rng.normal(0.0, 0.12), radius_min, radius_max))
        z_offset = (0.35 * max_height) + rng.uniform(-0.25, 0.45)
        eye = focus_center + np.asarray(
            [radius * math.cos(yaw), radius * math.sin(yaw), z_offset],
            dtype=np.float32,
        )
        rotation = look_at_opencv(eye, focus_center, up)
        poses.append((eye, rotation))
    return poses


def select_multi_object_candidate_infos(
    candidate_infos: list[dict[str, Any]],
    *,
    total_views: int,
    target_ids: list[int],
    focus_center: np.ndarray,
    selection_mode: str,
    azimuth_bin_count: int,
) -> list[dict[str, Any]]:
    ranked_candidates = sorted(
        candidate_infos,
        key=lambda info: float(info["union_visible_ratio"]),
        reverse=True,
    )
    selected_infos: list[dict[str, Any]] = []
    seen_pose_keys: set[tuple[float, ...]] = set()

    # Ensure every selected target contributes at least one crop when possible.
    for target_id in target_ids:
        target_specific = next(
            (
                info
                for info in ranked_candidates
                if float(info["visible_ratios"].get(target_id, 0.0)) > 0.0
            ),
            None,
        )
        if target_specific is None:
            continue
        pose_key = camera_pose_key(np.asarray(target_specific["position"], dtype=np.float32))
        if pose_key in seen_pose_keys:
            continue
        selected_infos.append(target_specific)
        seen_pose_keys.add(pose_key)

    if selection_mode == "diverse_azimuth":
        binned_candidates: dict[int, list[dict[str, Any]]] = {index: [] for index in range(max(azimuth_bin_count, 1))}
        for info in ranked_candidates:
            bin_index = azimuth_bin_index(
                np.asarray(info["position"], dtype=np.float32),
                focus_center,
                bin_count=azimuth_bin_count,
            )
            binned_candidates[bin_index].append(info)

        while len(selected_infos) < total_views:
            progress = False
            for bin_index in range(max(azimuth_bin_count, 1)):
                bucket = binned_candidates[bin_index]
                while bucket:
                    candidate = bucket.pop(0)
                    pose_key = camera_pose_key(np.asarray(candidate["position"], dtype=np.float32))
                    if pose_key in seen_pose_keys:
                        continue
                    selected_infos.append(candidate)
                    seen_pose_keys.add(pose_key)
                    progress = True
                    break
                if len(selected_infos) >= total_views:
                    break
            if not progress:
                break

    for info in ranked_candidates:
        if len(selected_infos) >= total_views:
            break
        pose_key = camera_pose_key(np.asarray(info["position"], dtype=np.float32))
        if pose_key in seen_pose_keys:
            continue
        selected_infos.append(info)
        seen_pose_keys.add(pose_key)

    return selected_infos[:total_views]


def crop_rgb_by_mask(rgb: np.ndarray, mask: np.ndarray) -> Image.Image:
    if not mask.any():
        return Image.fromarray(rgb)
    ys, xs = np.where(mask)
    y0, y1 = ys.min(), ys.max()
    x0, x1 = xs.min(), xs.max()
    crop = rgb[y0 : y1 + 1, x0 : x1 + 1].copy()
    crop_mask = mask[y0 : y1 + 1, x0 : x1 + 1]
    crop[~crop_mask] = 0
    return Image.fromarray(crop)


def _triangulate_faces(face_indices: Any) -> np.ndarray:
    triangles: list[list[int]] = []
    for polygon in face_indices:
        vertices = [int(value) for value in polygon.tolist()]
        if len(vertices) < 3:
            continue
        for index in range(1, len(vertices) - 1):
            triangles.append([vertices[0], vertices[index], vertices[index + 1]])
    if not triangles:
        raise ValueError("No valid mesh triangles found")
    return np.asarray(triangles, dtype=np.int64)


def _load_mesh_arrays(
    mesh_path: Path,
    *,
    include_object_ids: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None]:
    try:
        from plyfile import PlyData  # type: ignore
    except ImportError as exc:
        raise RuntimeError("plyfile is required to sample Replica mesh points.") from exc

    ply = PlyData.read(mesh_path)
    vertices = ply["vertex"].data
    xyz = np.stack([vertices["x"], vertices["y"], vertices["z"]], axis=1).astype(np.float32)
    rgb = np.stack([vertices["red"], vertices["green"], vertices["blue"]], axis=1).astype(np.uint8)
    face_data = ply["face"].data
    triangles = _triangulate_faces(face_data["vertex_indices"])
    object_ids = None
    if include_object_ids:
        if "object_id" not in (face_data.dtype.names or ()):
            raise ValueError(f"{mesh_path} does not contain face.object_id")
        polygon_object_ids = np.asarray(face_data["object_id"], dtype=np.int32)
        tri_object_ids: list[int] = []
        for object_id, polygon in zip(polygon_object_ids.tolist(), face_data["vertex_indices"]):
            triangle_count = max(len(polygon) - 2, 0)
            tri_object_ids.extend([int(object_id)] * triangle_count)
        object_ids = np.asarray(tri_object_ids, dtype=np.int32)
    return xyz, rgb, triangles, object_ids


def _sample_mesh_triangles(
    xyz: np.ndarray,
    rgb: np.ndarray,
    triangles: np.ndarray,
    *,
    num_points: int,
    seed: int,
    triangle_object_ids: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    tri = triangles
    v0 = xyz[tri[:, 0]]
    v1 = xyz[tri[:, 1]]
    v2 = xyz[tri[:, 2]]
    areas = np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1) * 0.5
    areas = np.maximum(areas, 1e-12)
    probs = areas / areas.sum()

    rng = np.random.default_rng(seed)
    face_indices = rng.choice(len(tri), size=num_points, replace=True, p=probs)
    chosen = tri[face_indices]
    u = rng.random(num_points, dtype=np.float32)
    v = rng.random(num_points, dtype=np.float32)
    swap = u + v > 1.0
    u[swap] = 1.0 - u[swap]
    v[swap] = 1.0 - v[swap]
    w = 1.0 - u - v

    verts0 = xyz[chosen[:, 0]]
    verts1 = xyz[chosen[:, 1]]
    verts2 = xyz[chosen[:, 2]]
    colors0 = rgb[chosen[:, 0]].astype(np.float32)
    colors1 = rgb[chosen[:, 1]].astype(np.float32)
    colors2 = rgb[chosen[:, 2]].astype(np.float32)

    samples = verts0 * w[:, None] + verts1 * u[:, None] + verts2 * v[:, None]
    colors = colors0 * w[:, None] + colors1 * u[:, None] + colors2 * v[:, None]
    object_ids = None
    if triangle_object_ids is not None:
        object_ids = triangle_object_ids[face_indices].astype(np.int32, copy=False)
    return samples.astype(np.float32), np.round(colors).astype(np.uint8), object_ids


def sample_mesh_points(mesh_path: Path, *, num_points: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    xyz, rgb, triangles, _ = _load_mesh_arrays(mesh_path)
    samples, colors, _ = _sample_mesh_triangles(
        xyz,
        rgb,
        triangles,
        num_points=num_points,
        seed=seed,
    )
    return samples, colors


def sample_semantic_mesh_points(
    mesh_path: Path,
    *,
    num_points: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xyz, rgb, triangles, triangle_object_ids = _load_mesh_arrays(mesh_path, include_object_ids=True)
    samples, colors, object_ids = _sample_mesh_triangles(
        xyz,
        rgb,
        triangles,
        num_points=num_points,
        seed=seed,
        triangle_object_ids=triangle_object_ids,
    )
    assert object_ids is not None
    return samples, colors, object_ids


def write_colmap_text_scene(
    scene_root: Path,
    *,
    frames: list[CameraFrame],
    width: int,
    height: int,
    hfov_deg: float,
    points_xyz: np.ndarray,
    points_rgb: np.ndarray,
) -> None:
    images_dir = scene_root / "images"
    sparse_dir = scene_root / "sparse" / "0"
    images_dir.mkdir(parents=True, exist_ok=True)
    sparse_dir.mkdir(parents=True, exist_ok=True)

    fx, fy, cx, cy = camera_intrinsics(width, height, hfov_deg)
    cameras_path = sparse_dir / "cameras.txt"
    images_path = sparse_dir / "images.txt"
    points_path = sparse_dir / "points3D.txt"
    test_path = sparse_dir / "test.txt"

    cameras_path.write_text(
        "\n".join(
            [
                "# Camera list with one line of data per camera:",
                "#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]",
                f"1 PINHOLE {width} {height} {fx} {fy} {cx} {cy}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    image_lines = [
        "# Image list with two lines of data per image:",
        "#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME",
        "#   POINTS2D[] as (X, Y, POINT3D_ID)",
    ]
    test_names: list[str] = []
    for index, frame in enumerate(frames, start=1):
        qvec, tvec = world_to_colmap_pose(frame.rotation_cam2world, frame.position)
        image_lines.append(
            f"{index} {qvec[0]} {qvec[1]} {qvec[2]} {qvec[3]} {tvec[0]} {tvec[1]} {tvec[2]} 1 {frame.image_name}"
        )
        image_lines.append("")
        if frame.split == "test":
            test_names.append(frame.image_name)
    images_path.write_text("\n".join(image_lines) + "\n", encoding="utf-8")
    test_path.write_text("\n".join(test_names) + ("\n" if test_names else ""), encoding="utf-8")

    point_lines = [
        "# 3D point list with one line of data per point:",
        "#   POINT3D_ID, X, Y, Z, R, G, B, ERROR",
    ]
    for index, (xyz, rgb) in enumerate(zip(points_xyz, points_rgb), start=1):
        point_lines.append(
            f"{index} {xyz[0]} {xyz[1]} {xyz[2]} {int(rgb[0])} {int(rgb[1])} {int(rgb[2])} 1.0"
        )
    points_path.write_text("\n".join(point_lines) + "\n", encoding="utf-8")


class ReplicaHabitatRenderer:
    def __init__(
        self,
        scene_root: Path,
        *,
        width: int,
        height: int,
        hfov_deg: float,
    ) -> None:
        try:
            import habitat_sim  # type: ignore
            import quaternion  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "Replica export requires habitat_sim and numpy-quaternion in the current Python environment."
            ) from exc

        self._habitat_sim = habitat_sim
        self._quaternion = quaternion
        self.width = width
        self.height = height
        self.hfov_deg = hfov_deg

        sim_cfg = habitat_sim.SimulatorConfiguration()
        sim_cfg.scene_dataset_config_file = str(scene_root.parent / "replica.scene_dataset_config.json")
        sim_cfg.scene_id = str(scene_root / "habitat" / "replica_stage.stage_config.json")
        sim_cfg.load_semantic_mesh = True

        rgb_sensor = habitat_sim.CameraSensorSpec()
        rgb_sensor.uuid = "color"
        rgb_sensor.sensor_type = habitat_sim.SensorType.COLOR
        rgb_sensor.resolution = [height, width]
        rgb_sensor.hfov = hfov_deg

        semantic_sensor = habitat_sim.CameraSensorSpec()
        semantic_sensor.uuid = "semantic"
        semantic_sensor.sensor_type = habitat_sim.SensorType.SEMANTIC
        semantic_sensor.resolution = [height, width]
        semantic_sensor.hfov = hfov_deg

        agent_cfg = habitat_sim.agent.AgentConfiguration(
            sensor_specifications=[rgb_sensor, semantic_sensor]
        )
        cfg = habitat_sim.Configuration(sim_cfg, [agent_cfg])
        self._sim = habitat_sim.Simulator(cfg)
        self._agent = self._sim.initialize_agent(agent_id=0)

    def close(self) -> None:
        self._sim.close()

    def _opencv_to_habitat_quaternion(self, rotation_cam2world: np.ndarray):
        habitat_sim = self._habitat_sim
        quaternion = self._quaternion
        r_opencv_to_habitat = np.stack(
            (habitat_sim.geo.RIGHT, -habitat_sim.geo.UP, habitat_sim.geo.FRONT),
            axis=0,
        )
        return quaternion.from_rotation_matrix(rotation_cam2world @ r_opencv_to_habitat.T)

    def render(self, *, position: np.ndarray, rotation_cam2world: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        habitat_sim = self._habitat_sim
        state = habitat_sim.AgentState()
        state.position = position
        state.rotation = self._opencv_to_habitat_quaternion(rotation_cam2world)
        self._agent.set_state(state)
        observations = self._sim.get_sensor_observations(0)
        rgb = np.asarray(observations["color"])[..., :3].copy()
        semantic = np.asarray(observations["semantic"]).copy()
        return rgb, semantic


class ReplicaPointRenderer:
    def __init__(
        self,
        scene_root: Path,
        *,
        width: int,
        height: int,
        hfov_deg: float,
        sample_count: int,
        seed: int,
    ) -> None:
        self.width = width
        self.height = height
        self.hfov_deg = hfov_deg
        self.fx, self.fy, self.cx, self.cy = camera_intrinsics(width, height, hfov_deg)
        self.points_xyz, self.points_rgb, self.points_object_id = sample_semantic_mesh_points(
            scene_root / "habitat" / "mesh_semantic.ply",
            num_points=sample_count,
            seed=seed,
        )

    def close(self) -> None:
        return None

    def render(self, *, position: np.ndarray, rotation_cam2world: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        rotation_world2cam = rotation_cam2world.T.astype(np.float32)
        camera_xyz = (self.points_xyz - position[None, :]) @ rotation_world2cam.T
        depth = camera_xyz[:, 2]
        valid = depth > 1e-4
        if not np.any(valid):
            rgb = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            semantic = np.full((self.height, self.width), -1, dtype=np.int32)
            return rgb, semantic

        xyz = camera_xyz[valid]
        rgb_values = self.points_rgb[valid]
        object_ids = self.points_object_id[valid]
        z = xyz[:, 2]
        u = np.rint((self.fx * (xyz[:, 0] / z)) + self.cx).astype(np.int32)
        v = np.rint((self.fy * (xyz[:, 1] / z)) + self.cy).astype(np.int32)
        in_bounds = (u >= 0) & (u < self.width) & (v >= 0) & (v < self.height)
        if not np.any(in_bounds):
            rgb = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            semantic = np.full((self.height, self.width), -1, dtype=np.int32)
            return rgb, semantic

        u = u[in_bounds]
        v = v[in_bounds]
        z = z[in_bounds]
        rgb_values = rgb_values[in_bounds]
        object_ids = object_ids[in_bounds]

        order = np.argsort(z, kind="stable")[::-1]
        u = u[order]
        v = v[order]
        rgb_values = rgb_values[order]
        object_ids = object_ids[order]

        rgb = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        semantic = np.full((self.height, self.width), -1, dtype=np.int32)
        rgb[v, u] = rgb_values
        semantic[v, u] = object_ids
        return rgb, semantic


def export_replica_oracle_scene(
    *,
    raw_root: Path,
    output_root: Path,
    scene_id: str,
    category: str,
    width: int,
    height: int,
    hfov_deg: float,
    train_views: int,
    test_views: int,
    mesh_point_count: int,
    seed: int,
    radius_min: float,
    radius_max: float,
    min_visible_ratio: float,
    feature_config: FeatureExtractorConfig,
    render_point_count: int = 1_000_000,
) -> Path:
    scene_root = raw_root / scene_id
    target = select_largest_target(scene_root, category=category)
    output_scene_root = output_root / scene_id
    images_dir = output_scene_root / "images"
    oracle_dir = output_scene_root / "oracle"
    crops_dir = oracle_dir / "crops"
    images_dir.mkdir(parents=True, exist_ok=True)
    crops_dir.mkdir(parents=True, exist_ok=True)

    total_views = train_views + test_views
    render_backend = "habitat_sim"
    try:
        renderer = ReplicaHabitatRenderer(scene_root, width=width, height=height, hfov_deg=hfov_deg)
    except RuntimeError:
        renderer = ReplicaPointRenderer(
            scene_root,
            width=width,
            height=height,
            hfov_deg=hfov_deg,
            sample_count=render_point_count,
            seed=seed,
        )
        render_backend = "semantic_point_renderer"
    try:
        accepted: list[CameraFrame] = []
        crop_paths: list[Path] = []
        candidate_poses = generate_orbit_camera_poses(
            target,
            count=max(total_views * 12, 64),
            seed=seed,
            radius_min=radius_min,
            radius_max=radius_max,
        )
        for candidate_index, (position, rotation) in enumerate(candidate_poses):
            rgb, semantic = renderer.render(position=position, rotation_cam2world=rotation)
            visible_ratio = float((semantic == target.object_id).mean())
            if visible_ratio < min_visible_ratio:
                continue
            image_name = f"{len(accepted):05d}.png"
            Image.fromarray(rgb).save(images_dir / image_name)
            crop = crop_rgb_by_mask(rgb, semantic == target.object_id)
            crop.save(crops_dir / image_name)
            accepted.append(
                CameraFrame(
                    image_name=image_name,
                    position=position,
                    rotation_cam2world=rotation,
                    visible_ratio=visible_ratio,
                    split="train",
                )
            )
            crop_paths.append(crops_dir / image_name)
            if len(accepted) >= total_views:
                break

        if len(accepted) < total_views:
            raise RuntimeError(
                f"Only collected {len(accepted)} valid views for {scene_id}, need {total_views}"
            )
    finally:
        renderer.close()

    test_indices = set(np.linspace(0, len(accepted) - 1, num=test_views, dtype=int).tolist())
    for index, frame in enumerate(accepted):
        frame.split = "test" if index in test_indices else "train"

    points_xyz, points_rgb = sample_mesh_points(scene_root / "mesh.ply", num_points=mesh_point_count, seed=seed)
    write_colmap_text_scene(
        output_scene_root,
        frames=accepted,
        width=width,
        height=height,
        hfov_deg=hfov_deg,
        points_xyz=points_xyz,
        points_rgb=points_rgb,
    )

    query_feature = extract_image_features(crop_paths, config=feature_config)
    query_feature_path = oracle_dir / "query_feature.npy"
    np.save(query_feature_path, query_feature.astype(np.float32))

    scene_meta = {
        "dataset": "replica",
        "raw_scene_id": scene_id,
        "subset_id": scene_id,
        "export_type": "colmap_text_gt",
        "frame_count": len(accepted),
        "notes": [
            "Rendered from Replica GT mesh using the configured Replica renderer backend.",
            "Camera poses and sparse points are generated from ground truth, not COLMAP estimation.",
        ],
        "render_backend": render_backend,
        "oracle_target_path": "oracle/target.json",
        "oracle_query_feature_path": "oracle/query_feature.npy",
    }
    (output_scene_root / "scene_meta.json").write_text(json.dumps(scene_meta, indent=2), encoding="utf-8")

    target_payload = {
        "scene_id": target.scene_id,
        "object_id": target.object_id,
        "category": target.category,
        "center": target.center.tolist(),
        "sizes": target.sizes.tolist(),
        "rotation_xyzw": target.rotation_xyzw.tolist(),
        "volume": target.volume,
        "query_feature_path": "oracle/query_feature.npy",
        "crop_dir": "oracle/crops",
        "view_count": len(accepted),
        "test_view_count": test_views,
        "train_view_count": len(accepted) - test_views,
    }
    (oracle_dir / "target.json").write_text(json.dumps(target_payload, indent=2), encoding="utf-8")
    return output_scene_root


def export_replica_multi_oracle_scene(
    *,
    raw_root: Path,
    output_root: Path,
    scene_id: str,
    categories: list[str] | tuple[str, ...],
    max_objects: int,
    width: int,
    height: int,
    hfov_deg: float,
    train_views: int,
    test_views: int,
    mesh_point_count: int,
    seed: int,
    radius_min: float,
    radius_max: float,
    min_visible_ratio: float,
    selection_mode: str = "top_visibility",
    azimuth_bin_count: int = 8,
    candidate_pose_count: int | None = None,
    render_point_count: int = 1_000_000,
) -> Path:
    scene_root = raw_root / scene_id
    targets = select_top_targets(scene_root, categories=list(categories), max_objects=max_objects)
    focus_center, _ = compute_scene_focus(targets)
    output_scene_root = output_root / scene_id
    images_dir = output_scene_root / "images"
    oracle_dir = output_scene_root / "oracle"
    objects_dir = oracle_dir / "objects"
    images_dir.mkdir(parents=True, exist_ok=True)
    objects_dir.mkdir(parents=True, exist_ok=True)

    total_views = train_views + test_views
    render_backend = "habitat_sim"
    try:
        renderer = ReplicaHabitatRenderer(scene_root, width=width, height=height, hfov_deg=hfov_deg)
    except RuntimeError:
        renderer = ReplicaPointRenderer(
            scene_root,
            width=width,
            height=height,
            hfov_deg=hfov_deg,
            sample_count=render_point_count,
            seed=seed,
        )
        render_backend = "semantic_point_renderer"

    target_ids = [target.object_id for target in targets]
    crop_paths: dict[int, list[Path]] = {target.object_id: [] for target in targets}
    effective_min_visible_ratio = min_visible_ratio
    try:
        accepted: list[CameraFrame] = []
        candidate_poses = generate_scene_orbit_camera_poses(
            targets,
            count=int(candidate_pose_count) if candidate_pose_count is not None else max(total_views * 48, 512),
            seed=seed,
            radius_min=radius_min,
            radius_max=radius_max,
        )
        candidate_infos: list[dict[str, Any]] = []
        for position, rotation in candidate_poses:
            _, semantic = renderer.render(position=position, rotation_cam2world=rotation)
            visible_ratios = {
                target_id: float((semantic == target_id).mean())
                for target_id in target_ids
            }
            union_visible_ratio = float(np.isin(semantic, target_ids).mean())
            candidate_infos.append(
                {
                    "position": np.asarray(position, dtype=np.float32),
                    "rotation": np.asarray(rotation, dtype=np.float32),
                    "visible_ratios": visible_ratios,
                    "union_visible_ratio": union_visible_ratio,
                }
            )

        strong_candidates = [
            info for info in candidate_infos if float(info["union_visible_ratio"]) >= min_visible_ratio
        ]
        if len(strong_candidates) >= total_views:
            ranked_candidates = strong_candidates
        else:
            ranked_candidates = [
                info for info in candidate_infos if float(info["union_visible_ratio"]) > 0.0
            ]
            effective_min_visible_ratio = 0.0

        if len(ranked_candidates) < total_views:
            raise RuntimeError(
                f"Only collected {len(ranked_candidates)} usable multi-object views for {scene_id}, need {total_views}"
            )

        selected_infos = select_multi_object_candidate_infos(
            ranked_candidates,
            total_views=total_views,
            target_ids=target_ids,
            focus_center=focus_center,
            selection_mode=selection_mode,
            azimuth_bin_count=azimuth_bin_count,
        )
        for info in selected_infos:
            rgb, semantic = renderer.render(
                position=np.asarray(info["position"], dtype=np.float32),
                rotation_cam2world=np.asarray(info["rotation"], dtype=np.float32),
            )
            image_name = f"{len(accepted):05d}.png"
            Image.fromarray(rgb).save(images_dir / image_name)
            accepted.append(
                CameraFrame(
                    image_name=image_name,
                    position=np.asarray(info["position"], dtype=np.float32),
                    rotation_cam2world=np.asarray(info["rotation"], dtype=np.float32),
                    visible_ratio=float(info["union_visible_ratio"]),
                    split="train",
                    visible_ratios=dict(info["visible_ratios"]),
                )
            )
            for target in targets:
                mask = semantic == target.object_id
                if not mask.any():
                    continue
                object_dir = objects_dir / str(target.object_id)
                crops_dir = object_dir / "crops"
                crops_dir.mkdir(parents=True, exist_ok=True)
                crop = crop_rgb_by_mask(rgb, mask)
                crop_path = crops_dir / image_name
                crop.save(crop_path)
                crop_paths[target.object_id].append(crop_path)
    finally:
        renderer.close()

    test_indices = set(np.linspace(0, len(accepted) - 1, num=test_views, dtype=int).tolist())
    for index, frame in enumerate(accepted):
        frame.split = "test" if index in test_indices else "train"

    missing_crops = [str(target.object_id) for target in targets if not crop_paths[target.object_id]]
    if missing_crops:
        raise RuntimeError(
            f"Failed to collect object crops for targets {', '.join(missing_crops)} in {scene_id}"
        )

    points_xyz, points_rgb = sample_mesh_points(scene_root / "mesh.ply", num_points=mesh_point_count, seed=seed)
    write_colmap_text_scene(
        output_scene_root,
        frames=accepted,
        width=width,
        height=height,
        hfov_deg=hfov_deg,
        points_xyz=points_xyz,
        points_rgb=points_rgb,
    )

    scene_meta = {
        "dataset": "replica",
        "raw_scene_id": scene_id,
        "subset_id": scene_id,
        "export_type": "colmap_text_gt_multi_object",
        "frame_count": len(accepted),
        "train_view_count": len(accepted) - test_views,
        "test_view_count": test_views,
        "notes": [
            "Rendered from Replica GT mesh using a scene-centric multi-object camera path.",
            "Camera poses and sparse points are generated from ground truth, not COLMAP estimation.",
        ],
        "render_backend": render_backend,
        "oracle_targets_path": "oracle/targets.json",
        "oracle_categories": list(categories),
        "oracle_max_objects": len(targets),
        "oracle_effective_min_visible_ratio": effective_min_visible_ratio,
        "camera_selection_mode": selection_mode,
        "camera_azimuth_bin_count": int(azimuth_bin_count),
        "camera_azimuth_histogram": accepted_azimuth_histogram(
            accepted,
            focus_center,
            bin_count=azimuth_bin_count,
        ),
        "candidate_pose_count": len(candidate_poses),
    }
    (output_scene_root / "scene_meta.json").write_text(json.dumps(scene_meta, indent=2), encoding="utf-8")

    targets_payload = []
    for target in targets:
        entry = {
            "scene_id": target.scene_id,
            "object_id": target.object_id,
            "category": target.category,
            "center": target.center.tolist(),
            "sizes": target.sizes.tolist(),
            "rotation_xyzw": target.rotation_xyzw.tolist(),
            "volume": target.volume,
            "crop_dir": f"oracle/objects/{target.object_id}/crops",
            "query_feature_paths": {},
            "visible_frame_count": len(crop_paths[target.object_id]),
        }
        targets_payload.append(entry)

    (oracle_dir / "targets.json").write_text(json.dumps(targets_payload, indent=2), encoding="utf-8")
    if targets_payload:
        primary_target = dict(targets_payload[0])
        primary_target["view_count"] = len(accepted)
        primary_target["test_view_count"] = test_views
        primary_target["train_view_count"] = len(accepted) - test_views
        (oracle_dir / "target.json").write_text(json.dumps(primary_target, indent=2), encoding="utf-8")
    return output_scene_root
