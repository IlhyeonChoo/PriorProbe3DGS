# Prior Position Sweep Collection Note

Date: 2026-04-05

관련 문서:
- `docs/experiment_plans/04-05_automated_prior_position_validation_plan_2026.md`
- `docs/notes/04-05_automated_prior_position_validator_v1_2026.md`
- `docs/notes/04-05_iter0_triplet_validation_room0_2026.md`

---

## Summary

사용자 요청에 따라 room_0의 roomcontained prior smoke를 기준으로 현재 판정 상태를 먼저 확인했고,
그 다음 각 prior object별로 위치를 조금씩 바꿔가며 validator label을 대량 수집했다.

진행 순서:
1. 현재 roomcontained prior smoke의 validator 결과 확인
2. 현재 기준으로 `FAIL/AMBIGUOUS`가 실제로 나온 상태를 유지한 채
3. 각 prior object별로 위치 perturbation sweep 수행
4. 각 object당 55개 variant, 총 220개 variant의 `PASS / FAIL / AMBIGUOUS`와 overlay/contact sheet를 저장

---

## 1. 현재 roomcontained prior smoke 상태

기준 run:
- `outputs/gaussian_direct/backend_runs/surface_rgb_roomcontained_prior_100k_geo_smoke_1000/room_0`

validator 결과:
- `obj_77`: `AMBIGUOUS`
- `obj_74`: `AMBIGUOUS`
- `obj_73`: `AMBIGUOUS`
- `obj_11`: `FAIL`

핵심 artifact:
- `outputs/gaussian_direct/reports/position_validation_surface_rgb_roomcontained_prior_100k_geo_smoke_1000_room0/summary.json`
- `outputs/gaussian_direct/reports/position_validation_surface_rgb_roomcontained_prior_100k_geo_smoke_1000_room0/contact_sheet.png`
- `outputs/gaussian_direct/reports/position_validation_surface_rgb_roomcontained_prior_100k_geo_smoke_1000_room0/overlays/`

즉, 사용자가 예상한 대로 현재 자동 판정은 clean `PASS`가 아니라 failure-side에 가깝다.

---

## 2. Sweep 방식

신규 스크립트:
- `scripts/collect_prior_position_sweep.py`

방식:
- base run의 aligned prior를 object별로 하나씩 가져온다
- local frame offset을 적용해 shifted aligned prior를 만든다
- optimization/training은 하지 않는다
- validator와 동일한 2D multi-view 기준으로 object별 판정을 다시 계산한다
- per-variant overlay/contact sheet와 summary를 저장한다

중요 제약:
- 이번 sweep은 "joint 4-object full scene optimization"이 아니라
  **object별 isolated prior position sweep**이다
- 목적은 validator의 `PASS / FAIL / AMBIGUOUS` 경계가 사람 눈 기준으로 납득 가능한지 확인할 수 있게 하는 것이다
- 즉 threshold calibration용 corpus로 본다

offset set:
- XY grid: `[-0.24, -0.16, -0.08, 0.0, 0.08, 0.16, 0.24] m`
- Z axis: `[-0.16, -0.08, -0.04, 0.04, 0.08, 0.16] m`
- 총 55 variants / object

총 수집량:
- 4 objects × 55 variants = 220 variants

---

## 3. Sweep output root

전체 root:
- `outputs/gaussian_direct/reports/prior_position_sweep_room0_full_2026`

집계 파일:
- `outputs/gaussian_direct/reports/prior_position_sweep_room0_full_2026/aggregate_summary.json`
- `outputs/gaussian_direct/reports/prior_position_sweep_room0_full_2026/aggregate_summary.csv`

object별 summary:
- `.../object_77/summary.json`
- `.../object_77/summary.csv`
- `.../object_74/summary.json`
- `.../object_74/summary.csv`
- `.../object_73/summary.json`
- `.../object_73/summary.csv`
- `.../object_11/summary.json`
- `.../object_11/summary.csv`

