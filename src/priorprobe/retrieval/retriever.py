from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

from priorprobe.features import cosine_similarity
from priorprobe.prior_library.library import PriorLibrary


@dataclass(slots=True)
class RetrievalResult:
    """Top-k retrieval output."""

    object_id: str
    score: float
    mode: str
    gaussian_path: Path
    category: str
    candidate_count: int
    fallback_used: bool
    feature_path: Path | None = None


def _load_feature(path: Path | None) -> np.ndarray | None:
    if path is None or not path.exists():
        return None
    payload = np.load(path)
    return payload.reshape(-1).astype(np.float32)


class PriorRetriever:
    """Category-aware top-k retriever for ShapeSplat prior assets."""

    def __init__(self, library: PriorLibrary) -> None:
        self._library = library

    def retrieve(
        self,
        query_features: Sequence[float] | None = None,
        *,
        top_k: int = 1,
        oracle_category: str | None = None,
        fallback_to_all: bool = True,
    ) -> list[RetrievalResult]:
        query_vector = (
            np.asarray(query_features, dtype=np.float32).reshape(-1)
            if query_features is not None
            else None
        )

        candidates = (
            self._library.find_by_category(oracle_category)
            if oracle_category is not None
            else self._library.list_entries()
        )
        fallback_used = False
        if not candidates and fallback_to_all:
            candidates = self._library.list_entries()
            fallback_used = True

        scored: list[tuple[float, object]] = []
        for index, entry in enumerate(candidates):
            score = 1.0 / (index + 1)
            feature = _load_feature(entry.feature_path)
            if query_vector is not None and feature is not None:
                score = cosine_similarity(query_vector, feature)
            scored.append((score, entry))

        scored.sort(key=lambda item: item[0], reverse=True)
        mode = "oracle_category" if oracle_category is not None else "automatic"
        results = [
            RetrievalResult(
                object_id=entry.object_id,
                score=float(score),
                mode=mode,
                gaussian_path=entry.gaussian_path,
                category=entry.category,
                candidate_count=len(candidates),
                fallback_used=fallback_used,
                feature_path=entry.feature_path,
            )
            for score, entry in scored[:top_k]
        ]
        return results
