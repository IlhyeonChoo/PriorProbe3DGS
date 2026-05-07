# Shared Infra Merge Plan Refresh: `exp/gaussian-direct` -> `origin/main`

**Date**: 2026-04-17
**Last updated**: 2026-05-04
**Purpose**: Replace the earlier merge note with a cleaner execution plan while keeping the older note for comparison.
**Comparison reference**: [04-13_branch_merge_plan_2026.md](./04-13_branch_merge_plan_2026.md)

## Current Baseline

- Source committed snapshot for this merge pass: `exp/gaussian-direct` at `bf91e1f`
- Current target base: `origin/main` at `83b3f69`
- Shared ancestor between `origin/main` and `exp/gaussian-direct`: `101e6b5`
- This pass includes the original `da75d40` shared set plus the four committed follow-up commits through `bf91e1f`.
- Local untracked docs, reports, and output artifacts are **not** part of this merge pass.

## Why This Refresh Exists

The 2026-04-13 note remains useful as a comparison artifact, but it no longer matches the cleanest execution path.

- The operative target is now `origin/main`, not the older local `main` snapshot.
- The previous note misclassified several shared tests as branch-only.
- The previous note copied `configs/datasets/` too broadly. This refresh locks the merge set to an explicit list of eight shared dataset files.
- The previously deferred validator, sweep, room-contained preset, and geometry-gate work is now committed and included where it is shared.

## Locked Decisions For This Pass

- Merge only the **committed shared set** from `bf91e1f`.
- Include committed validator, sweep, room-contained dataset, and geometry-gate shared work.
- Do **not** pull in `gaussian_direct_*` experiment configs, result docs, output artifacts, or local AI/tooling files.
- Keep `configs/base/project.yaml` generic on `main` with `outputs_dir: outputs`.
- Keep `configs/base/project.yaml` generic on `main` with `logs_dir: logs`.
- Use `runtime_paths.py` as the branch-aware helper, but do not encode `gaussian_direct` defaults into `main`.

## In Scope

### Core library

- `src/priorprobe/experiment_storage.py`
- `src/priorprobe/gaussian_affine.py`
- `src/priorprobe/gaussian_prior_diagnostics.py`
- `src/priorprobe/replica_surface.py`
- `src/priorprobe/result_ply_naming.py`
- `src/priorprobe/runtime_paths.py`
- `src/priorprobe/validation/__init__.py`
- `src/priorprobe/validation/prior_position_validator.py`
- `src/priorprobe/evaluation/metrics.py`
- `src/priorprobe/optimization/trainer.py`
- `src/priorprobe/optimization/vanilla_3dgs.py`
- `src/priorprobe/prior_assets.py`
- `src/priorprobe/replica_export.py`
- `src/priorprobe/shapesplat_modelnet.py`

### Shared tests

New tests:
- `tests/test_experiment_storage.py`
- `tests/test_gaussian_affine.py`
- `tests/test_gaussian_prior_diagnostics.py`
- `tests/test_replica_surface.py`
- `tests/test_result_ply_naming.py`
- `tests/test_build_initial_snapshot_viewer.py`
- `tests/test_build_recent_inspection_viewers.py`
- `tests/test_inventory_replica_image_counts.py`
- `tests/test_rename_to_date_format.py`
- `tests/test_run_experiment_script.py`
- `tests/test_update_internal_refs.py`
- `tests/test_collect_prior_position_fine_sweep.py`
- `tests/test_collect_prior_position_fine_sweep_override.py`
- `tests/test_collect_prior_position_sweep.py`
- `tests/test_prepare_replica_phase5_surface_assets.py`
- `tests/test_prior_position_validator.py`
- `tests/test_validate_prior_positions_script.py`

Modified tests:
- `tests/test_evaluation_metrics.py`
- `tests/test_prior_assets.py`
- `tests/test_replica_export.py`
- `tests/test_runtime_paths.py`
- `tests/test_shapesplat_modelnet.py`
- `tests/test_vanilla_3dgs_backend.py`

### General scripts

- `scripts/build_initial_snapshot_viewer.py`
- `scripts/build_recent_inspection_viewers.py`
- `scripts/export_replica_multi_oracle_scene.py`
- `scripts/export_results.py`
- `scripts/inventory_replica_image_counts.py`
- `scripts/merge_prior_manifests.py`
- `scripts/prepare_replica_exact_target_priors.py`
- `scripts/prepare_replica_phase5_surface_assets.py`
- `scripts/rename_result_point_clouds.py`
- `scripts/rename_to_date_format.py`
- `scripts/run_experiment.py`
- `scripts/train_vanilla_3dgs_backend.py`
- `scripts/update_internal_refs.py`
- `scripts/collect_prior_position_fine_sweep.py`
- `scripts/collect_prior_position_sweep.py`
- `scripts/validate_prior_positions.py`