각 variant 디렉터리에는 다음이 있다.
- shifted `aligned_prior.ply`
- `summary.json`
- `contact_sheet.png`
- `overlays/*.png`

---

## 4. Decision count 요약

aggregate summary 기준:

- `obj_77`
  - PASS: `0`
  - FAIL: `18`
  - AMBIGUOUS: `37`
- `obj_74`
  - PASS: `24`
  - FAIL: `16`
  - AMBIGUOUS: `15`
- `obj_73`
  - PASS: `12`
  - FAIL: `34`
  - AMBIGUOUS: `9`
- `obj_11`
  - PASS: `7`
  - FAIL: `37`
  - AMBIGUOUS: `11`

관찰:
- sofa `obj_77`는 현재 sweep 범위 내에서 `PASS`가 하나도 나오지 않았다
- chair `obj_74`는 세 label이 모두 충분히 나왔다
- chair `obj_73`, table `obj_11`도 세 label이 모두 나왔지만 FAIL 비중이 높다

---

## 5. 기준점 주변 대표 variant

사람이 빠르게 판독하기 위한 대표 variant를 아래처럼 뽑을 수 있다.

### obj_77 sofa
- base에 가장 가까운 `AMBIGUOUS`
  - `object_77/v024_dx+0p00_dy+0p00_dz+0p00`
- 가장 가까운 `FAIL`
  - `object_77/v016_dx-0p08_dy-0p08_dz+0p00`
- PASS는 없음

### obj_74 chair
- base에 가장 가까운 `AMBIGUOUS`
  - `object_74/v024_dx+0p00_dy+0p00_dz+0p00`
- 가장 가까운 `PASS`
  - `object_74/v025_dx+0p00_dy+0p08_dz+0p00`
- 가장 가까운 `FAIL`
  - `object_74/v022_dx+0p00_dy-0p16_dz+0p00`

### obj_73 chair
- base에 가장 가까운 `FAIL`
  - `object_73/v024_dx+0p00_dy+0p00_dz+0p00`
- 가장 가까운 `AMBIGUOUS`
  - `object_73/v025_dx+0p00_dy+0p08_dz+0p00`
- 가장 가까운 `PASS`
  - `object_73/v026_dx+0p00_dy+0p16_dz+0p00`

### obj_11 table
- base에 가장 가까운 `FAIL`
  - `object_11/v024_dx+0p00_dy+0p00_dz+0p00`
- 가장 가까운 `AMBIGUOUS`
  - `object_11/v025_dx+0p00_dy+0p08_dz+0p00`
- 가장 가까운 `PASS`
  - `object_11/v026_dx+0p00_dy+0p16_dz+0p00`

이 세트만 먼저 보면 label 경계가 사람 눈에도 맞는지 빠르게 볼 수 있다.

---

## 6. 현재 단계 해석

여기까지는 threshold를 고정한 것이 아니라,
**사용자가 직접 판독해서 PASS / FAIL / AMBIGUOUS 기준이 맞는지 확인할 수 있도록 calibration corpus를 구축한 단계**다.

중요 포인트:
- object별로 최소 55개 variant를 확보했으므로 "각 prior마다 50개 이상" 요구는 충족했다
- 현재 validator가 내린 label과 실제 시각적 타당성이 얼마나 맞는지 이제 사용자 검토가 가능하다
- 사용자 판독 결과를 받은 뒤에
  - threshold 수정
  - ambiguous band 조정
  - 필요 시 metric 조합 수정
을 진행하면 된다

---

## 7. 다음 권장 액션

1. 우선 아래 대표 variant부터 빠르게 확인
   - `object_74/v024`, `v025`, `v022`
   - `object_73/v024`, `v025`, `v026`
   - `object_11/v024`, `v025`, `v026`
   - `object_77/v024`, `v016`
2. 그 다음 필요하면 object별 전체 55 variants를 훑으며 label 경계 확인
3. 사용자가 label이 맞는지 피드백하면
   - threshold calibration note 작성
   - validator decision rule patch
   - 이후 smoke gate 통합 또는 다음 실험 단계 진행
