# Prior Position Fine Sweep Room0 100-each Note

Date: 2026-04-05

관련 문서:
- `docs/notes/04-05_prior_position_sweep_room0_v2_2026.md`
- `docs/experiment_plans/04-05_automated_prior_position_validation_plan_2026.md`

---

## Summary

사용자가 지정한 PASS anchor variant를 기준으로 room_0 각 object에 대해 100개씩 미세 위치 perturbation sweep을 수행했다.

anchor 기준:
- `obj_11`
  - `v020_dx-0p08_dy+0p24_dz+0p00`
  - `v027_dx+0p00_dy+0p24_dz+0p00`
- `obj_73`
  - `v020_dx-0p08_dy+0p24_dz+0p00`
  - `v027_dx+0p00_dy+0p24_dz+0p00`
- `obj_74`
  - `v020_dx-0p08_dy+0p24_dz+0p00`
  - `v027_dx+0p00_dy+0p24_dz+0p00`
  - `v034_dx+0p08_dy+0p24_dz+0p00`
- `obj_77`
  - `v050_dx+0p00_dy+0p00_dz-0p08`

수집량:
- object당 100 variants
- 총 400 variants
- 각 variant는 16 views, 4x4 edge-only contact sheet 포함

---

## 구현

신규 스크립트:
- `scripts/collect_prior_position_fine_sweep.py`

관련 테스트:
- `tests/test_collect_prior_position_fine_sweep.py`

추가 반영:
- fine sweep script는 coarse sweep summary에서 anchor variant의 local offset을 읽는다
- object별 anchor 개수에 따라 `100`개를 균등 분배한다
  - 2 anchors -> `50 + 50`
  - 3 anchors -> `34 + 33 + 33`
  - 1 anchor -> `100`
- 미세 delta 후보:
  - XY: `[-0.06, -0.045, -0.03, -0.015, 0.0, 0.015, 0.03, 0.045, 0.06] m`
  - Z: `[-0.03, -0.015, 0.0, 0.015, 0.03] m`
- 각 variant에 대해
  - `aligned_prior.ply`
  - 16-view edge-only contact sheet
  - decision bucket copy
  - csv/json summary
를 기록한다

테스트:
- `uv run pytest -q tests/test_collect_prior_position_fine_sweep.py tests/test_collect_prior_position_sweep.py tests/test_prior_position_validator.py`
- 결과: `11 passed`

smoke:
- `obj_11`만 `6 variants`로 smoke 실행 후 정상 완료 확인

---

## Output root

- `outputs/gaussian_direct/reports/prior_position_fine_sweep_room0_100each_2026`

주요 파일:
- `aggregate_summary.json`
- `aggregate_summary.csv`
- `by_decision/PASS/`
- `by_decision/FAIL/`
- `by_decision/AMBIGUOUS/`
- `object_11/summary.json`
- `object_73/summary.json`
- `object_74/summary.json`
- `object_77/summary.json`

---

## 결과 요약

aggregate summary 기준:

- `obj_11`
  - PASS: `100`
  - FAIL: `0`
  - AMBIGUOUS: `0`
- `obj_73`
  - PASS: `100`
  - FAIL: `0`
  - AMBIGUOUS: `0`
- `obj_74`
  - PASS: `100`
  - FAIL: `0`
  - AMBIGUOUS: `0`
- `obj_77`
  - PASS: `0`
  - FAIL: `0`
  - AMBIGUOUS: `100`

해석:
- 사용자가 지정한 PASS anchor 주변의 fine neighborhood에서는
  - `obj_11`, `obj_73`, `obj_74`는 현재 validator 기준으로 전부 PASS로 유지된다
- 반면 `obj_77`은 사용자가 PASS anchor로 지정한 `v050` 주변 fine neighborhood 전체가 아직 AMBIGUOUS다

즉, 현재 validator는
- 11/73/74에 대해서는 사용자가 지정한 PASS 영역을 강하게 PASS로 유지하고
- 77에 대해서는 사용자가 PASS로 보고 싶은 영역을 아직 PASS로 올리지 못한다

---

## 리뷰 시작점

### PASS bucket
- `outputs/gaussian_direct/reports/prior_position_fine_sweep_room0_100each_2026/by_decision/PASS/`

### AMBIGUOUS bucket
- `outputs/gaussian_direct/reports/prior_position_fine_sweep_room0_100each_2026/by_decision/AMBIGUOUS/`

특히 확인 우선순위:
1. `obj_11`, `obj_73`, `obj_74`의 PASS 사례가 정말 PASS처럼 보이는지
2. `obj_77`의 AMBIGUOUS 사례가 사용자의 눈에는 PASS인지

`obj_77` review 예시:
- `by_decision/AMBIGUOUS/obj_77_v050_f000_dx+0p000_dy+0p000_dz-0p080.png`

---

## Next recommended action

1. 먼저 `by_decision/PASS/`와 `by_decision/AMBIGUOUS/obj_77_*`를 직접 검토
2. 사용자가 `obj_77`의 어느 사례까지 PASS로 볼지 정해주면
3. 그 기준으로 threshold 또는 ambiguous band를 patch
4. 그 뒤 validator decision policy를 고정
