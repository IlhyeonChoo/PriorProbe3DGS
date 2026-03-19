from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
from PIL import Image


def _normalize_vector(values: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(values))
    if norm <= 0.0:
        return values.astype(np.float32)
    return (values / norm).astype(np.float32)


def _foreground_mask(image: Image.Image) -> np.ndarray:
    if "A" in image.getbands():
        rgba = np.asarray(image.convert("RGBA"), dtype=np.float32) / 255.0
        mask = rgba[..., 3] > 0.05
        if mask.any():
            return mask

    rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    height, width, _ = rgb.shape
    corners = np.stack(
        [
            rgb[0, 0],
            rgb[0, width - 1],
            rgb[height - 1, 0],
            rgb[height - 1, width - 1],
        ],
        axis=0,
    )
    background = corners.mean(axis=0)
    color_distance = np.linalg.norm(rgb - background[None, None, :], axis=-1)
    mask = color_distance > 0.08
    if mask.any():
        return mask
    return rgb.sum(axis=-1) > 0.02


@dataclass(slots=True)
class SilhouetteStats:
    aspect_ratio_mean: float
    fill_ratio_mean: float
    visible_area_ratio_mean: float

    def to_dict(self) -> dict[str, float]:
        return {
            "aspect_ratio_mean": float(self.aspect_ratio_mean),
            "fill_ratio_mean": float(self.fill_ratio_mean),
            "visible_area_ratio_mean": float(self.visible_area_ratio_mean),
        }


def compute_silhouette_stats(
    image_paths: Sequence[Path],
    *,
    full_image_dir: Path | None = None,
) -> SilhouetteStats:
    if not image_paths:
        raise ValueError("At least one image path is required to compute silhouette stats")

    aspect_ratios: list[float] = []
    fill_ratios: list[float] = []
    visible_area_ratios: list[float] = []

    for path in image_paths:
        with Image.open(path) as image:
            mask = _foreground_mask(image)
            crop_height, crop_width = mask.shape

        if mask.any():
            ys, xs = np.where(mask)
            y0, y1 = int(ys.min()), int(ys.max())
            x0, x1 = int(xs.min()), int(xs.max())
            bbox_height = max(1, y1 - y0 + 1)
            bbox_width = max(1, x1 - x0 + 1)
            bbox_area = float(bbox_height * bbox_width)
            mask_area = float(mask.sum())
            aspect_ratios.append(float(bbox_width / max(bbox_height, 1)))
            fill_ratios.append(float(mask_area / max(bbox_area, 1.0)))
        else:
            aspect_ratios.append(1.0)
            fill_ratios.append(0.0)
            mask_area = 0.0

        full_area = float(crop_height * crop_width)
        if full_image_dir is not None:
            reference_path = full_image_dir / path.name
            if reference_path.exists():
                with Image.open(reference_path) as reference:
                    full_area = float(reference.width * reference.height)
        visible_area_ratios.append(float(mask_area / max(full_area, 1.0)))

    return SilhouetteStats(
        aspect_ratio_mean=float(np.mean(aspect_ratios)),
        fill_ratio_mean=float(np.mean(fill_ratios)),
        visible_area_ratio_mean=float(np.mean(visible_area_ratios)),
    )


def build_geometry_feature(
    size_xyz: Sequence[float] | np.ndarray,
    silhouette_stats: SilhouetteStats,
) -> np.ndarray:
    size = np.asarray(size_xyz, dtype=np.float32).reshape(-1)
    if size.shape != (3,):
        raise ValueError(f"size_xyz must be a 3-vector, got shape={size.shape}")

    max_dim = float(max(np.max(size), 1e-6))
    sorted_ratios = np.sort(size / max_dim).astype(np.float32)
    volume = float(np.prod(np.maximum(size, 1e-6)))
    log_volume = float(np.tanh(np.log(volume) / 5.0))
    log_aspect = float(np.tanh(np.log(max(silhouette_stats.aspect_ratio_mean, 1e-6)) / 2.0))
    vector = np.asarray(
        [
            sorted_ratios[0],
            sorted_ratios[1],
            sorted_ratios[2],
            log_volume,
            log_aspect,
            float(silhouette_stats.fill_ratio_mean),
            float(silhouette_stats.visible_area_ratio_mean),
        ],
        dtype=np.float32,
    )
    return _normalize_vector(vector)


def combine_appearance_and_geometry(
    appearance_feature: np.ndarray,
    geometry_feature: np.ndarray,
    *,
    appearance_weight: float = 0.7,
    geometry_weight: float = 0.3,
) -> np.ndarray:
    appearance = _normalize_vector(np.asarray(appearance_feature, dtype=np.float32).reshape(-1))
    geometry = _normalize_vector(np.asarray(geometry_feature, dtype=np.float32).reshape(-1))
    combined = np.concatenate(
        [
            np.sqrt(float(appearance_weight)) * appearance,
            np.sqrt(float(geometry_weight)) * geometry,
        ],
        axis=0,
    )
    return _normalize_vector(combined)
