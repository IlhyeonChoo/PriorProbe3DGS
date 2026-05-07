# Branch Merge Plan: exp/gaussian-direct → main / exp/pointcloud

**Date**: 2026-04-13
**Source branch**: `exp/gaussian-direct` (HEAD: `da75d40`)
**Target branches**: `main` (`7dd4dda`), `exp/pointcloud` (`fb5ae89`)
**Common ancestor**: `101e6b5`

## Summary

`exp/gaussian-direct` has ~50 commits since diverging from `main`, containing a mix of:
- General-purpose library improvements (should go to `main`)
- Shared dataset/infrastructure configs (should go to `main`)
- Experiment-specific configs, outputs, reports (stay on this branch)

Since `main` and `exp/pointcloud` share the same ancestor, merging to `main` first
makes the shared code available to both branches.

---

## Category 1: MERGE TO MAIN — Core Library (`src/`)

These are general-purpose library improvements that all branches benefit from.

### New files (not in main)
| File | Description | Lines |
|------|-------------|-------|
| `src/priorprobe/experiment_storage.py` | Experiment storage utility | +44 |
| `src/priorprobe/gaussian_affine.py` | Gaussian affine transform utils | +164 |
| `src/priorprobe/gaussian_prior_diagnostics.py` | Prior diagnostics tools | +108 |
| `src/priorprobe/replica_surface.py` | Surface dataset handling (Phase 5) | +332 |
| `src/priorprobe/result_ply_naming.py` | PLY result naming conventions | +139 |
| `src/priorprobe/runtime_paths.py` | Branch-aware runtime path management | +96 |

### Modified files (exist in main)
| File | Description | Delta |
|------|-------------|-------|
| `src/priorprobe/evaluation/metrics.py` | Enhanced evaluation metrics | +118/-1 |
| `src/priorprobe/optimization/trainer.py` | Trainer small fix | +3/-1 |
| `src/priorprobe/optimization/vanilla_3dgs.py` | 3DGS backend enhancement | +57 |
| `src/priorprobe/prior_assets.py` | Minor addition | +1 |
| `src/priorprobe/replica_export.py` | Major replica export enhancement | +423/-49 |
| `src/priorprobe/shapesplat_modelnet.py` | ShapeSplat improvement | +13/-2 |

---

## Category 2: MERGE TO MAIN — Tests

Corresponding tests for the library code above.

### New tests
- `tests/test_evaluation_metrics.py`
- `tests/test_experiment_storage.py`
- `tests/test_gaussian_affine.py`
- `tests/test_gaussian_prior_diagnostics.py`
- `tests/test_prior_assets.py`
- `tests/test_replica_export.py`
- `tests/test_replica_surface.py`
- `tests/test_result_ply_naming.py`
- `tests/test_runtime_paths.py`
- `tests/test_shapesplat_modelnet.py`

### Modified tests
- `tests/test_vanilla_3dgs_backend.py`

### Experiment-specific tests (STAY on branch)
- `tests/test_build_initial_snapshot_viewer.py`
- `tests/test_build_recent_inspection_viewers.py`
- `tests/test_inventory_replica_image_counts.py`
- `tests/test_rename_to_date_format.py`
- `tests/test_report_replica_gaussian_direct_office0_cross_validation.py`
- `tests/test_run_experiment_script.py`
- `tests/test_update_internal_refs.py`

---

## Category 3: MERGE TO MAIN — General Scripts

| File | Status | Description |
|------|--------|-------------|
| `scripts/build_initial_snapshot_viewer.py` | MODIFIED | Viewer builder |
| `scripts/export_replica_multi_oracle_scene.py` | MODIFIED | Oracle scene export |
| `scripts/export_results.py` | MODIFIED | Results export |
| `scripts/run_experiment.py` | MODIFIED | Experiment runner |
| `scripts/train_vanilla_3dgs_backend.py` | MODIFIED | 3DGS training backend |
| `scripts/inventory_replica_image_counts.py` | NEW | Image count inventory |
| `scripts/merge_prior_manifests.py` | NEW | Prior manifest merger |
| `scripts/prepare_replica_exact_target_priors.py` | NEW | Target prior prep |
| `scripts/prepare_replica_phase5_surface_assets.py` | NEW | Phase 5 surface asset prep |
| `scripts/rename_result_point_clouds.py` | NEW | PLY renaming utility |
| `scripts/rename_to_date_format.py` | NEW | Date-based renaming |
| `scripts/update_internal_refs.py` | NEW | Internal reference updater |
| `scripts/build_recent_inspection_viewers.py` | NEW | Inspection viewer builder |

---

## Category 4: MERGE TO MAIN — Infrastructure

| File | Notes |
|------|-------|
| `.gitignore` | Significantly improved — cleaner patterns, branch-aware output ignore |
| `pyproject.toml` | Added rendering deps: freetype-py, imageio, PyOpenGL, pyglet, pyrender, trimesh |
| `uv.lock` | Lockfile update for above |

### ⚠️ CAUTION: `configs/base/project.yaml`
This file changes `outputs_dir` from `outputs` → `outputs/gaussian_direct`.
For main, this should be reverted to `outputs` (or made branch-configurable via `runtime_paths.py`).

---

## Category 5: MERGE TO MAIN — Dataset Configs

