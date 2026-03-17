from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ControlledObject:
    """Object placement record used to quantify occlusion."""

    object_id: str
    visible_ratio: float = 1.0


@dataclass(slots=True)
class ControlledScene:
    """Simple container for controlled-scene metadata."""

    scene_id: str
    background_type: str = "simple_indoor"
    objects: list[ControlledObject] = field(default_factory=list)

    def occlusion_level(self) -> str:
        if not self.objects:
            return "none"

        mean_occlusion = 1.0 - sum(obj.visible_ratio for obj in self.objects) / len(self.objects)
        if mean_occlusion < 0.25:
            return "low"
        if mean_occlusion < 0.5:
            return "medium"
        return "high"
