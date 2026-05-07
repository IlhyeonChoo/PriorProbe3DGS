from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.gaussian_prior_diagnostics import (
    allocate_total_budget,
    expanded_aabb_from_positions,
    point_keep_mask_outside_aabbs,
    reset_gaussian_sh,
    stable_seed,
    subsample_structured_vertex,
)


def _gaussian_vertex(count: int) -> np.ndarray:
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
        ("f_rest_0", "f4"),
        ("f_rest_1", "f4"),
    ]
    vertex = np.zeros((count,), dtype=dtype)
    vertex["x"] = np.arange(count, dtype=np.float32)
    vertex["y"] = 1.0
    vertex["z"] = 2.0
    vertex["opacity"] = 0.5
    vertex["scale_0"] = 0.1
    vertex["scale_1"] = 0.2
    vertex["scale_2"] = 0.3
    vertex["rot_0"] = 1.0
    vertex["f_dc_0"] = 0.7
    vertex["f_dc_1"] = 0.8
    vertex["f_dc_2"] = 0.9
    vertex["f_rest_0"] = 1.1
    vertex["f_rest_1"] = 1.2
    return vertex


def test_allocate_total_budget_preserves_total() -> None:
    allocated = allocate_total_budget([10000, 20000, 30000, 40000], 25000)

    assert sum(allocated) == 25000
    assert allocated == [2500, 5000, 7500, 10000]


def test_subsample_structured_vertex_is_deterministic() -> None:
    vertex = _gaussian_vertex(10)
    seed = stable_seed("room_0", "chair_01", 42)

    first = subsample_structured_vertex(vertex, keep_count=4, seed=seed)
    second = subsample_structured_vertex(vertex, keep_count=4, seed=seed)

    assert np.array_equal(first, second)
    assert first.shape[0] == 4


def test_reset_gaussian_sh_zeroes_only_sh_fields() -> None:
    vertex = _gaussian_vertex(3)

    reset = reset_gaussian_sh(vertex, mode="zero_all")

    assert np.allclose(reset["x"], vertex["x"])
    assert np.allclose(reset["opacity"], vertex["opacity"])
    assert np.allclose(reset["scale_0"], vertex["scale_0"])
    assert np.allclose(reset["rot_0"], vertex["rot_0"])
    assert np.allclose(reset["f_dc_0"], 0.0)
    assert np.allclose(reset["f_dc_1"], 0.0)
    assert np.allclose(reset["f_rest_0"], 0.0)
    assert np.allclose(reset["f_rest_1"], 0.0)


def test_point_keep_mask_outside_aabbs_filters_inside_points() -> None:
    points = np.asarray(
        [
            [0.0, 0.0, 0.0],
            [0.5, 0.5, 0.5],
            [3.0, 3.0, 3.0],
        ],
        dtype=np.float32,
    )
    aabb = expanded_aabb_from_positions(
        np.asarray([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]], dtype=np.float32),
        margin_scale=1.0,
        margin_min_m=0.0,
    )

    keep_mask = point_keep_mask_outside_aabbs(points, [aabb])

    assert keep_mask.tolist() == [False, False, True]