Shared dataset definitions usable by any branch:
- `configs/datasets/replica_multi_diverse_dense_384_shared.yaml`
- `configs/datasets/replica_multi_roomwide_192_shared.yaml`
- `configs/datasets/replica_multi_roomwide_384_shared.yaml`
- `configs/datasets/replica_multi_roomwide_96_shared.yaml`
- `configs/datasets/replica_multi_roomwide_v2_192_shared.yaml`
- `configs/datasets/replica_multi_roomwide_v2_384_shared.yaml`
- `configs/datasets/replica_multi_roomwide_v2_384_surface_rgb_shared.yaml`
- `configs/datasets/replica_multi_roomwide_v2_96_shared.yaml`

---

## Category 6: STAY ON BRANCH — Experiment-Specific

### Experiment configs (~100+ files)
All `configs/experiments/gaussian_direct_*` files — specific to this branch's experiments.

### Experiment outputs (~750+ files)
All `outputs/gaussian_direct/experiments/` files.

### Experiment reports/docs (~50+ files)
- `docs/experiment_results/` — all experiment result markdown files
- `docs/experiment_plans/` — all experiment plan markdown files
- `docs/notes/` — most notes (except this plan itself)
- `docs/gaussian_direct_branch_plan.md`
- `docs/phase4_archive_guide_2026-03-23.md`

### Experiment-specific scripts
- `scripts/report_replica_gaussian_direct_*.py` (12 files)
- `scripts/run_replica_gaussian_direct_upper_bound.py`
- `scripts/migrate_branch_outputs.py`
- `scripts/rename_gaussian_direct_experiment_dirs.py`

---

## Category 7: STAY ON BRANCH — AI/Tooling Config

These are conversation-specific and should not pollute main:
- `AGENTS.md` / `AGENTS.md.bak`
- `.codex/` directory (5 files)

---

## Recommended Merge Strategy

### Approach: Create integration branch, selective file copy

Cherry-picking individual commits is impractical because many commits mix general and
experiment-specific changes. Instead:

1. **Create branch** `integrate/shared-infra` from `main`
2. **Copy files** from `exp/gaussian-direct` for Categories 1–5
3. **Fix** `configs/base/project.yaml` to use generic `outputs` path (not `gaussian_direct`)
4. **Run tests** to verify nothing is broken
5. **PR** `integrate/shared-infra` → `main`
6. After merge, `exp/pointcloud` can rebase/merge from updated `main`

### Git commands outline

```bash
# Step 1: Create integration branch from main
git checkout main
git checkout -b integrate/shared-infra

# Step 2: Bring files from exp/gaussian-direct
# (src, tests, general scripts, configs/datasets, infra)
git checkout exp/gaussian-direct -- \
  src/priorprobe/experiment_storage.py \
  src/priorprobe/gaussian_affine.py \
  src/priorprobe/gaussian_prior_diagnostics.py \
  src/priorprobe/replica_surface.py \
  src/priorprobe/result_ply_naming.py \
  src/priorprobe/runtime_paths.py \
  src/priorprobe/evaluation/metrics.py \
  src/priorprobe/optimization/trainer.py \
  src/priorprobe/optimization/vanilla_3dgs.py \
  src/priorprobe/prior_assets.py \
  src/priorprobe/replica_export.py \
  src/priorprobe/shapesplat_modelnet.py \
  tests/test_evaluation_metrics.py \
  tests/test_experiment_storage.py \
  tests/test_gaussian_affine.py \
  tests/test_gaussian_prior_diagnostics.py \
  tests/test_prior_assets.py \
  tests/test_replica_export.py \
  tests/test_replica_surface.py \
  tests/test_result_ply_naming.py \
  tests/test_runtime_paths.py \
  tests/test_shapesplat_modelnet.py \
  tests/test_vanilla_3dgs_backend.py \
  scripts/build_initial_snapshot_viewer.py \
  scripts/export_replica_multi_oracle_scene.py \
  scripts/export_results.py \
  scripts/run_experiment.py \
  scripts/train_vanilla_3dgs_backend.py \
  scripts/inventory_replica_image_counts.py \
  scripts/merge_prior_manifests.py \
  scripts/prepare_replica_exact_target_priors.py \
  scripts/prepare_replica_phase5_surface_assets.py \
  scripts/rename_result_point_clouds.py \
  scripts/rename_to_date_format.py \
  scripts/update_internal_refs.py \
  scripts/build_recent_inspection_viewers.py \
  configs/datasets/ \
  .gitignore \
  pyproject.toml \
  uv.lock

# Step 3: Fix project.yaml — revert outputs_dir to generic path
git checkout exp/gaussian-direct -- configs/base/project.yaml
# Then manually edit outputs_dir back to "outputs" and logs_dir to "logs"

# Step 4: Run tests
uv run pytest tests/ -x

# Step 5: Commit and push
git add -A
git commit -m "Merge shared infrastructure from exp/gaussian-direct"
git push -u origin integrate/shared-infra
gh pr create --base main --title "Shared infra from gaussian-direct"
```

---

## Decisions Needed

1. **`configs/base/project.yaml`**: Should `outputs_dir` be `outputs` (generic) or should
   `runtime_paths.py` handle branch-specific paths automatically? The latter is cleaner.
2. **Dataset configs**: Some reference surface-specific data. Confirm all 8 are universal.
3. **`pyproject.toml` rendering deps**: The new deps (pyrender, trimesh, etc.) are in
   `[experiments]` optional group — safe to merge but confirm they're wanted globally.
4. **Test coverage**: Run full test suite on the integration branch before merging.
