from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from priorprobe.validation import prior_position_validator as validator


@pytest.fixture()
def temp_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    return tmp_path


def _write_colmap_scene(scene_root: Path) -> None:
    sparse = scene_root / "sparse" / "0"
    images = scene_root / "images"
    sparse.mkdir(parents=True)
    images.mkdir(parents=True)
    (sparse / "cameras.txt").write_text(
        "1 PINHOLE 4 4 4.0 4.0 2.0 2.0\n",
        encoding="utf-8",
    )
    (sparse / "images.txt").write_text(
        "1 1 0 0 0 0 0 0 1 test_000.png\n0 0 0\n"
        "2 1 0 0 0 0 0 0 1 train_000.png\n0 0 0\n",
        encoding="utf-8",
    )
    (sparse / "test.txt").write_text("test_000.png\n", encoding="utf-8")


def test_resolve_semantic_scene_root_uses_scene_meta_fallback(temp_repo: Path) -> None:
    scene_root = temp_repo / "surface_scene" / "room_0"
    scene_root.mkdir(parents=True)
    raw_root = temp_repo / "raw_scene" / "room_0"
    (raw_root / "habitat").mkdir(parents=True)
    (raw_root / "habitat" / "mesh_semantic.ply").write_text("ply", encoding="utf-8")
    (scene_root / "scene_meta.json").write_text(
        json.dumps({"raw_scene_root": str(raw_root)}),
        encoding="utf-8",
    )

    resolved = validator._resolve_semantic_scene_root(scene_root)

    assert resolved == raw_root.resolve()


def test_resolve_position_validation_inputs_prefers_prior_metadata_and_fallback_paths(temp_repo: Path) -> None:
    scene_root = temp_repo / "scene_root" / "room_0"
    _write_colmap_scene(scene_root)

    backend_run_dir = temp_repo / "outputs" / "gaussian_direct" / "backend_runs" / "demo_run" / "room_0"
    prior_init_dir = backend_run_dir / "prior_init"
    prior_init_dir.mkdir(parents=True)
    aligned_actual = prior_init_dir / "aligned_prior_00.ply"
    aligned_actual.write_text("ply", encoding="utf-8")

    (backend_run_dir / "cfg_args").write_text(
        f"Namespace(source_path='{scene_root}', model_path='{backend_run_dir}', images='images', depths='', train_test_exp=False, eval=True, sh_degree=3)",
        encoding="utf-8",
    )
    (prior_init_dir / "metadata.json").write_text(
        json.dumps(
            {
                "selected_priors": [
                    {
                        "aligned_prior": str(temp_repo / "stale" / "aligned_prior_00.ply"),
                        "target_object_id": 77,
                        "target_category": "sofa",
                    }
                ],
                "sfm_region_replacement_mode": "aligned_prior_aabb_union",
            }
        ),
        encoding="utf-8",
    )

    experiment_dir = temp_repo / "outputs" / "gaussian_direct" / "experiments" / "demo_run" / "room_0"
    experiment_dir.mkdir(parents=True)
    (experiment_dir / "backend_run.json").write_text(
        json.dumps(
            {
                "model_path": str(backend_run_dir),
                "repo_path": str(temp_repo / "external_repo"),
                "dataset_scene": {"scene_id": "room_0", "source_path": str(scene_root)},
                "prior_spec_json": str(experiment_dir / "prior_specs.json"),
            }
        ),
        encoding="utf-8",
    )
    (experiment_dir / "prior_specs.json").write_text(
        json.dumps([
            {"target_object_id": 77, "target_category": "sofa"},
        ]),
        encoding="utf-8",
    )

    inputs = validator.resolve_position_validation_inputs(backend_run_dir)

    assert inputs.input_consistency["status"] == "OK"
    assert inputs.selected_priors[0]["aligned_prior"] == str(aligned_actual.resolve())
    assert inputs.target_object_ids == [77]
    assert inputs.sfm_region_replacement_mode == "aligned_prior_aabb_union"
    assert len(inputs.test_views) == 1


