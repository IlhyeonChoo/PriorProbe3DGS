# AGENTS — exp/gaussian-direct

This file is the repo-local contract for the `PriorProbe3DGS-gaussian` worktree.
Keep global defaults in the user-level `AGENTS.md`; this file records only the meaning and operational boundaries required for this branch.
All repository paths below are relative to the repository root unless otherwise noted.

## Scope and Intent

- This worktree validates the path that inserts the retrieved prior as the original Gaussian asset during initialization from SfM views or sparse point clouds.
- The goal of prior insertion is to improve optimization convergence speed and final reconstruction quality.
- The `pointcloud` branch is only a comparison baseline. Do not reinterpret gaussian-direct as point cloud proxy insertion.
- If the user explicitly says the plan is already approved, or that only the results need to be recorded, proceed without asking for additional approval.
- Ask short questions only when experiment definition or result interpretation would materially diverge.

## Core Terms

- Prior: the source asset inserted into the initial 3D Gaussian state.
- Prior artifact: the registered Gaussian asset together with its feature and metadata bundle in the manifest.
- `source_prior_path`: original Gaussian asset selected by retrieval.
- `canonical_seed_path`: canonical seed used for alignment search and reference metadata.
- Alignment representation: the canonical seed and canonical metadata used to compute where and how to place the prior.
- Insertion representation:
  The representation actually passed into backend initialization. If `insertion_representation=gaussian_direct`, use the original Gaussian asset. If `pointcloud_proxy`, use the canonical seed.
- `insertion_source_path`: asset actually passed into backend initialization.
- Experiment spec: explicit config bundle or plan document defining how the run should execute.
- Report artifact: documents under `docs/experiment_results/` and summary outputs under `outputs/gaussian_direct/reports/`.

## Repository Map

- [scripts/run_experiment.py](scripts/run_experiment.py): experiment entrypoint, retrieval/alignment/insertion wiring, backend launch metadata
- [scripts/train_vanilla_3dgs_backend.py](scripts/train_vanilla_3dgs_backend.py): backend training entrypoint for vanilla 3DGS runs
- [scripts/evaluate.py](scripts/evaluate.py): evaluation entrypoint, reads backend run summaries, computes reconstruction metrics
- [scripts/export_results.py](scripts/export_results.py): report/export entrypoint for summary markdown and CSV artifacts
- [src/priorprobe/prior_library/library.py](src/priorprobe/prior_library/library.py): prior manifest registry
- [src/priorprobe/retrieval/retriever.py](src/priorprobe/retrieval/retriever.py): retrieval selection logic
- [src/priorprobe/insertion](src/priorprobe/insertion): alignment search, transform payload generation, insertion-side helpers
- [src/priorprobe/optimization/vanilla_3dgs.py](src/priorprobe/optimization/vanilla_3dgs.py): backend config and command construction
- [src/priorprobe/optimization/trainer.py](src/priorprobe/optimization/trainer.py): training-side orchestration helpers
- [src/priorprobe/runtime_paths.py](src/priorprobe/runtime_paths.py): dated docs/report path helpers
- `outputs/gaussian_direct/experiments/**/backend_run.json`: canonical per-run provenance source of truth
- [configs/experiments](configs/experiments): experiment presets
- [configs/datasets](configs/datasets): dataset family definitions
- [docs/experiment_plans](docs/experiment_plans): approved or candidate experiment specs
- [docs/experiment_results](docs/experiment_results): dated milestone reports
- [docs/notes](docs/notes): bug notes, diagnostics, supporting observations
- [outputs/gaussian_direct/reports](outputs/gaussian_direct/reports): canonical report CSV/JSON/Markdown outputs

## Documentation Path Conventions

- Use project-root-relative paths for repository-internal paths in prose and inline code unless a more specific local rule is stated.
- Use document-relative links for Markdown links that point to files inside the repository.
- Keep repository-external paths as absolute paths by default.
- When the same external root appears repeatedly, define a short local variable alias and reuse it.
- Do not replace external Markdown link targets with variable expressions when direct clickability matters.
- Keep document-specific variable names, mixed-policy exceptions, and one-off path migration plans in a dedicated policy or plan document rather than expanding this file.

## Hard Invariants

