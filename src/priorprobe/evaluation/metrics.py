from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from priorprobe.optimization.trainer import TrainingRun


_METHOD_PATTERN = re.compile(r"ours_(\d+)$")


@dataclass(slots=True)
class CheckpointMetric:
    iteration: int
    method: str
    psnr: float | None
    ssim: float | None
    lpips: float | None
    gaussian_count: int | None = None
    estimated_elapsed_sec: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "method": self.method,
            "psnr": self.psnr,
            "ssim": self.ssim,
            "lpips": self.lpips,
            "gaussian_count": self.gaussian_count,
            "estimated_elapsed_sec": self.estimated_elapsed_sec,
        }


@dataclass(slots=True)
class EvaluationSummary:
    """Computed metrics derived from a placeholder run or a backend artifact."""

    experiment_name: str | None
    backend: str | None
    initialization: str | None
    status: str | None
    dataset_name: str | None
    scene_id: str | None
    model_path: str | None
    total_optimization_time_sec: float
    time_to_target_quality_sec: float | None
    target_psnr: float | None
    final_iteration: int | None
    psnr: float | None
    ssim: float | None
    lpips: float | None
    retrieval_accuracy: float | None = None
    alignment_success_rate: float | None = None
    gaussian_count: int | None = None
    prior_object_id: str | None = None
    prior_category: str | None = None
    prior_object_ids: tuple[str, ...] = ()
    prior_count: int = 0
    checkpoint_metrics: list[CheckpointMetric] = field(default_factory=list)
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_name": self.experiment_name,
            "backend": self.backend,
            "initialization": self.initialization,
            "status": self.status,
            "dataset_name": self.dataset_name,
            "scene_id": self.scene_id,
            "model_path": self.model_path,
            "total_optimization_time_sec": self.total_optimization_time_sec,
            "time_to_target_quality_sec": self.time_to_target_quality_sec,
            "target_psnr": self.target_psnr,
            "final_iteration": self.final_iteration,
            "psnr": self.psnr,
            "ssim": self.ssim,
            "lpips": self.lpips,
            "retrieval_accuracy": self.retrieval_accuracy,
            "alignment_success_rate": self.alignment_success_rate,
            "gaussian_count": self.gaussian_count,
            "prior_object_id": self.prior_object_id,
            "prior_category": self.prior_category,
            "prior_object_ids": list(self.prior_object_ids),
            "prior_count": self.prior_count,
            "checkpoint_metrics": [metric.to_dict() for metric in self.checkpoint_metrics],
            "warnings": list(self.warnings),
        }


def _parse_iteration(method: str) -> int | None:
    match = _METHOD_PATTERN.fullmatch(method)
    if match is None:
        return None
    return int(match.group(1))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_ply_vertex_count(path: Path) -> int | None:
    if not path.exists():
        return None

    with path.open("rb") as handle:
        while True:
            raw_line = handle.readline()
            if not raw_line:
                break
            try:
                line = raw_line.decode("ascii").strip()
            except UnicodeDecodeError:
                return None
            if line.startswith("element vertex "):
                return int(line.split()[-1])
            if line == "end_header":
                return None
    return None


def _load_checkpoint_metrics(model_path: Path, total_elapsed_sec: float | None) -> tuple[list[CheckpointMetric], tuple[str, ...]]:
    warnings: list[str] = []
    results_path = model_path / "results.json"
    if not results_path.exists():
        return [], (f"missing results.json: {results_path}",)

    payload = _load_json(results_path)
    if not isinstance(payload, dict):
        return [], (f"invalid results.json payload: {results_path}",)

    checkpoints: list[CheckpointMetric] = []
    for method, metrics in payload.items():
        iteration = _parse_iteration(str(method))
        if iteration is None or not isinstance(metrics, dict):
            continue

        point_cloud_path = model_path / "point_cloud" / f"iteration_{iteration}" / "point_cloud.ply"
        checkpoints.append(
            CheckpointMetric(
                iteration=iteration,
                method=str(method),
                psnr=float(metrics["PSNR"]) if metrics.get("PSNR") is not None else None,
                ssim=float(metrics["SSIM"]) if metrics.get("SSIM") is not None else None,
                lpips=float(metrics["LPIPS"]) if metrics.get("LPIPS") is not None else None,
                gaussian_count=_read_ply_vertex_count(point_cloud_path),
            )
        )

    checkpoints.sort(key=lambda metric: metric.iteration)
    if not checkpoints:
        return [], (f"no ours_<iteration> entries in results.json: {results_path}",)

    max_iteration = checkpoints[-1].iteration
    if total_elapsed_sec is not None and max_iteration > 0:
        for metric in checkpoints:
            metric.estimated_elapsed_sec = round(total_elapsed_sec * metric.iteration / max_iteration, 6)

    return checkpoints, tuple(warnings)


