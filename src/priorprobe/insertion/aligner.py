from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


IDENTITY_TRANSFORM = (
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0),
)


@dataclass(slots=True)
class AlignmentResult:
    """Alignment output for a retrieved prior."""

    object_id: str
    transform: tuple[tuple[float, float, float, float], ...]
    mode: str
    score: float


class PriorAligner:
    """Placeholder aligner with identity transforms."""

    def align(
        self,
        object_id: str,
        *,
        oracle: bool = False,
        initial_transform: Sequence[Sequence[float]] | None = None,
    ) -> AlignmentResult:
        if initial_transform is not None:
            transform = tuple(tuple(float(value) for value in row) for row in initial_transform)
        else:
            transform = IDENTITY_TRANSFORM

        return AlignmentResult(
            object_id=object_id,
            transform=transform,
            mode="oracle" if oracle else "automatic",
            score=1.0 if oracle else 0.5,
        )
