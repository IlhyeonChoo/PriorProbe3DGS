# Replica Gaussian-Direct Surface RGB Baseline Determinism (2026-03-31)

## Purpose

Measure whether the baseline variance observed in `surface_rgb_baseline_15000_variance01~10` can be reduced by fixing the seed and camera ordering, and check whether the repeated runs satisfy the determinism acceptance criteria from `docs/experiment_plans/03-31_baseline_surface_rgb_determinism_2026.md`.

## Scope

- Dataset family: `replica_multi_roomwide_v2_384_surface_rgb_shared`
- Initialization: `from_scratch`
- Iterations: `15000`
- Target scenes from the plan: `room_0`, `office_0`
- Intended experiment configs:
  - `configs/experiments/gaussian_direct_surface_rgb_baseline_15000_deterministic_repeat1.yaml`
  - `configs/experiments/gaussian_direct_surface_rgb_baseline_15000_deterministic_repeat2.yaml`
  - `configs/experiments/gaussian_direct_surface_rgb_baseline_15000_deterministic_repeat3.yaml`

## Intended Configuration

All three configs request the same determinism settings:

- `seed: 42`
- `camera_order_seed: 42`
- `camera_shuffle_enabled: true`
- `deterministic: true`

The current codebase also supports these fields in both the backend wrapper and the command builder:

- `scripts/train_vanilla_3dgs_backend.py`
  - `resolve_determinism_settings(...)`
  - `apply_determinism_settings(...)`
  - parser flags `--seed`, `--camera-order-seed`, `--camera-shuffle`, `--deterministic`
- `src/priorprobe/optimization/vanilla_3dgs.py`
  - appends `--seed`
  - appends `--camera-order-seed`
  - appends `--camera-shuffle` or `--no-camera-shuffle`
  - appends `--deterministic` when requested

## What Actually Exists

### 1. `room_0` repeated runs exist for all three reps

The following canonical evaluation files exist:

- `outputs/gaussian_direct/experiments/03-31-baseline-rep1-15k-2026/room_0/evaluation.json`
- `outputs/gaussian_direct/experiments/03-31-baseline-rep2-15k-2026/room_0/evaluation.json`
- `outputs/gaussian_direct/experiments/03-31-baseline-rep3-15k-2026/room_0/evaluation.json`

All three corresponding `backend_run.json` files record:

- `seed = 42`
- `camera_order_seed = 42`
- `camera_shuffle_enabled = true`
- `deterministic = false`

Their recorded command lines include:

- `--seed 42`
- `--camera-order-seed 42`
- `--camera-shuffle`

and do **not** include `--deterministic`.

### 2. `office_0` is incomplete

Observed artifacts:

- `03-31-baseline-rep1-15k-2026/office_0/` contains `backend_run.json`, render logs, and metric logs
- `03-31-baseline-rep2-15k-2026/office_0/` does not exist
- `03-31-baseline-rep3-15k-2026/office_0/` does not exist

Important gaps:

- `03-31-baseline-rep1-15k-2026/office_0/evaluation.json` is missing
- `rep2` and `rep3` have no `office_0` result directory at all

Additional inconsistency:

- `rep1/office_0/backend_run.json` has no `determinism` block
- its command line also omits `--seed`, `--camera-order-seed`, and `--deterministic`
- `rep1/office_0/metrics_stdout.log` prints metrics for
  `outputs/gaussian_direct/backend_runs/surface_rgb_baseline_15000_repeat1/office_0`
  rather than
  `outputs/gaussian_direct/backend_runs/03-31-baseline-rep1-15k-2026/office_0`

Therefore the available `office_0` artifacts should be treated as non-canonical for the 03-31 determinism validation.

## Key Metrics

### Reference: 03-27 10-run baseline variance batch

From `docs/experiment_results/03-27_baseline_surface_rgb_variance10_2026.md`:

- `room_0`: PSNR mean `46.689600`, std `0.370861`, range `1.347790`
- `office_0`: PSNR mean `44.123923`, std `0.351150`, range `1.124893`

