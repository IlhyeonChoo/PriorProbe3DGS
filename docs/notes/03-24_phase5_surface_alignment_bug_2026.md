# Replica Phase 5 Surface Alignment Bug

Date: 2026-03-24

## Summary

- Phase 5 `surface_rgb_*` prior 실험에서 **prior Gaussian이 target box와 다른 좌표계로 삽입되는 버그**를 확인했다.
- 이 문제는 `inspection` 시각화만의 문제가 아니라 실제 `iter_0 prior_points.ply`와 `aligned_prior_*.ply` 좌표에서도 재현된다.
- 따라서 아래 기존 Phase 5 결과는 **legacy / invalid qualitative prior-placement result**로 취급한다.

## Affected Results

다음 top-level 결과 디렉토리를 legacy로 이동했다.

- `outputs/gaussian_direct/backend_runs/legacy_bugged_surface_rgb_*`
- `outputs/gaussian_direct/experiments/legacy_bugged_surface_rgb_*`

이동 대상에는 다음 계열이 포함된다.

- `surface_rgb_baseline_*`
- `surface_rgb_prior_full_*`
- `surface_rgb_prior_100k*`
- `surface_rgb_prior_75k*`
- `surface_rgb_prior_50k*`
- `surface_rgb_prior_25k*`

## Root Cause

Phase 5 prior asset 준비 경로에서:

1. object-only surface RGB dataset으로 학습한 `point_cloud.ply`는 **scene/world frame**에 남아 있었고
2. `canonical_seed_floor.ply`는 그 asset으로부터 별도 계산된 **canonical seed frame**이었으며
3. `gaussian_direct` 삽입은 정렬 계산에는 canonical seed를 사용하고, 실제 삽입에는 원본 world-frame `splat.ply`를 사용했다.

즉, **정렬 기준 좌표계와 실제 삽입 Gaussian 좌표계가 달랐다.**

## Concrete Evidence

`room_0 / surface_rgb_prior_100k_15000`에서 확인한 대표 오차:

- `replica_room_0_obj_6`: target 대비 `2.58m`
- `replica_room_0_obj_9`: target 대비 `4.01m`
- `replica_room_0_obj_77`: target 대비 `4.80m`
- `replica_room_0_obj_74`: target 대비 `6.01m`

`office_0`도 같은 유형의 오차가 있으며 대략 `1.13m ~ 1.60m` 수준으로 확인됐다.

## Interpretation

- Phase 5 baseline run 자체는 prior 삽입이 없으므로 좌표계 버그의 직접 영향은 없다.
- 그러나 prior run과의 비교를 같은 batch로 해석하기 어렵기 때문에, 이번 정리에서는 baseline 포함 전체 `surface_rgb_*` 결과를 legacy로 묶어 후속 재실험과 분리했다.
- 기존 Phase 5 보고서와 CSV는 기록 보존용으로 남기되, **새 결론의 근거로 사용하지 않는다.**

## Next Step

- surface prior asset을 object-local canonical seed frame으로 다시 저장하도록 코드 수정
- 짧은 smoke run으로 `iter_0 prior placement`가 target 근처로 들어오는지 검증
- 검증 통과 후 Phase 5 실험을 새 clean run으로 재시작
