from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class TrainingRun:
    """Serialized summary for a single experiment run."""

    experiment_name: str
    initialization: str
    steps: int
    wall_time_sec: float
    target_metric: str | None = None
    target_value: float | None = None
    prior_object_id: str | None = None
    alignment_mode: str | None = None
    adaptation: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_name": self.experiment_name,
            "initialization": self.initialization,
            "steps": self.steps,
            "wall_time_sec": self.wall_time_sec,
            "target_metric": self.target_metric,
            "target_value": self.target_value,
            "prior_object_id": self.prior_object_id,
            "alignment_mode": self.alignment_mode,
            "adaptation": self.adaptation,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TrainingRun":
        return cls(
            experiment_name=payload["experiment_name"],
            initialization=payload["initialization"],
            steps=payload["steps"],
            wall_time_sec=payload["wall_time_sec"],
            target_metric=payload.get("target_metric"),
            target_value=payload.get("target_value"),
            prior_object_id=payload.get("prior_object_id"),
            alignment_mode=payload.get("alignment_mode"),
            adaptation=payload.get("adaptation"),
            notes=list(payload.get("notes", [])),
        )


class PriorProbeTrainer:
    """Placeholder trainer that emits deterministic run summaries."""

    def __init__(self, output_root: Path) -> None:
        self.output_root = output_root

    def run_from_scratch(
        self,
        experiment_name: str,
        *,
        steps: int,
        target_metric: str | None = None,
        target_value: float | None = None,
    ) -> TrainingRun:
        return TrainingRun(
            experiment_name=experiment_name,
            initialization="from_scratch",
            steps=steps,
            wall_time_sec=round(steps * 0.08, 3),
            target_metric=target_metric,
            target_value=target_value,
            notes=["scaffold run", "replace with actual 3DGS backend"],
        )

    def run_with_prior(
        self,
        experiment_name: str,
        *,
        prior_object_id: str,
        steps: int,
        alignment_mode: str,
        adaptation: str,
        target_metric: str | None = None,
        target_value: float | None = None,
    ) -> TrainingRun:
        speed_factor = 0.05 if alignment_mode == "oracle" else 0.06
        if adaptation == "lightweight_finetune":
            speed_factor += 0.005

        return TrainingRun(
            experiment_name=experiment_name,
            initialization="prior",
            steps=steps,
            wall_time_sec=round(steps * speed_factor, 3),
            target_metric=target_metric,
            target_value=target_value,
            prior_object_id=prior_object_id,
            alignment_mode=alignment_mode,
            adaptation=adaptation,
            notes=["scaffold run", "replace with actual 3DGS backend"],
        )

    def save_run(self, run: TrainingRun) -> Path:
        run_dir = self.output_root / "experiments" / run.experiment_name
        run_dir.mkdir(parents=True, exist_ok=True)
        output_path = run_dir / "run_summary.json"
        output_path.write_text(json.dumps(run.to_dict(), indent=2), encoding="utf-8")
        return output_path
