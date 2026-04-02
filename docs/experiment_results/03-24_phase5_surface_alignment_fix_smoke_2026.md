# Replica Phase 5 Surface Alignment Fix Smoke

Date: 2026-03-24

## Summary

- 기존 Phase 5 surface prior 결과는 `legacy_bugged_surface_rgb_*`로 이동했다.
- 원인은 **surface prior Gaussian asset이 canonical seed frame이 아니라 world/object-training frame으로 저장된 상태에서 direct insertion에 사용된 것**이었다.
- 버그 수정 후 `room_0` 전용 fixed prior library를 다시 만들고 `100K / 1000 iter` smoke를 재실행했다.

## Fixed Asset

- Fixed prior stage root:
  - `outputs/gaussian_direct/prior_library/replica_target_surface_exact_trained_clip_fixed_room0_smoke`
- Fixed prior config:
  - `outputs/gaussian_direct/prior_library/replica_target_surface_exact_trained_clip_fixed_room0_smoke.yaml`
- Fixed prep report:
  - `docs/notes/03-24_phase5_surface_prep_fixed_room0_smoke_2026.md`

## Validation Run

- Experiment:
  - `surface_rgb_prior_100k_smoke_1000`
- Scene:
  - `room_0`
- Result directory:
  - `outputs/gaussian_direct/backend_runs/surface_rgb_prior_100k_smoke_1000/room_0`

## Alignment Error Before vs After

### Before fix

`room_0 / prior_100k / 15000` 기준 target center 대비 `aligned_prior` 중심 오차:

- `obj_6`: `2.58 m`
- `obj_9`: `4.01 m`
- `obj_77`: `4.80 m`
- `obj_74`: `6.01 m`

### After fix

`room_0 / prior_100k / smoke_1000` 기준 target center 대비 `aligned_prior` 중심 오차:

- `obj_6`: `0.0031 m`
- `obj_9`: `0.0448 m`
- `obj_77`: `0.0047 m`
- `obj_74`: `0.0120 m`

## Smoke Metrics

- iter 0:
  - PSNR `11.4914`
  - SSIM `0.5497`
  - LPIPS `0.5814`
  - Gaussians `200000`
- iter 500:
  - PSNR `32.2826`
- iter 1000:
  - PSNR `38.8822`
  - Gaussians `245297`

## Interpretation

- 버그 수정 후 prior placement는 더 이상 방 바깥으로 수 미터씩 밀리지 않는다.
- 현재 smoke 기준으로는 **실제 direct Gaussian insertion 좌표계가 정상화되었다고 봐도 된다.**
- 다음 단계는 fixed surface prior library를 `room_0`, `office_0` 전체에 대해 다시 만들고, Phase 5 실험을 clean run으로 재시작하는 것이다.
