from __future__ import annotations

import importlib
import json
import re
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from math import exp
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
import torchvision.transforms.functional as tvf
from PIL import Image

from priorprobe.optimization.trainer import TrainingRun


_METHOD_PATTERN = re.compile(r"ours_(\d+)$")
_SSIM_C1 = 0.01 ** 2
_SSIM_C2 = 0.03 ** 2


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


def _gaussian_window(window_size: int, sigma: float) -> torch.Tensor:
    values = [exp(-((index - window_size // 2) ** 2) / float(2 * sigma ** 2)) for index in range(window_size)]
    window = torch.tensor(values, dtype=torch.float32)
    return window / window.sum()


def _create_ssim_window(window_size: int, channel: int, *, device: torch.device, dtype: torch.dtype) -> torch.Tensor:
    one_d = _gaussian_window(window_size, 1.5).unsqueeze(1)
    two_d = one_d.mm(one_d.t()).float().unsqueeze(0).unsqueeze(0)
    return two_d.expand(channel, 1, window_size, window_size).contiguous().to(device=device, dtype=dtype)


def _ssim_metric(img1: torch.Tensor, img2: torch.Tensor, window_size: int = 11) -> torch.Tensor:
    channel = img1.size(-3)
    window = _create_ssim_window(window_size, channel, device=img1.device, dtype=img1.dtype)
    mu1 = F.conv2d(img1, window, padding=window_size // 2, groups=channel)
    mu2 = F.conv2d(img2, window, padding=window_size // 2, groups=channel)

    mu1_sq = mu1.pow(2)
    mu2_sq = mu2.pow(2)
    mu1_mu2 = mu1 * mu2
    sigma1_sq = F.conv2d(img1 * img1, window, padding=window_size // 2, groups=channel) - mu1_sq
    sigma2_sq = F.conv2d(img2 * img2, window, padding=window_size // 2, groups=channel) - mu2_sq
    sigma12 = F.conv2d(img1 * img2, window, padding=window_size // 2, groups=channel) - mu1_mu2

    ssim_map = ((2 * mu1_mu2 + _SSIM_C1) * (2 * sigma12 + _SSIM_C2)) / (
        (mu1_sq + mu2_sq + _SSIM_C1) * (sigma1_sq + sigma2_sq + _SSIM_C2)
    )
    return ssim_map.mean()


def _psnr_metric(img1: torch.Tensor, img2: torch.Tensor) -> torch.Tensor:
    mse = (((img1 - img2)) ** 2).view(img1.shape[0], -1).mean(1, keepdim=True)
    return 20 * torch.log10(1.0 / torch.sqrt(mse))


@lru_cache(maxsize=8)
def _lpips_model(repo_path_str: str, device_type: str):
    repo_path = Path(repo_path_str)
    inserted = False
    if str(repo_path) not in sys.path:
        sys.path.insert(0, str(repo_path))
        inserted = True
    try:
        module = importlib.import_module("lpipsPyTorch")
        criterion = module.LPIPS("vgg", "0.1").to(torch.device(device_type))
        criterion.eval()
        return criterion
    finally:
        if inserted:
            sys.path.remove(str(repo_path))


def _initial_snapshot_metric(
    model_path: Path,
    *,
    repo_path: Path | None,
) -> tuple[CheckpointMetric | None, tuple[str, ...]]:
    warnings: list[str] = []
    render_dir = model_path / "test" / "ours_0" / "renders"
    gt_dir = model_path / "test" / "ours_0" / "gt"
    if not render_dir.exists() or not gt_dir.exists():
        return None, ()

    names = sorted(path.name for path in render_dir.iterdir() if path.is_file() and (gt_dir / path.name).exists())
    if not names:
        return None, (f"missing initial snapshot images: {render_dir}",)

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    lpips_model = None
    if repo_path is not None and repo_path.exists():
        try:
            lpips_model = _lpips_model(str(repo_path.resolve()), device.type)
        except Exception as exc:
            warnings.append(f"failed to load LPIPS model for iter_0: {exc}")

    psnr_values: list[float] = []
    ssim_values: list[float] = []
    lpips_values: list[float] = []
    with torch.no_grad():
        for name in names:
            render = tvf.to_tensor(Image.open(render_dir / name).convert("RGB")).unsqueeze(0).to(device)
            gt = tvf.to_tensor(Image.open(gt_dir / name).convert("RGB")).unsqueeze(0).to(device)
            psnr_values.append(float(_psnr_metric(render, gt).mean().item()))
            ssim_values.append(float(_ssim_metric(render, gt).item()))
            if lpips_model is not None:
                lpips_values.append(float(lpips_model(render, gt).mean().item()))

    point_cloud_path = model_path / "point_cloud" / "iteration_0" / "point_cloud.ply"
    metric = CheckpointMetric(
        iteration=0,
        method="ours_0",
        psnr=float(sum(psnr_values) / len(psnr_values)) if psnr_values else None,
        ssim=float(sum(ssim_values) / len(ssim_values)) if ssim_values else None,
        lpips=float(sum(lpips_values) / len(lpips_values)) if lpips_values else None,
        gaussian_count=_read_ply_vertex_count(point_cloud_path),
        estimated_elapsed_sec=0.0,
    )
    return metric, tuple(warnings)


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
    repo_path = Path(payload["repo_path"]) if payload.get("repo_path") is not None else None
    total_elapsed_sec = float(payload["elapsed_sec"]) if payload.get("elapsed_sec") is not None else None
    checkpoints, checkpoint_warnings = _load_checkpoint_metrics(model_path, total_elapsed_sec)
    initial_checkpoint, initial_warnings = _initial_snapshot_metric(model_path, repo_path=repo_path)
    warnings = list(checkpoint_warnings) + list(initial_warnings)
    if initial_checkpoint is not None:
        checkpoints = [metric for metric in checkpoints if metric.iteration != 0]
        checkpoints.insert(0, initial_checkpoint)

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