- Alignment and insertion are different concepts. Alignment may use the canonical seed, but insertion must not silently fall back to point cloud proxy behavior.
- In `gaussian_direct` experiments, the insertion source must be the original Gaussian asset. Keep the canonical seed only for alignment and reference purposes.
- Preserve the meaning of the pointcloud baseline when adding gaussian-direct-specific logic.
- Assume current gaussian-direct orchestration supports only `backend.init_mode in {merge, replace}` unless the related plans and reports are updated together.
- Record `source_prior_path`, `canonical_seed_path`, `insertion_source_path`, and `insertion_representation` together whenever possible.
- New experiment config names must use the `gaussian_direct_` prefix.
- Store experiment artifacts only under `outputs/gaussian_direct/`.
- Keep the current PLY naming behavior:
  - Real file: `{design}[_protection]_iter_{N}.ply`
  - Compatibility link: `point_cloud.ply`

## Source of Truth

- Check context in this order before new work:
  1. `docs/experiment_plans/`
  2. `docs/experiment_results/`
  3. `docs/notes/`
  4. `configs/experiments/` and `configs/datasets/`
  5. Existing artifacts under `outputs/gaussian_direct/`
- Reuse an existing condition if it already matches the requested experiment instead of launching a duplicate run.
- The canonical run provenance source is `outputs/gaussian_direct/experiments/**/backend_run.json`.
- If the backend writes `prior_init/metadata.json`, reconcile selected prior and insertion settings against that file again.

## Dataset and Result Semantics

- `roomwide_96/192/384` is the legacy biased room-wide dataset, not a neutral room scan.
- `roomwide_v2_96/192/384` is the balanced azimuth family.
- When modifying the room-wide exporter, inspect azimuth distribution around `room_center` before focusing on view count.
- If `scene_meta.json` has `render_backend=semantic_point_renderer`, expect point-like GT appearance and do not interpret it as RGB photography.
- Do not generalize from a single-scene result.
- Separate likely causes before concluding, including data bias, SH mismatch, overlap interference, prior density, protection, and renderer differences.

## Execution and Reporting Rules

- `prior-builder` work must not silently change training-loop or optimizer behavior unless the task is explicitly about initialization inputs for prior construction.
- `prior-runtime` work must not silently change prior provenance fields, insertion semantics, or the meaning of the pointcloud baseline.
- `experiment-runner` work must execute an explicit spec and must not invent settings to force a run to succeed.
- `quality-gate` work is review-first: prefer identifying evidence gaps, consistency problems, and risks over direct edits.
- When adding a new experiment, explicitly state comparison target, scene, dataset family, iteration count, prior insertion condition, protection condition, output directory, and report location.
- Do not reuse an existing output directory for a materially different run.
- Do not perform large deletions unless the user explicitly requested them.
- Do not overwrite existing reports. Write new reports to `docs/experiment_results/{MM-DD}_{slug}_{YYYY}.md`.
- Use LF line endings for report CSV files.
- The canonical report artifact location is `outputs/gaussian_direct/reports/`.
- Result reports must include experiment goal, config, dataset family, and scene, key metrics, baseline differences, interpretation, and next steps.
- Every handoff must include:
  - `what changed`
  - `what was checked`
  - `what remains risky`
  - `next concrete action`

## Delegation Defaults

- Keep the main session focused on user-coupled work: goal clarification, baseline comparison, causal interpretation, next-experiment prioritization, final trade-off explanation.
- Delegate bounded tasks whenever practical: artifact collection, targeted code-path checks, config drafting, dry-runs, smoke checks, consistency review.
- Delegated tasks should have a small scope and a clear write set.
- Delegate long-running training or experiment execution to the local `experiment-runner` agent only when the user explicitly asks to run, continue, resume, or launch an experiment.
- Request delegated results in this format:
  - `files or paths checked`
  - `commands or artifacts verified`
  - `key findings`
  - `remaining uncertainty`
  - `next recommended action`
- Do not fully re-explore delegated results in the main session. Use them to drive analysis and planning.

## Definition of Done

- Prior or metadata changes preserve the meaning of the initialization-stage prior and keep provenance loadable and coherent.
- Runtime or insertion changes preserve mutual consistency among `source_prior_path`, `canonical_seed_path`, `insertion_source_path`, and `insertion_representation`, with a relevant dry-run, smoke check, or artifact check recorded.
- Experiment spec changes make the comparison target, scene, dataset family, iteration count, prior insertion condition, protection condition, output directory, and report location explicit.
- Report changes record metrics, baseline deltas, interpretation, next steps, and unresolved risks without overwriting prior reports.
