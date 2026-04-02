# Replica Gaussian-Direct Surface RGB Baseline Variance (2026-03-27)

## Purpose

`surface_rgb` 15K baseline을 최근 여러 번 반복 실행한 결과를 모아서 run-to-run 분산 범위를 확인한다.

## Scope

- Dataset family: `replica_multi_roomwide_v2_384_surface_rgb`
- Initialization: `from_scratch`
- Iterations: `15000`
- Runs inspected:
  - `legacy_bugged_surface_rgb_baseline_15000`
  - `surface_rgb_baseline_15000`
  - `surface_rgb_baseline_15000_fixscale`
  - `surface_rgb_baseline_15000_repeat1`

`surface_rgb_baseline_15000_repeat1`은 `room_0`만 완료됐고 `office_0`는 없다.

## Same-Condition Check

- 모든 run의 `source_path`는 scene별로 동일하다.
  - `room_0`: `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_v2_384_surface_rgb/room_0`
  - `office_0`: `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_v2_384_surface_rgb/office_0`
- `fixscale` 변경은 prior insertion 경로용 수정이므로 baseline code path 자체는 같다.

## Broad Variance

### room_0 (n=4)

- PSNR: mean `46.6489`, std `0.3317`, range `0.8088`
- SSIM: mean `0.992775`, std `0.000079`, range `0.000186`
- LPIPS: mean `0.023323`, std `0.000378`, range `0.000860`
- Total time: mean `161.2947s`, std `1.3797s`, range `2.4925s`

### office_0 (n=3)

- PSNR: mean `44.1526`, std `0.3940`, range `0.7836`
- SSIM: mean `0.989143`, std `0.000838`, range `0.001671`
- LPIPS: mean `0.028502`, std `0.001355`, range `0.002702`
- Total time: mean `160.6858s`, std `2.1401s`, range `4.2653s`

## Current-Only Variance

`legacy_bugged_surface_rgb_baseline_15000`를 제외한 값.

### room_0 (n=3)

- PSNR: mean `46.6380`, std `0.4053`, range `0.8088`
- SSIM: mean `0.992746`, std `0.000064`, range `0.000129`
- LPIPS: mean `0.023254`, std `0.000430`, range `0.000860`
- Total time: mean `161.7021s`, std `1.3636s`, range `2.4351s`

### office_0 (n=2)

- PSNR: mean `44.3605`, std `0.2262`, range `0.3198`
- SSIM: mean `0.989105`, std `0.001182`, range `0.001671`
- LPIPS: mean `0.028442`, std `0.001910`, range `0.002702`
- Total time: mean `161.8036s`, std `1.2899s`, range `1.8242s`

## Per-Run Values

### room_0

- `legacy_bugged_surface_rgb_baseline_15000`: PSNR `46.6816`, SSIM `0.992864`, LPIPS `0.023533`, time `160.0726s`
- `surface_rgb_baseline_15000`: PSNR `46.6062`, SSIM `0.992678`, LPIPS `0.022831`, time `162.5651s`
- `surface_rgb_baseline_15000_fixscale`: PSNR `46.2495`, SSIM `0.992752`, LPIPS `0.023691`, time `162.4112s`
- `surface_rgb_baseline_15000_repeat1`: PSNR `47.0583`, SSIM `0.992807`, LPIPS `0.023238`, time `160.1300s`

### office_0

- `legacy_bugged_surface_rgb_baseline_15000`: PSNR `43.7367`, SSIM `0.989220`, LPIPS `0.028623`, time `158.4504s`
- `surface_rgb_baseline_15000`: PSNR `44.2005`, SSIM `0.988269`, LPIPS `0.029793`, time `162.7157s`
- `surface_rgb_baseline_15000_fixscale`: PSNR `44.5204`, SSIM `0.989940`, LPIPS `0.027091`, time `160.8914s`

## Takeaway

- 현재 확보된 반복 run 기준으로 baseline 15K는 scene별 최종 PSNR이 대략 `0.3 ~ 0.4 dB` 수준의 표준편차를 가질 수 있다.
- `room_0`는 현재 3~4회 범위에서 PSNR 변동폭이 `0.81 dB`까지 나온다.
- `office_0`는 표본 수가 아직 적지만 현재 범위에서는 `0.32 ~ 0.78 dB` 정도다.
- 따라서 Phase 5 prior 조건 비교에서 `0.05 ~ 0.1 dB` 수준의 차이는 baseline 분산 안에 묻힐 가능성이 있다.
