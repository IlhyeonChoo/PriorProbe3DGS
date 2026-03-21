from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.gaussian_affine import quaternion_to_rotation_matrix, transform_gaussian_vertex


def _gaussian_covariance(vertex: np.ndarray) -> np.ndarray:
    scales = np.exp(
        np.asarray([vertex["scale_0"], vertex["scale_1"], vertex["scale_2"]], dtype=np.float64)
    )
    rotation = quaternion_to_rotation_matrix(
        np.asarray([vertex["rot_0"], vertex["rot_1"], vertex["rot_2"], vertex["rot_3"]], dtype=np.float64)
    )
    return rotation @ np.diag(np.square(scales)) @ rotation.T


def test_transform_gaussian_vertex_applies_affine_to_mean_and_covariance() -> None:
    dtype = [
        ("x", "f4"),
        ("y", "f4"),
        ("z", "f4"),
        ("opacity", "f4"),
        ("f_dc_0", "f4"),
        ("f_dc_1", "f4"),
        ("f_dc_2", "f4"),
        ("scale_0", "f4"),
        ("scale_1", "f4"),
        ("scale_2", "f4"),
        ("rot_0", "f4"),
        ("rot_1", "f4"),
        ("rot_2", "f4"),
        ("rot_3", "f4"),
    ]
    vertex = np.zeros(1, dtype=dtype)
    vertex["x"] = 1.0
    vertex["y"] = 2.0
    vertex["z"] = 3.0
    vertex["opacity"] = 0.1
    vertex["scale_0"] = np.log(0.5)
    vertex["scale_1"] = np.log(1.0)
    vertex["scale_2"] = np.log(1.5)
    vertex["rot_0"] = 1.0

    rotation = np.asarray(
        [
            [0.0, -1.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    scale = np.asarray([2.0, 3.0, 4.0], dtype=np.float64)
    translation = np.asarray([10.0, 20.0, 30.0], dtype=np.float64)

    transformed = transform_gaussian_vertex(
        vertex,
        rotation_matrix=rotation,
        scale=scale,
        translation=translation,
    )

    affine = rotation @ np.diag(scale)
    expected_xyz = np.asarray([[1.0, 2.0, 3.0]], dtype=np.float64) @ affine.T + translation
    actual_xyz = np.stack([transformed["x"], transformed["y"], transformed["z"]], axis=1)
    assert np.allclose(actual_xyz, expected_xyz, atol=1e-5)

    original_cov = _gaussian_covariance(vertex[0])
    expected_cov = affine @ original_cov @ affine.T
    actual_cov = _gaussian_covariance(transformed[0])
    assert np.allclose(actual_cov, expected_cov, atol=1e-5)
