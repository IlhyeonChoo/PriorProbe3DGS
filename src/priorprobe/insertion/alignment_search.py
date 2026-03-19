from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from plyfile import PlyData

from priorprobe.replica_export import quaternion_xyzw_to_rotation_matrix


FLOOR_SUPPORTED_CATEGORIES = {"chair", "sofa", "table", "lamp"}


def _sample_indices(count: int, limit: int) -> np.ndarray:
    if limit <= 0 or count <= limit:
        return np.arange(count, dtype=np.int64)
    return np.linspace(0, count - 1, num=limit, dtype=np.int64)


def load_ply_xyz(path: Path, *, max_points: int = 0) -> np.ndarray:
    ply = PlyData.read(path)
    vertex = ply["vertex"]
    xyz = np.stack(
        [
            np.asarray(vertex["x"], dtype=np.float32),
            np.asarray(vertex["y"], dtype=np.float32),
            np.asarray(vertex["z"], dtype=np.float32),
        ],
        axis=1,
    )
    indices = _sample_indices(xyz.shape[0], max_points)
    return xyz[indices]


def rotation_z_degrees(yaw_deg: float) -> np.ndarray:
    yaw_rad = np.deg2rad(float(yaw_deg))
    c = float(np.cos(yaw_rad))
    s = float(np.sin(yaw_rad))
    return np.asarray(
        [
            [c, -s, 0.0],
            [s, c, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )


@dataclass(slots=True)
class TargetBox:
    object_id: int | str
    category: str
    center: np.ndarray
    sizes: np.ndarray
    rotation_matrix: np.ndarray

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "TargetBox":
        return cls(
            object_id=payload["object_id"],
            category=str(payload["category"]),
            center=np.asarray(payload["center"], dtype=np.float32),
            sizes=np.asarray(payload["sizes"], dtype=np.float32),
            rotation_matrix=quaternion_xyzw_to_rotation_matrix(
                np.asarray(payload["rotation_xyzw"], dtype=np.float32)
            ),
        )

    def anchor_point(self, anchor_mode: str) -> np.ndarray:
        if anchor_mode == "floor":
            return self.center + self.rotation_matrix @ np.asarray(
                [0.0, 0.0, -float(self.sizes[2]) * 0.5],
                dtype=np.float32,
            )
        if anchor_mode == "center":
            return self.center
        raise ValueError(f"Unsupported anchor_mode: {anchor_mode}")

    def expanded(self, factor: float) -> "TargetBox":
        return TargetBox(
            object_id=self.object_id,
            category=self.category,
            center=self.center.copy(),
            sizes=self.sizes * np.float32(factor),
            rotation_matrix=self.rotation_matrix.copy(),
        )


@dataclass(slots=True)
class AlignmentCandidate:
    yaw_deg: float
    anchor_mode: str
    scale_vec: np.ndarray
    rotation_matrix: np.ndarray
    translation: np.ndarray
    target_anchor_world: np.ndarray
    candidate_center_world: np.ndarray
    candidate_sizes_world: np.ndarray
    candidate_aabb_min: np.ndarray
    candidate_aabb_max: np.ndarray
    outside_scene_ratio: float
    non_target_penetration_ratio: float
    other_target_max_iou: float
    prior_target_max_iou: float
    score: float
    accepted: bool
    rejected_reasons: tuple[str, ...]
    dropped: bool = False
    drop_reason: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "yaw_deg": float(self.yaw_deg),
            "anchor_mode": self.anchor_mode,
            "scale_vec": self.scale_vec.tolist(),
            "rotation_matrix": self.rotation_matrix.tolist(),
            "translation": self.translation.tolist(),
            "target_anchor_world": self.target_anchor_world.tolist(),
            "candidate_center_world": self.candidate_center_world.tolist(),
            "candidate_sizes_world": self.candidate_sizes_world.tolist(),
            "candidate_aabb_min": self.candidate_aabb_min.tolist(),
            "candidate_aabb_max": self.candidate_aabb_max.tolist(),
            "outside_scene_ratio": float(self.outside_scene_ratio),
            "non_target_penetration_ratio": float(self.non_target_penetration_ratio),
            "other_target_max_iou": float(self.other_target_max_iou),
            "prior_target_max_iou": float(self.prior_target_max_iou),
            "score": float(self.score),
            "accepted": bool(self.accepted),
            "rejected_reasons": list(self.rejected_reasons),
            "dropped": bool(self.dropped),
            "drop_reason": self.drop_reason,
        }


@dataclass(slots=True)
class AlignmentSearchResult:
    chosen: AlignmentCandidate
    candidates: list[AlignmentCandidate]


def support_type_for_category(category: str, explicit: str | None = None) -> str:
    if explicit:
        return str(explicit)
    return "floor" if str(category) in FLOOR_SUPPORTED_CATEGORIES else "unknown"


def default_anchor_mode(category: str, support_type: str) -> str:
    return "floor" if support_type == "floor" or str(category) in FLOOR_SUPPORTED_CATEGORIES else "center"


def transform_points(
    xyz: np.ndarray,
    *,
    scale_vec: np.ndarray,
    rotation_matrix: np.ndarray,
    translation: np.ndarray,
) -> np.ndarray:
    return (xyz * scale_vec[None, :]) @ rotation_matrix.T + translation[None, :]


def obb_contains_points(
    points: np.ndarray,
    *,
    center: np.ndarray,
    sizes: np.ndarray,
    rotation_matrix: np.ndarray,
) -> np.ndarray:
    local = (points - center[None, :]) @ rotation_matrix
    half_sizes = sizes[None, :] * 0.5
    return np.all(np.abs(local) <= (half_sizes + 1e-6), axis=1)


def aabb_iou(min_a: np.ndarray, max_a: np.ndarray, min_b: np.ndarray, max_b: np.ndarray) -> float:
    inter_min = np.maximum(min_a, min_b)
    inter_max = np.minimum(max_a, max_b)
    inter_size = np.maximum(inter_max - inter_min, 0.0)
    inter_volume = float(np.prod(inter_size))
    if inter_volume <= 0.0:
        return 0.0
    vol_a = float(np.prod(np.maximum(max_a - min_a, 0.0)))
    vol_b = float(np.prod(np.maximum(max_b - min_b, 0.0)))
    union = max(vol_a + vol_b - inter_volume, 1e-6)
    return inter_volume / union


def obb_corners(
    *,
    center: np.ndarray,
    sizes: np.ndarray,
    rotation_matrix: np.ndarray,
) -> np.ndarray:
    half = sizes * 0.5
    corners_local = np.asarray(
        [
            [-half[0], -half[1], -half[2]],
            [-half[0], -half[1], +half[2]],
            [-half[0], +half[1], -half[2]],
            [-half[0], +half[1], +half[2]],
            [+half[0], -half[1], -half[2]],
            [+half[0], -half[1], +half[2]],
            [+half[0], +half[1], -half[2]],
            [+half[0], +half[1], +half[2]],
        ],
        dtype=np.float32,
    )
    return corners_local @ rotation_matrix.T + center[None, :]


def aabb_from_obb(*, center: np.ndarray, sizes: np.ndarray, rotation_matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    corners = obb_corners(center=center, sizes=sizes, rotation_matrix=rotation_matrix)
    return corners.min(axis=0), corners.max(axis=0)


def build_scene_points_in_any_target_mask(
    scene_points: np.ndarray,
    targets: Iterable[TargetBox],
    *,
    margin_factor: float,
) -> np.ndarray:
    mask = np.zeros(scene_points.shape[0], dtype=bool)
    for target in targets:
        expanded = target.expanded(margin_factor)
        mask |= obb_contains_points(
            scene_points,
            center=expanded.center,
            sizes=expanded.sizes,
            rotation_matrix=expanded.rotation_matrix,
        )
    return mask


def _candidate_center_world(
    *,
    anchor_mode: str,
    translation: np.ndarray,
    rotation_matrix: np.ndarray,
    scaled_sizes: np.ndarray,
) -> np.ndarray:
    if anchor_mode == "center":
        return translation
    if anchor_mode == "floor":
        return translation + rotation_matrix @ np.asarray([0.0, 0.0, float(scaled_sizes[2]) * 0.5], dtype=np.float32)
    raise ValueError(f"Unsupported anchor_mode: {anchor_mode}")


def choose_alignment_candidate(
    *,
    prior_seed_path: Path,
    prior_bbox_size: np.ndarray,
    target: TargetBox,
    all_targets: list[TargetBox],
    scene_points: np.ndarray,
    scene_points_in_any_target: np.ndarray,
    previous_candidate_aabbs: list[tuple[np.ndarray, np.ndarray]],
    anchor_mode: str,
    yaw_candidates: Iterable[float],
    max_prior_points: int = 16_000,
    scene_bbox_margin: float = 0.02,
    target_obb_margin: float = 1.05,
    overlap_iou_threshold: float = 0.15,
    prior_overlap_iou_threshold: float = 0.15,
    outside_scene_ratio_threshold: float = 0.01,
    non_target_penetration_ratio_threshold: float = 0.35,
    skip_on_bad_alignment: bool = False,
) -> AlignmentSearchResult:
    if np.any(prior_bbox_size <= 0):
        raise ValueError(f"prior_bbox_size must be positive: {prior_bbox_size}")

    prior_points = load_ply_xyz(prior_seed_path, max_points=max_prior_points)
    scale_vec = target.sizes / prior_bbox_size
    if not np.all(np.isfinite(scale_vec)) or np.any(scale_vec <= 0):
        raise ValueError(f"invalid anisotropic scale vector: {scale_vec}")

    scene_bbox_min = scene_points.min(axis=0) - np.float32(scene_bbox_margin)
    scene_bbox_max = scene_points.max(axis=0) + np.float32(scene_bbox_margin)
    current_target_expanded = target.expanded(target_obb_margin)
    other_target_aabbs = [
        aabb_from_obb(center=other.center, sizes=other.sizes, rotation_matrix=other.rotation_matrix)
        for other in all_targets
        if other.object_id != target.object_id
    ]

    candidates: list[AlignmentCandidate] = []
    for yaw_deg in yaw_candidates:
        local_yaw = rotation_z_degrees(yaw_deg)
        rotation_matrix = target.rotation_matrix @ local_yaw
        translation = target.anchor_point(anchor_mode)
        transformed_points = transform_points(
            prior_points,
            scale_vec=scale_vec,
            rotation_matrix=rotation_matrix,
            translation=translation,
        )
        scaled_sizes = prior_bbox_size * scale_vec
        candidate_center_world = _candidate_center_world(
            anchor_mode=anchor_mode,
            translation=translation,
            rotation_matrix=rotation_matrix,
            scaled_sizes=scaled_sizes,
        )
        candidate_aabb_min = transformed_points.min(axis=0)
        candidate_aabb_max = transformed_points.max(axis=0)
        candidate_mask = obb_contains_points(
            scene_points,
            center=candidate_center_world,
            sizes=scaled_sizes,
            rotation_matrix=rotation_matrix,
        )
        outside_scene_mask = np.any(
            (transformed_points < scene_bbox_min[None, :]) | (transformed_points > scene_bbox_max[None, :]),
            axis=1,
        )
        outside_scene_ratio = float(outside_scene_mask.mean()) if transformed_points.size else 0.0
        non_target_mask = candidate_mask & ~scene_points_in_any_target
        candidate_scene_count = int(candidate_mask.sum())
        non_target_penetration_ratio = float(non_target_mask.sum() / max(candidate_scene_count, 1))

        other_target_max_iou = 0.0
        for other_min, other_max in other_target_aabbs:
            other_target_max_iou = max(
                other_target_max_iou,
                aabb_iou(candidate_aabb_min, candidate_aabb_max, other_min, other_max),
            )

        prior_target_max_iou = 0.0
        for prev_min, prev_max in previous_candidate_aabbs:
            prior_target_max_iou = max(
                prior_target_max_iou,
                aabb_iou(candidate_aabb_min, candidate_aabb_max, prev_min, prev_max),
            )

        rejected_reasons: list[str] = []
        if outside_scene_ratio > outside_scene_ratio_threshold:
            rejected_reasons.append("outside_scene")
        if non_target_penetration_ratio > non_target_penetration_ratio_threshold:
            rejected_reasons.append("non_target_penetration")
        if other_target_max_iou > overlap_iou_threshold:
            rejected_reasons.append("target_overlap")
        if prior_target_max_iou > prior_overlap_iou_threshold:
            rejected_reasons.append("prior_overlap")

        score = (
            outside_scene_ratio * 1000.0
            + non_target_penetration_ratio * 100.0
            + other_target_max_iou * 30.0
            + prior_target_max_iou * 50.0
        )
        candidates.append(
            AlignmentCandidate(
                yaw_deg=float(yaw_deg),
                anchor_mode=anchor_mode,
                scale_vec=scale_vec.astype(np.float32),
                rotation_matrix=rotation_matrix.astype(np.float32),
                translation=translation.astype(np.float32),
                target_anchor_world=translation.astype(np.float32),
                candidate_center_world=candidate_center_world.astype(np.float32),
                candidate_sizes_world=scaled_sizes.astype(np.float32),
                candidate_aabb_min=candidate_aabb_min.astype(np.float32),
                candidate_aabb_max=candidate_aabb_max.astype(np.float32),
                outside_scene_ratio=outside_scene_ratio,
                non_target_penetration_ratio=non_target_penetration_ratio,
                other_target_max_iou=other_target_max_iou,
                prior_target_max_iou=prior_target_max_iou,
                score=score,
                accepted=not rejected_reasons,
                rejected_reasons=tuple(rejected_reasons),
            )
        )

    if not candidates:
        raise ValueError("No alignment candidates were generated")

    accepted = [candidate for candidate in candidates if candidate.accepted]
    chosen = min(accepted or candidates, key=lambda candidate: candidate.score)
    if skip_on_bad_alignment and not accepted:
        chosen = AlignmentCandidate(
            yaw_deg=chosen.yaw_deg,
            anchor_mode=chosen.anchor_mode,
            scale_vec=chosen.scale_vec.copy(),
            rotation_matrix=chosen.rotation_matrix.copy(),
            translation=chosen.translation.copy(),
            target_anchor_world=chosen.target_anchor_world.copy(),
            candidate_center_world=chosen.candidate_center_world.copy(),
            candidate_sizes_world=chosen.candidate_sizes_world.copy(),
            candidate_aabb_min=chosen.candidate_aabb_min.copy(),
            candidate_aabb_max=chosen.candidate_aabb_max.copy(),
            outside_scene_ratio=chosen.outside_scene_ratio,
            non_target_penetration_ratio=chosen.non_target_penetration_ratio,
            other_target_max_iou=chosen.other_target_max_iou,
            prior_target_max_iou=chosen.prior_target_max_iou,
            score=chosen.score,
            accepted=False,
            rejected_reasons=chosen.rejected_reasons,
            dropped=True,
            drop_reason="all_candidates_rejected",
        )
    return AlignmentSearchResult(chosen=chosen, candidates=candidates)