### Infrastructure and shared configs

- `.gitignore`
- `pyproject.toml`
- `uv.lock`
- `configs/base/project.yaml` with generic runtime paths restored

### Shared dataset configs

- `configs/datasets/replica_multi_diverse_dense_384_shared.yaml`
- `configs/datasets/replica_multi_roomwide_192_shared.yaml`
- `configs/datasets/replica_multi_roomwide_384_shared.yaml`
- `configs/datasets/replica_multi_roomwide_96_shared.yaml`
- `configs/datasets/replica_multi_roomwide_v2_192_shared.yaml`
- `configs/datasets/replica_multi_roomwide_v2_384_shared.yaml`
- `configs/datasets/replica_multi_roomwide_v2_384_surface_rgb_shared.yaml`
- `configs/datasets/replica_multi_roomwide_v2_96_shared.yaml`
- `configs/datasets/replica_multi_roomwide_v2_384_surface_rgb_roomcontained_hq192_ds_shared.yaml`
- `configs/datasets/replica_multi_roomwide_v2_384_surface_rgb_roomcontained_hq192_ds_v2_shared.yaml`
- `configs/datasets/replica_multi_roomwide_v2_384_surface_rgb_roomcontained_hq192_shared.yaml`
- `configs/datasets/replica_multi_roomwide_v2_384_surface_rgb_roomcontained_shared.yaml`
- `configs/datasets/replica_multi_roomwide_v2_384_surface_rgb_roomcontained_sofa77_hq_shared.yaml`

## Explicitly Out Of Scope

These items should stay on `exp/gaussian-direct` until reviewed as a separate follow-up:

- All `configs/experiments/gaussian_direct_*`
- All `outputs/gaussian_direct/**`
- Most `docs/experiment_plans/`, `docs/experiment_results/`, and `docs/notes/`
- `scripts/report_replica_gaussian_direct_*.py`
- `scripts/run_replica_gaussian_direct_upper_bound.py`
- `scripts/migrate_branch_outputs.py`
- `scripts/rename_gaussian_direct_experiment_dirs.py`
- `AGENTS.md`, `AGENTS.md.bak`, `.codex/`
- `configs/experiments/gaussian_direct_surface_rgb_roomcontained_baseline_smoke_1000.yaml`
- `configs/experiments/gaussian_direct_surface_rgb_roomcontained_prior_100k_geo_smoke_1000.yaml`

## Recommended Execution Procedure

1. Create a clean integration worktree from `origin/main`.
2. Copy only the committed shared file set from `bf91e1f`.
3. Restore generic runtime paths in `configs/base/project.yaml`.
4. Run targeted shared tests before any commit.
5. Review diff, then commit and open a PR only after the staged set matches this document.

## Current Execution Status

The integration pass has already been assembled in a separate worktree:

- Worktree: `/tmp/priorprobe-integrate-shared-infra`
- Branch: `integrate/shared-infra`
- Base: `origin/main`
- Source copied from: `bf91e1f`

Applied checks:

```bash
uv run pytest \
  tests/test_experiment_storage.py \
  tests/test_gaussian_affine.py \
  tests/test_gaussian_prior_diagnostics.py \
  tests/test_evaluation_metrics.py \
  tests/test_prior_assets.py \
  tests/test_replica_export.py \
  tests/test_replica_surface.py \
  tests/test_result_ply_naming.py \
  tests/test_runtime_paths.py \
  tests/test_shapesplat_modelnet.py \
  tests/test_vanilla_3dgs_backend.py \
  tests/test_build_initial_snapshot_viewer.py \
  tests/test_build_recent_inspection_viewers.py \
  tests/test_inventory_replica_image_counts.py \
  tests/test_rename_to_date_format.py \
  tests/test_run_experiment_script.py \
  tests/test_update_internal_refs.py \
  tests/test_prepare_replica_phase5_surface_assets.py \
  tests/test_prior_position_validator.py \
  tests/test_validate_prior_positions_script.py \
  tests/test_collect_prior_position_sweep.py \
  tests/test_collect_prior_position_fine_sweep.py \
  tests/test_collect_prior_position_fine_sweep_override.py
```

Observed result:

- 98 tests passed in `/tmp/priorprobe-integrate-shared-infra`
- No failures in the selected shared merge set

## Remaining Risks

- The validator code still contains gaussian-direct output-path assumptions for deriving backend provenance. That is acceptable for this pass because the runtime gate and scripts are intended for the current experiment family.
- Branch-only experiment configs and output artifacts must remain absent from the integration diff.

## Next Concrete Action

- Keep this document as the active checklist.
- If the current integration worktree diff still matches this document, commit the `integrate/shared-infra` worktree changes next.
