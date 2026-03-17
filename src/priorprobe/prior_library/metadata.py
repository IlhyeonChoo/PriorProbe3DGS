from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PriorMetadata:
    """Auxiliary metadata used during retrieval and insertion."""

    category: str
    source: str = "unknown"
    scale_meters: tuple[float, float, float] | None = None
    tags: tuple[str, ...] = ()
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "category": self.category,
            "source": self.source,
            "tags": list(self.tags),
        }
        if self.scale_meters is not None:
            payload["scale_meters"] = list(self.scale_meters)
        if self.extras:
            payload["extras"] = self.extras
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PriorMetadata":
        scale = payload.get("scale_meters")
        return cls(
            category=payload["category"],
            source=payload.get("source", "unknown"),
            scale_meters=tuple(scale) if scale else None,
            tags=tuple(payload.get("tags", [])),
            extras=dict(payload.get("extras", {})),
        )
