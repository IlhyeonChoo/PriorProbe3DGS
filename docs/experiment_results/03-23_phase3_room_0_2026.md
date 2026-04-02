# Replica Gaussian-Direct Phase 3

- Date: 2026-03-23
- Scene: `room_0`
- Dataset family: `roomwide_v2_384`
- 비교 기준: baseline / prior 100K current / A 25K current / Phase 3 세 조건
- 주 지표: `iter_0`, `iter_3000`, `iter_15000` PSNR/SSIM/LPIPS, prior 생존량, total gaussian count
- 참고: `time_to_target_sec`는 표에는 남기되 판단의 주 근거로 쓰지 않음

## Summary

| label | group | lr_scale | prune_protect | densify_protect | iter_0_psnr | iter_3000_psnr | iter_15000_psnr | gaussians@0 | gaussians@3000 | gaussians@15000 | prior@0 | prior@3000 | prior@15000 |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | reference | 0.05 | True | True | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| prior 100K current | reference | 0.05 | True | True | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| A 25K current | reference | 0.05 | True | True | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| lr_0.1 | phase3 | 0.10 | True | True | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| lr_1.0 | phase3 | 1.00 | True | True | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| full_none | phase3 | 1.00 | False | False | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Phase 3 Focus

| label | final vs A25K | iter_3000 vs A25K | final vs baseline | prior_survival@3000 | prior_survival@15000 | prior_densified@3000 | prior_densified@15000 | total_time_sec | time_to_target_sec |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| lr_0.1 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 715.443237 | n/a |
| lr_1.0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 712.491813 | n/a |
| full_none | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 707.578849 | n/a |

## Interpretation Hints

- 현재 기준 비교점 `A 25K current`: iter_0 `n/a`, iter_3000 `n/a`, final `n/a`
- `lr_1.0` final vs A25K: `n/a` -> `insufficient data`
- `lr_0.1` final vs A25K: `n/a` -> `insufficient data`
- `full_none` final vs A25K: `n/a` -> `insufficient data`
- `full_none` prior@15000: `n/a` / kept `25000`
- `full_none` densified@15000: `n/a`
