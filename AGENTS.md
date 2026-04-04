# AGENTS.md — exp/gaussian-direct

This file is the repo-local contract for the `PriorProbe3DGS-gaussian` worktree.
Keep global defaults in the user-level `AGENTS.md`; this file records only the meaning and operational boundaries required for this branch.

## Project Scope

- The purpose of this worktree is to validate the path that inserts the retrieved prior as the original Gaussian asset during the initialization stage that builds 3D Gaussians from SfM views or sparse point clouds.
- The working goal of prior insertion is to improve optimization convergence speed and final reconstruction quality.
- The `pointcloud` branch is only a comparison baseline. Do not reinterpret or mix the meaning of gaussian-direct with the point cloud proxy meaning in this branch.
- If the user explicitly says that the plan is already approved, that work should continue without additional approval, or that only the results need to be recorded, proceed without asking for additional approval.
- Ask short questions only when the experiment definition or result interpretation would materially diverge.

## Domain Glossary

- Prior:
  A project-specific source asset inserted during the stage that turns SfM views or sparse point clouds into the initial 3D Gaussian state.
  In this branch, the prior is typically an object-level Gaussian asset, and its purpose is to improve convergence speed and final reconstruction quality.
- Prior artifact:
  The registered Gaussian asset together with its feature and metadata bundle in the manifest.
- `source_prior_path`:
  The path to the original Gaussian asset selected by retrieval.
- `canonical_seed_path`:
  The canonical seed path used for alignment search and reference metadata.
- Alignment representation:
  The representation used to compute where and how to place the prior. In this branch, this refers to the canonical seed and canonical metadata.
- Insertion representation:
  The representation actually passed into backend initialization. If `insertion_representation=gaussian_direct`, use the original Gaussian asset. If `pointcloud_proxy`, use the canonical seed.
- Experiment spec:
  The plan document or explicit config bundle that defines how the run should be executed.
- Report artifact:
  The documents under `docs/experiment_results/` and the CSV/JSON/Markdown outputs under `outputs/gaussian_direct/reports/`.

## Repository Map

- [scripts/run_experiment.py](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/scripts/run_experiment.py):
  experiment entrypoint, retrieval/alignment/insertion wiring, backend launch metadata
- [scripts/train_vanilla_3dgs_backend.py](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/scripts/train_vanilla_3dgs_backend.py):
  backend training entrypoint for vanilla 3DGS runs launched from experiment orchestration
- [scripts/evaluate.py](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/scripts/evaluate.py):
  evaluation entrypoint that reads backend run summaries and computes reconstruction metrics
- [scripts/export_results.py](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/scripts/export_results.py):
  report/export entrypoint for summary markdown and CSV artifacts under the gaussian-direct output root
- [src/priorprobe/prior_library/library.py](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/src/priorprobe/prior_library/library.py):
  prior manifest registry
- [src/priorprobe/retrieval/retriever.py](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/src/priorprobe/retrieval/retriever.py):
  retrieval selection logic
- [src/priorprobe/insertion](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/src/priorprobe/insertion):
  alignment search, transform payload generation, insertion-side helpers
- [src/priorprobe/optimization/vanilla_3dgs.py](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/src/priorprobe/optimization/vanilla_3dgs.py):
  backend config and command construction
- [src/priorprobe/optimization/trainer.py](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/src/priorprobe/optimization/trainer.py):
  training-side orchestration helpers shared by experiment launch code
- [src/priorprobe/runtime_paths.py](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/src/priorprobe/runtime_paths.py):
  dated docs/report path helpers
- `outputs/gaussian_direct/experiments/**/backend_run.json`:
  canonical per-run source of truth for provenance, backend launch settings, and downstream evaluation/reporting inputs
- [configs/experiments](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/configs/experiments):
  experiment presets
- [configs/datasets](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/configs/datasets):
  dataset family definitions
- [docs/experiment_plans](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/docs/experiment_plans):
  approved or candidate experiment specs
- [docs/experiment_results](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/docs/experiment_results):
  dated milestone reports
- [docs/notes](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/docs/notes):
  bug notes, diagnostics, supporting observations
- [outputs/gaussian_direct/reports](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/reports):
  canonical report CSV/JSON/Markdown outputs

## Pipeline Invariants

- Alignment and insertion are not the same concept. Even if alignment search uses the canonical seed, insertion must not silently become point cloud proxy insertion.
- In `gaussian_direct` experiments, the insertion source must be the original Gaussian asset. Keep the canonical seed only for alignment and reference purposes.
- Assume that `gaussian_direct` orchestration currently supports only `backend.init_mode in {merge, replace}`. If that meaning changes, update the related plan documents and result documents together.
- For selected prior provenance, record `source_prior_path`, `canonical_seed_path`, `insertion_source_path`, and `insertion_representation` together whenever possible.
- When adding gaussian-direct-specific logic, do not change the meaning of the pointcloud baseline.
- New experiment config names must use the `gaussian_direct_` prefix.
- Store experiment artifacts only under `outputs/gaussian_direct/`.
- Follow the current implementation for result PLY naming.
  - Real file: `{design}[_protection]_iter_{N}.ply`
  - Compatibility link: `point_cloud.ply`

