from __future__ import annotations

import zlib
from typing import Iterable, Sequence

import numpy as np


def normalize_prior_sh_reset_mode(value: str | None) -> str:
    normalized = str(value or "none").strip().lower()
    if normalized not in {"none", "zero_all"}:
        raise ValueError(f"Unsupported prior SH reset mode: {value!r}")
    return normalized


def stable_seed(*parts: object) -> int:
    payload = "::".join(str(part) for part in parts)
    return int(zlib.crc32(payload.encode("utf-8")) & 0xFFFFFFFF)


def allocate_total_budget(counts: Sequence[int], target_total: int) -> list[int]:
    original = np.asarray([max(int(value), 0) for value in counts], dtype=np.int64)
    if original.size == 0:
        return []

    total_available = int(original.sum())
    if target_total <= 0 or target_total >= total_available:
        return original.astype(int).tolist()

    if total_available == 0:
        return [0 for _ in counts]

    raw = original.astype(np.float64) / float(total_available) * float(target_total)
    allocated = np.floor(raw).astype(np.int64)
    remaining = int(target_total - int(allocated.sum()))
    if remaining > 0:
        remainders = raw - allocated.astype(np.float64)
        order = np.argsort(-remainders, kind="mergesort")
        for index in order[:remaining]:
            allocated[int(index)] += 1
    return allocated.astype(int).tolist()


def subsample_structured_vertex(vertex: np.ndarray, *, keep_count: int, seed: int) -> np.ndarray:
    total = int(vertex.shape[0])
    if keep_count <= 0:
        return vertex[:0].copy()
    if keep_count >= total:
        return np.array(vertex, copy=True)

    rng = np.random.default_rng(int(seed))
    indices = np.sort(rng.choice(total, size=int(keep_count), replace=False))
    return np.array(vertex[indices], copy=True)


def reset_gaussian_sh(vertex: np.ndarray, *, mode: str) -> np.ndarray:
    normalized = normalize_prior_sh_reset_mode(mode)
    if normalized == "none":
        return np.array(vertex, copy=True)

    updated = np.array(vertex, copy=True)
    for field_name in updated.dtype.names or ():
        if field_name.startswith("f_dc_") or field_name.startswith("f_rest_"):
            updated[field_name] = 0.0
    return updated


def gaussian_positions(vertex: np.ndarray) -> np.ndarray:
    return np.stack(
        [
            np.asarray(vertex["x"], dtype=np.float32),
            np.asarray(vertex["y"], dtype=np.float32),
            np.asarray(vertex["z"], dtype=np.float32),
        ],
        axis=1,
    )


def expanded_aabb_from_positions(
    positions: np.ndarray,
    *,
    margin_scale: float,
    margin_min_m: float,
) -> tuple[np.ndarray, np.ndarray]:
    if positions.size == 0:
        zeros = np.zeros((3,), dtype=np.float32)
        return zeros.copy(), zeros.copy()

    mins = positions.min(axis=0).astype(np.float32)
    maxs = positions.max(axis=0).astype(np.float32)
    extents = np.maximum(maxs - mins, 0.0)
    scale_margin = np.maximum(float(margin_scale) - 1.0, 0.0) * 0.5 * extents
    margin = np.maximum(scale_margin, float(margin_min_m)).astype(np.float32)
    return mins - margin, maxs + margin


def point_keep_mask_outside_aabbs(
    points: np.ndarray,
    aabbs: Iterable[tuple[np.ndarray, np.ndarray]],
) -> np.ndarray:
    if points.size == 0:
        return np.zeros((0,), dtype=bool)

    keep_mask = np.ones((points.shape[0],), dtype=bool)
    for aabb_min, aabb_max in aabbs:
        inside = np.all((points >= aabb_min) & (points <= aabb_max), axis=1)
        keep_mask &= ~inside
    return keep_mask
