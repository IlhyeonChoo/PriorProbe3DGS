from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.evaluation.metrics import summarize_backend_run


def _write_minimal_ply(path: Path, vertex_count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "ply",
                "format ascii 1.0",
                f"element vertex {vertex_count}",
                "property float x",
                "property float y",
                "property float z",
                "end_header",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _load_export_results_module():
    script_path = ROOT / "scripts" / "export_results.py"
    spec = importlib.util.spec_from_file_location("priorprobe_export_results", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_summarize_backend_run_collects_checkpoint_metrics(tmp_path: Path) -> None:
    model_path = tmp_path / "model"
    results_path = model_path / "results.json"
    results_path.parent.mkdir(parents=True)
    results_path.write_text(
        json.dumps(
            {
                "ours_1000": {"PSNR": 27.1, "SSIM": 0.88, "LPIPS": 0.12},
                "ours_3000": {"PSNR": 29.4, "SSIM": 0.91, "LPIPS": 0.09},
            }
        ),
        encoding="utf-8",
    )
    _write_minimal_ply(model_path / "point_cloud" / "iteration_1000" / "point_cloud.ply", 1234)
    _write_minimal_ply(model_path / "point_cloud" / "iteration_3000" / "point_cloud.ply", 2345)

    backend_run_path = tmp_path / "backend_run.json"
    backend_run_path.write_text(
        json.dumps(
            {
                "experiment_name": "oracle_prior_vanilla_3dgs",
                "backend": "vanilla_3dgs",
                "initialization": "prior",
                "status": "completed",
                "model_path": str(model_path),
                "elapsed_sec": 60.0,
                "dataset_scene": {"dataset_name": "replica", "scene_id": "room_0"},
                "selected_prior": {"object_id": "chair_basic", "category": "chair", "score": 0.42},
            }
        ),
        encoding="utf-8",
    )

    summary = summarize_backend_run(backend_run_path, target_psnr=28.0)

    assert summary.experiment_name == "oracle_prior_vanilla_3dgs"
    assert summary.scene_id == "room_0"
    assert summary.psnr == 29.4
    assert summary.gaussian_count == 2345
    assert summary.retrieval_accuracy == 0.42
    assert summary.time_to_target_quality_sec == 60.0
    assert [metric.iteration for metric in summary.checkpoint_metrics] == [1000, 3000]
    assert summary.checkpoint_metrics[0].gaussian_count == 1234


def test_summarize_backend_run_aggregates_selected_priors(tmp_path: Path) -> None:
    model_path = tmp_path / "model"
    results_path = model_path / "results.json"
    results_path.parent.mkdir(parents=True)
    results_path.write_text(
        json.dumps({"ours_1000": {"PSNR": 27.1, "SSIM": 0.88, "LPIPS": 0.12}}),
        encoding="utf-8",
    )
    _write_minimal_ply(model_path / "point_cloud" / "iteration_1000" / "point_cloud.ply", 1234)
    backend_run_path = tmp_path / "backend_run.json"
    backend_run_path.write_text(
        json.dumps(
            {
                "experiment_name": "oracle_prior_vanilla_3dgs_multi_clip",
                "backend": "vanilla_3dgs",
                "initialization": "prior",
                "status": "completed",
                "model_path": str(model_path),
                "elapsed_sec": 20.0,
                "dataset_scene": {"dataset_name": "replica", "scene_id": "room_0"},
                "selected_priors": [
                    {"object_id": "chair_0201", "category": "chair", "score": 0.9},
                    {"object_id": "table_0011", "category": "table", "score": 0.7},
                ],
            }
        ),
        encoding="utf-8",
    )

    summary = summarize_backend_run(backend_run_path)

    assert summary.prior_count == 2
    assert summary.prior_object_ids == ("chair_0201", "table_0011")
    assert summary.retrieval_accuracy == 0.8


def test_export_results_flattens_checkpoint_rows(tmp_path: Path) -> None:
    outputs_root = tmp_path / "outputs"
    evaluation_dir = outputs_root / "experiments" / "oracle_prior_vanilla_3dgs"
    evaluation_dir.mkdir(parents=True)
    evaluation_dir.joinpath("evaluation.json").write_text(
        json.dumps(
            {
                "experiment_name": "oracle_prior_vanilla_3dgs",
                "backend": "vanilla_3dgs",
                "initialization": "prior",
                "status": "completed",
                "dataset_name": "replica",
                "scene_id": "room_0",
                "total_optimization_time_sec": 60.0,
                "time_to_target_quality_sec": 40.0,
                "target_psnr": 28.0,
                "final_iteration": 3000,
                "psnr": 29.4,
                "ssim": 0.91,
                "lpips": 0.09,
                "gaussian_count": 2345,
                "retrieval_accuracy": 0.42,
                "prior_object_id": "chair_basic",
                "prior_category": "chair",
                "warnings": [],
                "checkpoint_metrics": [
                    {
                        "iteration": 1000,
                        "method": "ours_1000",
                        "psnr": 27.1,
                        "ssim": 0.88,
                        "lpips": 0.12,
                        "gaussian_count": 1234,
                        "estimated_elapsed_sec": 20.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    export_results = _load_export_results_module()
    evaluations = export_results.collect_evaluations(outputs_root)
    summary_rows = [export_results._summary_row(evaluation) for evaluation in evaluations]
    checkpoint_rows = export_results.flatten_checkpoint_rows(evaluations)

    assert len(evaluations) == 1
    assert summary_rows[0]["scene_id"] == "room_0"
    assert checkpoint_rows == [
        {
            "experiment_name": "oracle_prior_vanilla_3dgs",
            "scene_id": "room_0",
            "initialization": "prior",
            "prior_object_id": "chair_basic",
            "prior_count": None,
            "iteration": 1000,
            "method": "ours_1000",
            "psnr": 27.1,
            "ssim": 0.88,
            "lpips": 0.12,
            "gaussian_count": 1234,
            "estimated_elapsed_sec": 20.0,
        }
    ]
