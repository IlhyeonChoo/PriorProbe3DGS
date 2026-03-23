# Replica Gaussian-Direct Phase 3

- Date: 2026-03-22
- Scene: `room_0`
- Dataset family: `roomwide_v2_384`
- 비교 기준: baseline / prior 100K current / A 25K current / Phase 3 세 조건
- 주 지표: `iter_0`, `iter_3000`, `iter_15000` PSNR/SSIM/LPIPS, prior 생존량, total gaussian count
- 참고: `time_to_target_sec`는 표에는 남기되 판단의 주 근거로 쓰지 않음

## Summary

| label | group | lr_scale | prune_protect | densify_protect | iter_0_psnr | iter_3000_psnr | iter_15000_psnr | gaussians@0 | gaussians@3000 | gaussians@15000 | prior@0 | prior@3000 | prior@15000 |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | reference | 0.05 | True | True | 8.142289 | 10.324856 | 12.233681 | 100000 | 1098647 | 4569461 | n/a | n/a | n/a |
| prior 100K current | reference | 0.05 | True | True | 8.011765 | 10.486682 | 12.270486 | 200000 | 1218554 | 4568764 | 100000 | 94809 | 64287 |
| A 25K current | reference | 0.05 | True | True | 8.099512 | 10.560642 | 12.289521 | 125000 | 1183260 | 4667135 | 25000 | 24396 | 18143 |
| lr_0.1 | phase3 | 0.10 | True | True | 8.098713 | 10.558125 | 12.238309 | 125000 | 1178333 | 4645032 | 25000 | 24525 | 18358 |
| lr_1.0 | phase3 | 1.00 | True | True | 8.099193 | 10.527694 | 12.245140 | 125000 | 1172936 | 4656003 | 25000 | 24496 | 18421 |
| full_none | phase3 | 1.00 | False | False | 8.099988 | 10.570299 | 12.269149 | 125000 | 1164741 | 4639582 | 25000 | 24480 | 18380 |

## Phase 3 Focus

| label | final vs A25K | iter_3000 vs A25K | final vs baseline | prior_survival@3000 | prior_survival@15000 | prior_densified@3000 | prior_densified@15000 | total_time_sec | time_to_target_sec |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| lr_0.1 | -0.051212 | -0.002517 | +0.004628 | 0.981000 | 0.734320 | -475 | -6642 | 715.443237 | 143.088647 |
| lr_1.0 | -0.044381 | -0.032948 | +0.011459 | 0.979840 | 0.736840 | -504 | -6579 | 712.491813 | 142.498363 |
| full_none | -0.020372 | +0.009657 | +0.035468 | 0.979200 | 0.735200 | -520 | -6620 | 707.578849 | 141.515770 |

## Interpretation Hints

- 현재 기준 비교점 `A 25K current`: iter_0 `8.099512`, iter_3000 `10.560642`, final `12.289521`
- `lr_1.0` final vs A25K: `-0.044381` -> `lower`
- `lr_0.1` final vs A25K: `-0.051212` -> `lower`
- `full_none` final vs A25K: `-0.020372` -> `lower`
- `full_none` prior@15000: `18380` / kept `25000`
- `full_none` densified@15000: `-6620`
