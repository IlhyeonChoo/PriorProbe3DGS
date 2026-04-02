# Replica Gaussian-Direct Prior Protection (`room_0`)

Date: 2026-03-20

## Setup

- Scene: `room_0`
- Dataset: `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_diverse_384`
- Views: `320 train + 64 test = 384`
- Prior condition: `same_scene_exact`
- Insertion: `gaussian_direct`
- Alignment: `oracle_target_box`
- Target PSNR threshold: `10.628532`
  - derived from `gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_diverse_384_15000` at iteration `3000`

## Configs

- Baseline: `configs/experiments/gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_diverse_384_15000.yaml`
- Unprotected exact prior: `configs/experiments/gaussian_direct_same_scene_exact_clip_diverse_384_15000.yaml`
- Freeze prior: `configs/experiments/gaussian_direct_same_scene_exact_clip_diverse_384_freeze_15000.yaml`
- Weak prior: `configs/experiments/gaussian_direct_same_scene_exact_clip_diverse_384_weak_15000.yaml`

## Smoke Sanity (`1000 iter`)

두 보호 모드는 먼저 `room_0`에서 1000-iter smoke로 검증했다. 둘 다 `prior_protection.json`이 정상 생성됐고, 삽입된 prior Gaussian `100000개`가 iteration `1000`까지 그대로 유지됐다.

| mode | lr_scale | protected @0 | protected @1000 | total @1000 | psnr @1000 | total_time_sec |
|---|---:|---:|---:|---:|---:|---:|
| freeze | 0.00 | 100000 | 100000 | 249926 | 9.526825 | 49.919779 |
| weak | 0.02 | 100000 | 100000 | 250397 | 9.823987 | 49.798925 |

## Full Results (`15000 iter`, sequential wall-clock)

| experiment | protection | time_to_target_sec | total_time_sec | psnr @3000 | psnr @15000 | ssim @15000 | lpips @15000 | gaussians @0 | gaussians @3000 | gaussians @15000 | protected @3000 | protected @15000 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline_dense | none | 118.847082 | 594.235408 | 10.628532 | 12.487882 | 0.545952 | 0.335978 | 100000 | 1152886 | 3916981 | n/a | n/a |
| unprotected_exact | none | 124.032383 | 620.161913 | 10.708377 | 12.435008 | 0.538036 | 0.349264 | 200000 | 1291896 | 4042500 | n/a | n/a |
| freeze | freeze | 183.707660 | 551.122980 | 10.281592 | 11.858848 | 0.484434 | 0.395414 | 200000 | 1097890 | 3414144 | 100000 | 100000 |
| weak | weak (`lr_scale=0.02`) | 112.027473 | 560.137367 | 10.634333 | 12.374944 | 0.529553 | 0.352036 | 200000 | 1136436 | 3549813 | 100000 | 100000 |

## Key Findings

- Dense diverse view만 늘린 기존 `unprotected_exact`는 `room_0`에서 여전히 baseline보다 느렸다.
  - `124.03s` vs baseline `118.85s`
- `freeze`는 삽입된 prior Gaussian을 끝까지 완전히 보존했지만, convergence를 크게 해쳤다.
  - target PSNR 도달이 `183.71s`까지 밀렸고, 최종 PSNR도 `11.8588`로 가장 낮았다.
- `weak`는 삽입된 prior Gaussian `100000개`를 끝까지 유지하면서도 `time-to-target`을 baseline보다 앞당겼다.
  - `112.03s` vs baseline `118.85s`
  - `112.03s` vs unprotected exact `124.03s`
- 다만 `weak`의 최종 품질은 baseline과 unprotected exact보다 약간 낮았다.
  - `12.3749` vs baseline `12.4879`
  - `12.3749` vs unprotected exact `12.4350`

## Interpretation

- `room_0`에서는 단순히 view diversity만 늘리는 것으로는 prior 파괴 문제를 해결하지 못했다.
- prior를 완전히 고정하는 것은 너무 강해서, exact prior라도 최적화 적응 여지를 막아버린다.
- 반면 `weak` protection은 pruned/densified되지 않도록 prior를 보존하면서도, 낮은 learning rate로 미세 조정은 허용해 `time-to-target` 개선을 만들었다.
- 따라서 현재 기준으로는 `freeze`가 아니라 `weak + prune/densify protection`이 다음 sweep의 출발점이다.

## Recorded Artifacts

- `freeze` final protection snapshot:
  - `outputs/gaussian_direct/backend_runs/gaussian_direct_same_scene_exact_clip_diverse_384_freeze_15000/room_0/point_cloud/iteration_15000/prior_protection.json`
- `weak` final protection snapshot:
  - `outputs/gaussian_direct/backend_runs/gaussian_direct_same_scene_exact_clip_diverse_384_weak_15000/room_0/point_cloud/iteration_15000/prior_protection.json`
- Both runs record the four protected prior ranges explicitly.
  - `replica_room_0_obj_6`
  - `replica_room_0_obj_9`
  - `replica_room_0_obj_77`
  - `replica_room_0_obj_74`

## Next Step

- Keep `protect_prior_from_prune=true` and `protect_prior_from_densify=true`
- Sweep `prior_lr_scale` around the current working point
  - `0.01`
  - `0.02`
  - `0.05`
- Re-run the same protection sweep on `office_0`