def _time_to_target(checkpoints: list[CheckpointMetric], target_psnr: float | None) -> float | None:
    if target_psnr is None:
        return None
    for metric in checkpoints:
        if metric.psnr is not None and metric.psnr >= target_psnr:
            return metric.estimated_elapsed_sec
    return None


def summarize_backend_run(
    backend_run_path: Path,
    *,
    target_psnr: float | None = None,
) -> EvaluationSummary:
    payload = _load_json(backend_run_path)
    model_path = Path(payload["model_path"])
    total_elapsed_sec = float(payload["elapsed_sec"]) if payload.get("elapsed_sec") is not None else None
    checkpoints, checkpoint_warnings = _load_checkpoint_metrics(model_path, total_elapsed_sec)
    warnings = list(checkpoint_warnings)

    final_checkpoint = checkpoints[-1] if checkpoints else None
    selected_prior = payload.get("selected_prior") or {}
    selected_priors = payload.get("selected_priors") or []
    if not selected_prior and selected_priors:
        selected_prior = selected_priors[0]
    retrieval_accuracy = None
    if selected_priors:
        scores = [float(item["score"]) for item in selected_priors if item.get("score") is not None]
        retrieval_accuracy = float(sum(scores) / len(scores)) if scores else None
    elif selected_prior.get("score") is not None:
        retrieval_accuracy = float(selected_prior["score"])
    dataset_scene = payload.get("dataset_scene") or {}

    return EvaluationSummary(
        experiment_name=payload.get("experiment_name"),
        backend=payload.get("backend"),
        initialization=payload.get("initialization"),
        status=payload.get("status"),
        dataset_name=dataset_scene.get("dataset_name"),
        scene_id=dataset_scene.get("scene_id"),
        model_path=str(model_path),
        total_optimization_time_sec=total_elapsed_sec or 0.0,
        time_to_target_quality_sec=_time_to_target(checkpoints, target_psnr),
        target_psnr=target_psnr,
        final_iteration=final_checkpoint.iteration if final_checkpoint else None,
        psnr=final_checkpoint.psnr if final_checkpoint else None,
        ssim=final_checkpoint.ssim if final_checkpoint else None,
        lpips=final_checkpoint.lpips if final_checkpoint else None,
        retrieval_accuracy=retrieval_accuracy,
        alignment_success_rate=None,
        gaussian_count=final_checkpoint.gaussian_count if final_checkpoint else None,
        prior_object_id=selected_prior.get("object_id"),
        prior_category=selected_prior.get("category"),
        prior_object_ids=tuple(str(item.get("object_id")) for item in selected_priors if item.get("object_id") is not None),
        prior_count=len(selected_priors),
        checkpoint_metrics=checkpoints,
        warnings=tuple(warnings),
    )


def summarize_run(
    run: TrainingRun,
    *,
    retrieval_score: float | None = None,
    alignment_score: float | None = None,
) -> EvaluationSummary:
    base_psnr = 26.0 if run.initialization == "from_scratch" else 27.5
    base_ssim = 0.87 if run.initialization == "from_scratch" else 0.90
    base_lpips = 0.16 if run.initialization == "from_scratch" else 0.12
    time_to_target = round(run.wall_time_sec * 0.75, 3) if run.target_metric else None
    gaussian_count = 120_000 if run.initialization == "from_scratch" else 105_000

    return EvaluationSummary(
        experiment_name=run.experiment_name,
        backend=None,
        initialization=run.initialization,
        status="completed",
        dataset_name=None,
        scene_id=None,
        model_path=None,
        total_optimization_time_sec=run.wall_time_sec,
        time_to_target_quality_sec=time_to_target,
        target_psnr=None,
        final_iteration=run.steps,
        psnr=base_psnr,
        ssim=base_ssim,
        lpips=base_lpips,
        retrieval_accuracy=retrieval_score,
        alignment_success_rate=alignment_score,
        gaussian_count=gaussian_count,
    )
