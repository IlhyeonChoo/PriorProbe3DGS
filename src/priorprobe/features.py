from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import torch
from PIL import Image


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


@dataclass(slots=True)
class FeatureExtractorConfig:
    model_name: str = "ViT-B-32"
    pretrained: str = "laion2b_s34b_b79k"
    device: str = "cuda"
    render_count: int = 8
    allow_fallback: bool = True


def list_render_images(render_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in render_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def evenly_sample_paths(paths: Sequence[Path], count: int) -> list[Path]:
    if count <= 0:
        raise ValueError("count must be positive")
    if not paths:
        raise ValueError("at least one render image is required")
    if len(paths) <= count:
        return list(paths)

    indices = np.linspace(0, len(paths) - 1, num=count, dtype=int)
    return [paths[index] for index in indices.tolist()]


def _extract_mean_rgb_feature(paths: Iterable[Path]) -> np.ndarray:
    features: list[np.ndarray] = []
    for path in paths:
        with Image.open(path) as image:
            rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
        features.append(rgb.reshape(-1, 3).mean(axis=0))

    stacked = np.stack(features, axis=0)
    pooled = stacked.mean(axis=0)
    norm = np.linalg.norm(pooled)
    if norm > 0:
        pooled = pooled / norm
    return pooled.astype(np.float32)


def _resolve_device(requested: str) -> str:
    if requested == "cuda" and not torch.cuda.is_available():
        return "cpu"
    return requested


def extract_image_features(
    paths: Sequence[Path],
    *,
    config: FeatureExtractorConfig | None = None,
) -> np.ndarray:
    extractor_config = config or FeatureExtractorConfig()
    sampled = evenly_sample_paths(paths, extractor_config.render_count)

    if extractor_config.model_name == "mean_rgb":
        return _extract_mean_rgb_feature(sampled)

    try:
        import open_clip  # type: ignore
    except ImportError:
        if extractor_config.allow_fallback:
            return _extract_mean_rgb_feature(sampled)
        raise RuntimeError(
            "open_clip is required for feature extraction. Install open-clip-torch or set allow_fallback=true."
        ) from None

    device = _resolve_device(extractor_config.device)
    try:
        model, _, preprocess = open_clip.create_model_and_transforms(
            extractor_config.model_name,
            pretrained=extractor_config.pretrained,
            device=device,
        )
    except Exception:
        if extractor_config.allow_fallback:
            return _extract_mean_rgb_feature(sampled)
        raise
    model.eval()

    with torch.no_grad():
        batches = []
        for path in sampled:
            with Image.open(path) as image:
                batches.append(preprocess(image.convert("RGB")))
        inputs = torch.stack(batches, dim=0).to(device)
        image_features = model.encode_image(inputs)
        image_features = torch.nn.functional.normalize(image_features, dim=-1)
        pooled = image_features.mean(dim=0)
        pooled = torch.nn.functional.normalize(pooled, dim=0)

    return pooled.detach().cpu().numpy().astype(np.float32)


def extract_render_dir_feature(
    render_dir: Path,
    *,
    config: FeatureExtractorConfig | None = None,
) -> tuple[np.ndarray, list[Path]]:
    render_paths = list_render_images(render_dir)
    extractor_config = config or FeatureExtractorConfig()
    sampled = evenly_sample_paths(render_paths, extractor_config.render_count)
    feature = extract_image_features(sampled, config=extractor_config)
    return feature, sampled


def cosine_similarity(query: np.ndarray, candidate: np.ndarray) -> float:
    query_vec = np.asarray(query, dtype=np.float32).reshape(-1)
    candidate_vec = np.asarray(candidate, dtype=np.float32).reshape(-1)
    query_norm = np.linalg.norm(query_vec)
    candidate_norm = np.linalg.norm(candidate_vec)
    if query_norm == 0.0 or candidate_norm == 0.0:
        return 0.0
    return float(np.dot(query_vec, candidate_vec) / (query_norm * candidate_norm))