def test_build_visible_prior_masks_filters_occluded_pixels() -> None:
    full = {
        "view.png": validator.PriorRenderFrame(
            rgb=np.zeros((2, 2, 3), dtype=np.uint8),
            depth=np.asarray([[1.0, 2.0], [0.0, 0.0]], dtype=np.float32),
        )
    }
    isolated = {
        77: {
            "view.png": validator.PriorRenderFrame(
                rgb=np.zeros((2, 2, 3), dtype=np.uint8),
                depth=np.asarray([[1.0, 2.03], [0.5, 0.0]], dtype=np.float32),
            )
        }
    }

    masks = validator.build_visible_prior_masks(full, isolated, depth_visibility_epsilon_m=0.02)

    np.testing.assert_array_equal(
        masks[77]["view.png"],
        np.asarray([[True, False], [False, False]], dtype=bool),
    )


def test_compute_position_metrics_marks_small_gt_as_ignored() -> None:
    gt_masks = {
        77: {
            "small.png": np.asarray([[False, False], [False, True]], dtype=bool),
            "valid.png": np.asarray(
                [[False, True, True], [False, True, True], [False, False, False]],
                dtype=bool,
            ),
        }
    }
    prior_masks = {
        77: {
            "small.png": np.asarray([[False, False], [False, False]], dtype=bool),
            "valid.png": np.asarray(
                [[False, True, False], [False, True, False], [False, False, False]],
                dtype=bool,
            ),
        }
    }

    metrics = validator.compute_position_metrics(gt_masks, prior_masks, min_visible_pixel_ratio=0.3)

    assert metrics[77]["views"]["small.png"]["status"] == "ignored_occluded"
    assert metrics[77]["views"]["valid.png"]["status"] == "valid"
    assert metrics[77]["median_mask_iou"] is not None