These are the comparison values for judging whether the 03-31 repeated runs materially reduced variance.

### `room_0` repeated results (seed 42 in metadata)

| run | final PSNR | final SSIM | final LPIPS | gaussian_count | total_time_sec |
|---|---:|---:|---:|---:|---:|
| `rep1` | `46.754322` | `0.992785` | `0.024007` | `207244` | `161.557285` |
| `rep2` | `46.912838` | `0.992842` | `0.023842` | `202064` | `160.399334` |
| `rep3` | `46.998913` | `0.992887` | `0.022964` | `200172` | `158.593322` |

Summary across the three canonical `room_0` repeats:

- PSNR mean: `46.888691`
- PSNR std: `0.101303`
- PSNR range: `0.244591`
- SSIM range: `0.000102`
- LPIPS range: `0.001043`
- Gaussian-count range: `7072`

### `office_0` partial metric output

The only observed metric printout is from
`outputs/gaussian_direct/experiments/03-31-baseline-rep1-15k-2026/office_0/metrics_stdout.log`.
Because no canonical `evaluation.json` exists and the log points to a different model path, these values are informative only and should not be used as the official 03-31 result.

The printed final metric in that log is:

- `ours_15000`: PSNR `43.6457977`, SSIM `0.9898403`, LPIPS `0.0265992`

## Interpretation

### 1. The 03-31 run only partially covers the plan

The plan required same-seed repeats for both `room_0` and `office_0`.
What exists is:

- complete canonical `room_0` results for `rep1`, `rep2`, `rep3`
- incomplete and internally inconsistent `office_0` artifacts

So the Phase 1 acceptance test from the plan is not complete.

### 2. Variance improved for `room_0`, but the run does not satisfy the plan threshold

Compared with the 03-27 10-run batch:

- PSNR std decreased from `0.370861` to `0.101303`
- PSNR range decreased from `1.347790` to `0.244591`

This is a meaningful reduction, but it still fails the plan's acceptance thresholds:

- strong pass required final PSNR difference `< 0.01 dB`
- weak pass required final PSNR difference `< 0.03 dB`

Observed `room_0` range is `0.244591 dB`, so the result does **not** pass even the weak threshold.

### 3. The report cannot claim that deterministic mode itself was validated

The configs explicitly requested `deterministic: true`, but the canonical `room_0` run metadata says `deterministic: false` and the recorded commands omit `--deterministic`.

Therefore the cleanest interpretation is:

- seed and camera-order metadata were propagated for the canonical `room_0` runs
- strict deterministic mode was **not** demonstrably exercised in those runs
- the observed improvement cannot be attributed to full deterministic execution

### 4. Artifact hygiene is not clean enough for a final determinism conclusion

The 03-31 artifact set contains:

- overwritten or backed-up `room_0` material under `rep1`
- partial `office_0` artifacts only in `rep1`
- missing canonical `evaluation.json` for `office_0`
- inconsistent `office_0` metric-log model paths

This means the current 03-31 batch is better treated as an intermediate check than a final determinism sign-off.

## Current Conclusion

- The baseline-determinism follow-up is **partially executed**.
- `room_0` shows reduced variance relative to the 03-27 10-run batch.
- The available `room_0` results do **not** satisfy the plan's pass threshold.
- `office_0` determinism was not completed in a canonical, reportable form.
- The artifact metadata contradicts the config intent on `deterministic: true`, so the run should not be reported as a successful deterministic validation.

## Next Actions

1. Re-run the same-seed repeat set for both `room_0` and `office_0` with a fresh output directory and no reused or backed-up artifacts mixed into the canonical path.
2. Verify that each resulting `backend_run.json` records:
   - `seed`
   - `camera_order_seed`
   - `camera_shuffle_enabled`
   - `deterministic: true`
3. Verify that each recorded command line actually includes `--deterministic`.
4. Require canonical `evaluation.json` outputs for both scenes before writing the final determinism verdict.
5. Only after the same-seed repeat passes the plan threshold should the follow-up seed sweep be used to redefine the baseline tolerance for prior-vs-baseline comparison.
