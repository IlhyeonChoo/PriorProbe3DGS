# Replica Multi-Object Mean_RGB Align-Fix (2026-03-19)

## Goal

기존 `multi-object + mean_rgb + merge-init` 결과에, CLIP align-fix에서 검증한 새 정렬 경로를 그대로 적용했다.

- canonical seed point cloud 사용
- anisotropic scale 사용
- floor anchor / floor snap 사용
- 4-way yaw search 사용
- `v2`에서만 `skip_on_bad_alignment=true`

이번 라운드는 retrieval feature를 바꾸지 않고, **mean_rgb retrieval 그대로 유지한 채 정렬만 바꾼 실험**이다.

## Selected Priors

### office_0

- target `9` -> `sofa_0003`
- target `7` -> `sofa_0050`
- target `58` -> `table_0020`
- target `61` -> `chair_0240`

### room_0

- target `6` -> `lamp_0019`
- target `9` -> `sofa_0003`
- target `77` -> `sofa_0003`
- target `74` -> `chair_0201`

`v1`과 `v2`의 retrieval 결과는 같고, 차이는 bad alignment를 drop하느냐뿐이다.

## Results

Time-to-target는 각 scene의 `baseline multi 15000`에서 `3000 iter` PSNR을 target으로 다시 계산했다.

### office_0

| experiment | PSNR | SSIM | LPIPS | time-to-target (s) | total time (s) |
|---|---:|---:|---:|---:|---:|
| baseline multi 15000 | `13.2911` | `0.5942` | `0.3393` | `89.6877` | `448.4384` |
| mean_rgb multi 15000 | `13.2855` | `0.5934` | `0.3407` | `91.7422` | `458.7112` |
| mean_rgb alignfix v1 15000 | `13.3468` | `0.6041` | `0.3296` | `93.4313` | `467.1564` |
| mean_rgb alignfix v2 15000 | `13.3478` | `0.6021` | `0.3329` | `92.8324` | `464.1618` |

해석:

- old mean_rgb 대비 align-fix가 final quality를 분명히 올렸다.
- `v1`과 `v2`의 차이는 매우 작다.
- baseline을 speed로 이기지는 못했지만, old mean_rgb보다 결과가 더 안정적이다.

### room_0

| experiment | PSNR | SSIM | LPIPS | time-to-target (s) | total time (s) |
|---|---:|---:|---:|---:|---:|
| baseline multi 15000 | `13.6677` | `0.6604` | `0.2802` | `84.4107` | `422.0537` |
| mean_rgb multi 15000 | `13.6662` | `0.6629` | `0.2770` | `86.6250` | `433.1251` |
| mean_rgb alignfix v1 15000 | `13.6907` | `0.6660` | `0.2771` | `87.5541` | `437.7703` |
| mean_rgb alignfix v2 15000 | `13.6743` | `0.6605` | `0.2803` | `86.6974` | `433.4869` |

해석:

- `room_0`에서도 `v1`은 old mean_rgb보다 final PSNR/SSIM이 좋아졌다.
- `v2`는 speed는 old mean_rgb와 비슷하지만, quality는 `v1`보다 약했다.
- 따라서 `room_0` 기준으로도 기본 추천은 `v1`이다.

## Dropped Priors

`office_0`에서는 `v1`, `v2` 모두 dropped prior가 없었다.

`room_0 v2`에서는 두 prior가 drop됐다.

- target `6` -> `lamp_0019`, reason=`all_candidates_rejected`
- target `9` -> `sofa_0003`, reason=`all_candidates_rejected`

즉 mean_rgb도 CLIP과 같은 방향으로, `v2`의 hard skip이 항상 이득을 주지 않았다.

## Viewer

### office_0

- old mean_rgb: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_mean_rgb_15000/office_0/inspection/viewer.html`
- alignfix v1: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_mean_rgb_alignfix_v1_15000/office_0/inspection/viewer.html`
- alignfix v2: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_mean_rgb_alignfix_v2_15000/office_0/inspection/viewer.html`

### room_0

- old mean_rgb: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_mean_rgb_15000/room_0/inspection/viewer.html`
- alignfix v1: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_mean_rgb_alignfix_v1_15000/room_0/inspection/viewer.html`
- alignfix v2: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_mean_rgb_alignfix_v2_15000/room_0/inspection/viewer.html`

## Comparison to CLIP Align-Fix

`alignfix v1` 기준으로 보면 mean_rgb는 CLIP보다 final PSNR이 약간 낮지만, 매우 큰 차이는 아니었다.

- `office_0`
  - mean_rgb alignfix v1: `13.3468`
  - CLIP alignfix v1: `13.3746`
- `room_0`
  - mean_rgb alignfix v1: `13.6907`
  - CLIP alignfix v1: `13.7004`

즉 현재 Replica 설정에서는 **정렬 개선 효과가 retrieval backend 차이보다 더 크게 보이는 구간이 있다**고 해석할 수 있다.

## Recommendation

mean_rgb branch를 계속 유지할 거라면 기본 추천은 `oracle_prior_vanilla_3dgs_multi_mean_rgb_alignfix_v1_15000`이다.

이유:

- 두 scene 모두 old mean_rgb보다 quality가 개선됐다.
- `v2`는 뚜렷한 추가 이득이 없고, `room_0`에서는 hard skip으로 prior를 떨어뜨렸다.
- 따라서 다음 기본 branch는 `mean_rgb + alignfix v1`로 두고, `v2`는 threshold 실험용 보조 branch로 유지하는 게 맞다.