def test_generate_gt_semantic_masks_uses_bundle_renderer(monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = object()

    def fake_bundle(*args, **kwargs):
        return validator._SemanticRenderBundle(
            masks={1: {"view.png": np.asarray([[True]], dtype=bool)}},
            rgbs={"view.png": np.zeros((1, 1, 3), dtype=np.uint8)},
            backend_name="fake",
        )

    monkeypatch.setattr(validator, "_render_gt_semantic_bundle", fake_bundle)

    masks = validator.generate_gt_semantic_masks(inputs)

    assert masks[1]["view.png"][0, 0]


def test_validate_prior_positions_handles_baseline_no_prior(temp_repo: Path) -> None:
    scene_root = temp_repo / "scene_root" / "room_0"
    _write_colmap_scene(scene_root)

    backend_run_dir = temp_repo / "outputs" / "gaussian_direct" / "backend_runs" / "baseline_demo" / "room_0"
    backend_run_dir.mkdir(parents=True)
    (backend_run_dir / "cfg_args").write_text(
        f"Namespace(source_path='{scene_root}', model_path='{backend_run_dir}', images='images', depths='', train_test_exp=False, eval=True, sh_degree=3)",
        encoding="utf-8",
    )

    experiment_dir = temp_repo / "outputs" / "gaussian_direct" / "experiments" / "baseline_demo" / "room_0"
    experiment_dir.mkdir(parents=True)
    (experiment_dir / "backend_run.json").write_text(
        json.dumps(
            {
                "model_path": str(backend_run_dir),
                "repo_path": str(temp_repo / "external_repo"),
                "dataset_scene": {"scene_id": "room_0", "source_path": str(scene_root)},
                "selected_priors": [],
            }
        ),
        encoding="utf-8",
    )

    output_dir = temp_repo / "report"
    result = validator.validate_prior_positions(backend_run_dir, output_dir=output_dir)

    assert result.decision == "PASS"
    assert result.summary["decision_reasons"] == ["no_priors_to_validate"]
    assert (output_dir / "summary.json").exists()


def test_resolve_position_validation_inputs_detects_prior_spec_mismatch(temp_repo: Path) -> None:
    scene_root = temp_repo / "scene_root" / "room_0"
    _write_colmap_scene(scene_root)

    backend_run_dir = temp_repo / "outputs" / "gaussian_direct" / "backend_runs" / "mismatch_demo" / "room_0"
    prior_init_dir = backend_run_dir / "prior_init"
    prior_init_dir.mkdir(parents=True)
    aligned_actual = prior_init_dir / "aligned_prior_00.ply"
    aligned_actual.write_text("ply", encoding="utf-8")
    (backend_run_dir / "cfg_args").write_text(
        f"Namespace(source_path='{scene_root}', model_path='{backend_run_dir}', images='images', depths='', train_test_exp=False, eval=True, sh_degree=3)",
        encoding="utf-8",
    )
    (prior_init_dir / "metadata.json").write_text(
        json.dumps(
            {"selected_priors": [{"aligned_prior": str(aligned_actual), "target_object_id": 77, "target_category": "sofa"}]}
        ),
        encoding="utf-8",
    )

    experiment_dir = temp_repo / "outputs" / "gaussian_direct" / "experiments" / "mismatch_demo" / "room_0"
    experiment_dir.mkdir(parents=True)
    (experiment_dir / "backend_run.json").write_text(
        json.dumps(
            {
                "model_path": str(backend_run_dir),
                "repo_path": str(temp_repo / "external_repo"),
                "dataset_scene": {"scene_id": "room_0", "source_path": str(scene_root)},
                "prior_spec_json": str(experiment_dir / "prior_specs.json"),
            }
        ),
        encoding="utf-8",
    )
    (experiment_dir / "prior_specs.json").write_text(
        json.dumps([
            {"target_object_id": 74, "target_category": "chair"},
        ]),
        encoding="utf-8",
    )

    inputs = validator.resolve_position_validation_inputs(backend_run_dir)

    assert inputs.input_consistency["status"] == "INPUT_MISMATCH"
    assert any("target_object_id mismatch" in reason for reason in inputs.input_consistency["reasons"])


def test_resolve_position_validation_inputs_handles_cfg_args_parse_failure(temp_repo: Path) -> None:
    scene_root = temp_repo / "scene_root" / "room_0"
    _write_colmap_scene(scene_root)

    backend_run_dir = temp_repo / "outputs" / "gaussian_direct" / "backend_runs" / "parse_fail" / "room_0"
    backend_run_dir.mkdir(parents=True)
    (backend_run_dir / "cfg_args").write_text("not a namespace", encoding="utf-8")

    experiment_dir = temp_repo / "outputs" / "gaussian_direct" / "experiments" / "parse_fail" / "room_0"
    experiment_dir.mkdir(parents=True)
    (experiment_dir / "backend_run.json").write_text(
        json.dumps(
            {
                "model_path": str(backend_run_dir),
                "repo_path": str(temp_repo / "external_repo"),
                "dataset_scene": {"scene_id": "room_0", "source_path": str(scene_root)},
                "selected_priors": [],
            }
        ),
        encoding="utf-8",
    )

    inputs = validator.resolve_position_validation_inputs(backend_run_dir)

    assert inputs.input_consistency["status"] == "INPUT_MISMATCH"
    assert any("cfg_args parse failed" in reason for reason in inputs.input_consistency["reasons"])
    assert inputs.scene_root == scene_root.resolve()


def test_validate_prior_positions_writes_reports_on_cfg_args_missing(temp_repo: Path) -> None:
    backend_run_dir = temp_repo / "outputs" / "gaussian_direct" / "backend_runs" / "missing_cfg" / "room_0"
    backend_run_dir.mkdir(parents=True)
    experiment_dir = temp_repo / "outputs" / "gaussian_direct" / "experiments" / "missing_cfg" / "room_0"
    experiment_dir.mkdir(parents=True)
    (experiment_dir / "backend_run.json").write_text(
        json.dumps(
            {
                "model_path": str(backend_run_dir),
                "repo_path": str(temp_repo / "external_repo"),
                "dataset_scene": {"scene_id": "room_0", "source_path": str(temp_repo / "missing_scene")},
                "selected_priors": [],
            }
        ),
        encoding="utf-8",
    )

    output_dir = temp_repo / "validator_report"
    result = validator.validate_prior_positions(backend_run_dir, output_dir=output_dir)

    assert result.decision == "INPUT_MISMATCH"
    assert (output_dir / "summary.json").exists()
    assert (output_dir / "per_object_metrics.json").exists()
    assert (output_dir / "per_view_metrics.json").exists()
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert any("cfg_args missing" in reason for reason in summary["decision_reasons"])
