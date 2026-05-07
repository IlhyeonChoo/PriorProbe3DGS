from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
from plyfile import PlyData, PlyElement


ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    script_path = ROOT / "scripts" / "collect_prior_position_fine_sweep.py"
    spec = importlib.util.spec_from_file_location("collect_prior_position_fine_sweep", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_test_vertex(path: Path, xyz: np.ndarray) -> None:
    dtype = [
        ("x", "f4"), ("y", "f4"), ("z", "f4"),
        ("nx", "f4"), ("ny", "f4"), ("nz", "f4"),
        ("f_dc_0", "f4"), ("f_dc_1", "f4"), ("f_dc_2", "f4"),
    ]
    dtype.extend((f"f_rest_{index}", "f4") for index in range(45))
    dtype.extend([
        ("opacity", "f4"),
        ("scale_0", "f4"), ("scale_1", "f4"), ("scale_2", "f4"),
        ("rot_0", "f4"), ("rot_1", "f4"), ("rot_2", "f4"), ("rot_3", "f4"),
    ])
    vertex = np.zeros(xyz.shape[0], dtype=dtype)
    vertex["x"] = xyz[:, 0]
    vertex["y"] = xyz[:, 1]
    vertex["z"] = xyz[:, 2]
    vertex["rot_0"] = 1.0
    path.parent.mkdir(parents=True, exist_ok=True)
    PlyData([PlyElement.describe(vertex, "vertex")]).write(path)


def test_aligned_base_vertex_uses_override_source_prior(tmp_path: Path) -> None:
    module = _load_module()
    source_path = tmp_path / "source.ply"
    _write_test_vertex(source_path, np.asarray([[1.0, 2.0, 3.0]], dtype=np.float32))

    selected = {
        "target_object_id": 77,
        "aligned_prior": str(tmp_path / "unused_aligned.ply"),
        "alignment": {
            "rotation_matrix": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            "scale": [1.0, 1.0, 1.0],
            "translation": [0.5, -0.5, 1.0],
        },
    }

    vertex = module._aligned_base_vertex(selected, {77: source_path})

    assert abs(float(vertex["x"][0]) - 1.5) < 1e-6
    assert abs(float(vertex["y"][0]) - 1.5) < 1e-6
    assert abs(float(vertex["z"][0]) - 4.0) < 1e-6


def test_aligned_base_vertex_uses_alignment_debug_rotation_fallback(tmp_path: Path) -> None:
    module = _load_module()
    source_path = tmp_path / "source_rotated.ply"
    _write_test_vertex(source_path, np.asarray([[1.0, 0.0, 0.0]], dtype=np.float32))

    selected = {
        "target_object_id": 77,
        "aligned_prior": str(tmp_path / "unused_aligned.ply"),
        "alignment": {
            "scale": [1.0, 1.0, 1.0],
            "translation": [0.0, 0.0, 0.0],
        },
        "alignment_debug": {
            "target_rotation_matrix": [
                [0.0, -1.0, 0.0],
                [1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0],
            ]
        },
    }

    vertex = module._aligned_base_vertex(selected, {77: source_path})

    assert abs(float(vertex["x"][0]) - 0.0) < 1e-6
    assert abs(float(vertex["y"][0]) - 1.0) < 1e-6
    assert abs(float(vertex["z"][0]) - 0.0) < 1e-6