## Dataset and Result Semantics

- `roomwide_96/192/384` is the legacy biased room-wide dataset. Do not interpret it as a neutral room scan.
- `roomwide_v2_96/192/384` is the balanced azimuth family.
- When modifying the room-wide exporter, inspect the position azimuth distribution around `room_center` before focusing on the view count.
- If `scene_meta.json` has `render_backend=semantic_point_renderer`, it is expected that the GT looks point-like. Do not interpret it as actual RGB photography.
- Do not generalize from a single-scene result to the overall conclusion.
- If a result differs from expectation, separate causes before concluding. Consider data bias, SH mismatch, overlap interference, prior density, protection, and renderer differences as distinct factors.

## Workflow Boundaries

- `prior-builder`-style work must not silently modify the training loop or optimizer behavior unless the task is explicitly about initialization inputs for prior construction.
- `prior-runtime`-style work must not silently change prior provenance fields, insertion semantics, or the meaning of the pointcloud baseline.
- `experiment-runner`-style work must execute an explicit spec and must not invent settings or alter retrieval/insertion semantics to force a run to succeed.
- `quality-gate`-style work is review-first: prefer identifying evidence gaps, consistency problems, and risks over direct edits.
- When starting new work, check the source of truth in the following order.
  1. Relevant latest documents under [docs/experiment_plans](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/docs/experiment_plans)
  2. Relevant latest documents under [docs/experiment_results](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/docs/experiment_results)
  3. Relevant documents under [docs/notes](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/docs/notes)
  4. Relevant [configs/experiments](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/configs/experiments) and [configs/datasets](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/configs/datasets)
  5. Existing artifacts under `outputs/gaussian_direct/`
- If the same experimental condition already exists, check whether it can be reused before launching a duplicate run.
- When adding a new experiment, explicitly specify the comparison target, scene, dataset family, iteration count, prior insertion condition, protection condition, and report location.
- Do not reuse an existing output directory for a materially different run.
- Do not perform large deletions unless the user explicitly requested them.

## Delegation Defaults

- The main session should focus on work that directly couples with the user.
  - Clarifying the goal
  - Comparing results against the baseline
  - Organizing causal hypotheses
  - Designing the next experiment priority
  - Explaining final conclusions and trade-offs
- Delegate clearly bounded tasks whenever practical.
  - Collecting related plans, results, configs, and output inventories
  - Checking a specific code path or metadata flow
  - Preparing config drafts and mechanical document edits
  - Running `--dry-run`, smoke tests, or artifact existence checks
  - Reviewing consistency between changes and reports
- Delegated tasks should have a small scope and a clear write set.
- Delegate long-running training or experiment execution to the local `experiment-runner` agent when the user explicitly asks to run, continue, resume, or launch an experiment.
- Always request delegated task results in the following format and then integrate them.
  - `files or paths checked`
  - `commands or artifacts verified`
  - `key findings`
  - `remaining uncertainty`
  - `next recommended action`
- The main session should not fully re-explore delegated results. Use them to drive analysis and planning instead.

## Definition of Done

- Prior or metadata changes:
  the prior meaning remains consistent with the initialization stage, and the affected manifest or metadata path can still be loaded with coherent provenance.
- Runtime or insertion changes:
  the relevant dry-run, smoke path, or artifact existence check is recorded, and `source_prior_path`, `canonical_seed_path`, `insertion_source_path`, and `insertion_representation` remain mutually consistent.
- Experiment spec changes:
  the comparison target, scene, dataset family, iteration count, prior insertion condition, protection condition, output dir, and report location are all explicit.
- Report changes:
  metrics, baseline deltas, interpretation, next steps, and unresolved risks are written without overwriting previous reports.

## Reporting and Handoff

- Do not overwrite existing reports when adding new experiment results. Create a new file using the format `docs/experiment_results/{MM-DD}_{slug}_{YYYY}.md`.
- Use LF line endings for report CSV files.
- The canonical report artifact location is `outputs/gaussian_direct/reports/`.
- The primary source of truth for run provenance is `backend_run.json`. If the backend writes `prior_init/metadata.json`, reconcile the selected prior and insertion settings against that file again.
- Result reports must include at least the following.
  - experiment goal
  - config / dataset / scene
  - key metrics
  - differences from the comparison baseline
  - interpretation
  - next steps
- Every work handoff must always include these four lines.
  - `what changed`
  - `what was checked`
  - `what remains risky`
  - `next concrete action`
