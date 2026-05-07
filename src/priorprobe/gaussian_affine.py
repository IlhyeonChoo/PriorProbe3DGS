from __future__ import annotations

import numpy as np


GAUSSIAN_REQUIRED_FIELDS = {
    "x",
    "y",
    "z",
    "opacity",
    "scale_0",
    "scale_1",
    "scale_2",
    "rot_0",
    "rot_1",
    "rot_2",
    "rot_3",
}


def detect_asset_format(vertex: np.ndarray) -> str:
    names = set(vertex.dtype.names or ())
    if GAUSSIAN_REQUIRED_FIELDS.issubset(names):
        return "gaussian"
    if {"red", "green", "blue"}.issubset(names):
        return "point_cloud"
    raise ValueError(f"Unsupported PLY schema: {vertex.dtype.names}")


def parse_scale(scale_value: object) -> np.ndarray:
    if isinstance(scale_value, (int, float)):
        scalar = float(scale_value)
        return np.asarray([scalar, scalar, scalar], dtype=np.float64)

    scale = np.asarray(scale_value, dtype=np.float64).reshape(-1)
    if scale.shape != (3,):
        raise ValueError("scale must be a scalar or a length-3 vector")
    return scale


def quaternion_to_rotation_matrix(quaternion_wxyz: np.ndarray) -> np.ndarray:
    quat = np.asarray(quaternion_wxyz, dtype=np.float64).reshape(4)
    norm = float(np.linalg.norm(quat))
    if norm <= 1e-12:
        return np.eye(3, dtype=np.float64)
    quat = quat / norm
    w, x, y, z = quat.tolist()
    return np.asarray(
        [
            [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - w * z), 2.0 * (x * z + w * y)],
            [2.0 * (x * y + w * z), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - w * x)],
            [2.0 * (x * z - w * y), 2.0 * (y * z + w * x), 1.0 - 2.0 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )


def rotation_matrix_to_quaternion(rotation_matrix: np.ndarray) -> np.ndarray:
    m = np.asarray(rotation_matrix, dtype=np.float64).reshape(3, 3)
    trace = float(np.trace(m))
    if trace > 0.0:
        s = np.sqrt(trace + 1.0) * 2.0
        w = 0.25 * s
        x = (m[2, 1] - m[1, 2]) / s
        y = (m[0, 2] - m[2, 0]) / s
        z = (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2.0
        w = (m[2, 1] - m[1, 2]) / s
        x = 0.25 * s
        y = (m[0, 1] + m[1, 0]) / s
        z = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2.0
        w = (m[0, 2] - m[2, 0]) / s
        x = (m[0, 1] + m[1, 0]) / s
        y = 0.25 * s
        z = (m[1, 2] + m[2, 1]) / s
    else:
        s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2.0
        w = (m[1, 0] - m[0, 1]) / s
        x = (m[0, 2] + m[2, 0]) / s
        y = (m[1, 2] + m[2, 1]) / s
        z = 0.25 * s
    quat = np.asarray([w, x, y, z], dtype=np.float64)
    norm = float(np.linalg.norm(quat))
    if norm <= 1e-12:
        return np.asarray([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    return quat / norm


def build_affine_matrix(
    *,
    rotation_matrix: np.ndarray,
    scale: np.ndarray,
) -> np.ndarray:
    rotation = np.asarray(rotation_matrix, dtype=np.float64).reshape(3, 3)
    scale_vec = np.asarray(scale, dtype=np.float64).reshape(3)
    return rotation @ np.diag(scale_vec)


def transform_positions(
    xyz: np.ndarray,
    *,
    affine_matrix: np.ndarray,
    translation: np.ndarray,
) -> np.ndarray:
    return np.asarray(xyz, dtype=np.float64) @ affine_matrix.T + np.asarray(translation, dtype=np.float64)


def _ensure_right_handed(rotation_matrix: np.ndarray) -> np.ndarray:
    output = np.asarray(rotation_matrix, dtype=np.float64).copy()
    if np.linalg.det(output) < 0.0:
        output[:, 0] *= -1.0
    return output


def transform_gaussian_vertex(
    vertex: np.ndarray,
    *,
    rotation_matrix: np.ndarray,
    scale: np.ndarray,
    translation: np.ndarray,
) -> np.ndarray:
    transformed = np.array(vertex, copy=True)
    affine_matrix = build_affine_matrix(rotation_matrix=np.asarray(rotation_matrix), scale=np.asarray(scale))

    xyz = np.stack([transformed["x"], transformed["y"], transformed["z"]], axis=1).astype(np.float64)
    xyz = transform_positions(xyz, affine_matrix=affine_matrix, translation=np.asarray(translation))
    transformed["x"] = xyz[:, 0].astype(np.float32)
    transformed["y"] = xyz[:, 1].astype(np.float32)
    transformed["z"] = xyz[:, 2].astype(np.float32)

    scales = np.stack(
        [transformed["scale_0"], transformed["scale_1"], transformed["scale_2"]],
        axis=1,
    ).astype(np.float64)
    scales = np.exp(scales)
    rotations = np.stack(
        [transformed["rot_0"], transformed["rot_1"], transformed["rot_2"], transformed["rot_3"]],
        axis=1,
    ).astype(np.float64)

    new_scales = np.empty_like(scales, dtype=np.float64)
    new_rotations = np.empty_like(rotations, dtype=np.float64)

    for index in range(scales.shape[0]):
        base_rotation = quaternion_to_rotation_matrix(rotations[index])
        base_covariance = base_rotation @ np.diag(np.square(scales[index])) @ base_rotation.T
        transformed_covariance = affine_matrix @ base_covariance @ affine_matrix.T
        eigenvalues, eigenvectors = np.linalg.eigh(transformed_covariance)
        eigenvalues = np.maximum(eigenvalues, 1e-12)
        eigenvectors = _ensure_right_handed(eigenvectors)
        new_scales[index] = np.sqrt(eigenvalues)
        new_rotations[index] = rotation_matrix_to_quaternion(eigenvectors)

    transformed["scale_0"] = np.log(new_scales[:, 0]).astype(np.float32)
    transformed["scale_1"] = np.log(new_scales[:, 1]).astype(np.float32)
    transformed["scale_2"] = np.log(new_scales[:, 2]).astype(np.float32)
    transformed["rot_0"] = new_rotations[:, 0].astype(np.float32)
    transformed["rot_1"] = new_rotations[:, 1].astype(np.float32)
    transformed["rot_2"] = new_rotations[:, 2].astype(np.float32)
    transformed["rot_3"] = new_rotations[:, 3].astype(np.float32)
    return transformed
