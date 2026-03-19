from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.insertion.alignment_search import (
    TargetBox,
    build_scene_points_in_any_target_mask,
    choose_alignment_candidate,
)


def _write_point_cloud_ply(path: Path, points: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "ply",
        "format ascii 1.0",
        f"element vertex {points.shape[0]}",
        "property float x",
        "property float y",
        "property float z",
        "property float nx",
        "property float ny",
        "property float nz",
        "property uchar red",
        "property uchar green",
        "property uchar blue",
        "end_header",
    ]
    for xyz in points:
        lines.append(f"{xyz[0]} {xyz[1]} {xyz[2]} 0 0 1 255 255 255")
    path.write_text("\n".join(lines), encoding="utf-8")


def _make_target(
    *,
    object_id: int = 58,
    category: str = "table",
    center: tuple[float, float, float] = (1.0, 2.0, 0.5),
    sizes: tuple[float, float, float] = (2.0, 4.0, 6.0),
) -> TargetBox:
    return TargetBox(
        object_id=object_id,
        category=category,
        center=np.asarray(center, dtype=np.float32),
        sizes=np.asarray(sizes, dtype=np.float32),
        rotation_matrix=np.eye(3, dtype=np.float32),
    )


def test_choose_alignment_candidate_uses_floor_anchor_and_anisotropic_scale(tmp_path: Path) -> None:
    prior_seed_path = tmp_path / "prior_floor_seed.ply"
    prior_points = np.asarray(
        [
            [-0.5, -0.5, 0.0],
            [0.5, -0.5, 0.0],
            [-0.5, 0.5, 1.0],
            [0.5, 0.5, 1.0],
        ],
        dtype=np.float32,
    )
    _write_point_cloud_ply(prior_seed_path, prior_points)

    target = _make_target()
    scene_points = np.asarray(
        [
            [0.0, 0.0, -2.5],
            [2.0, 4.0, 3.5],
            [1.0, 2.0, 0.5],
            [0.2, 3.8, 3.4],
        ],
        dtype=np.float32,
    )
    scene_mask = build_scene_points_in_any_target_mask(scene_points, [target], margin_factor=1.05)

    result = choose_alignment_candidate(
        prior_seed_path=prior_seed_path,
        prior_bbox_size=np.asarray([1.0, 1.0, 1.0], dtype=np.float32),
        target=target,
        all_targets=[target],
        scene_points=scene_points,
        scene_points_in_any_target=scene_mask,
        previous_candidate_aabbs=[],
        anchor_mode="floor",
        yaw_candidates=[0.0],
    )

    chosen = result.chosen
    assert np.allclose(chosen.scale_vec, np.asarray([2.0, 4.0, 6.0], dtype=np.float32))
    assert np.isclose(chosen.candidate_aabb_min[2], -2.5, atol=1e-5)
    assert np.allclose(chosen.candidate_center_world, target.center, atol=1e-5)
    assert chosen.accepted is True
    assert chosen.rejected_reasons == ()


def test_choose_alignment_candidate_marks_drop_when_all_candidates_are_bad(tmp_path: Path) -> None:
    prior_seed_path = tmp_path / "prior_center_seed.ply"
    prior_points = np.asarray(
        [
            [-0.5, -0.5, -0.5],
            [0.5, -0.5, -0.5],
            [-0.5, 0.5, 0.5],
            [0.5, 0.5, 0.5],
        ],
        dtype=np.float32,
    )
    _write_point_cloud_ply(prior_seed_path, prior_points)

    target = _make_target(center=(10.0, 0.0, 0.5), sizes=(2.0, 2.0, 2.0))
    scene_points = np.asarray(
        [
            [-1.0, -1.0, -1.0],
            [1.0, 1.0, 1.0],
            [0.5, 0.0, 0.0],
        ],
        dtype=np.float32,
    )
    scene_mask = build_scene_points_in_any_target_mask(scene_points, [target], margin_factor=1.05)

    result = choose_alignment_candidate(
        prior_seed_path=prior_seed_path,
        prior_bbox_size=np.asarray([1.0, 1.0, 1.0], dtype=np.float32),
        target=target,
        all_targets=[target],
        scene_points=scene_points,
        scene_points_in_any_target=scene_mask,
        previous_candidate_aabbs=[],
        anchor_mode="center",
        yaw_candidates=[0.0, 90.0],
        scene_bbox_margin=0.0,
        outside_scene_ratio_threshold=0.0,
        skip_on_bad_alignment=True,
    )

    assert result.chosen.accepted is False
    assert result.chosen.dropped is True
    assert result.chosen.drop_reason == "all_candidates_rejected"
