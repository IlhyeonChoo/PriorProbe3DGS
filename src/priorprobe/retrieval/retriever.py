from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from priorprobe.prior_library.library import PriorLibrary


@dataclass(slots=True)
class RetrievalResult:
    """Top-k retrieval output."""

    object_id: str
    score: float
    mode: str
    gaussian_path: Path
    category: str


class PriorRetriever:
    """Placeholder retriever with oracle and deterministic fallback modes."""

    def __init__(self, library: PriorLibrary) -> None:
        self._library = library

    def retrieve(
        self,
        query_features: Sequence[float] | None = None,
        *,
        top_k: int = 1,
        oracle_object_id: str | None = None,
    ) -> list[RetrievalResult]:
        del query_features
        if oracle_object_id is not None:
            entry = self._library.get(oracle_object_id)
            return [
                RetrievalResult(
                    object_id=oracle_object_id,
                    score=1.0,
                    mode="oracle",
                    gaussian_path=entry.gaussian_path,
                    category=entry.category,
                )
            ]

        entries = self._library.list_entries()
        results = [
            RetrievalResult(
                object_id=entry.object_id,
                score=1.0 / (index + 1),
                mode="automatic",
                gaussian_path=entry.gaussian_path,
                category=entry.category,
            )
            for index, entry in enumerate(entries[:top_k])
        ]
        return results
