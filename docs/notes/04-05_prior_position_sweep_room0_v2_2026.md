# Prior Position Sweep Collection Note v2

Date: 2026-04-05

관련 문서:
- `docs/experiment_plans/04-05_automated_prior_position_validation_plan_2026.md`
- `docs/notes/04-05_prior_position_sweep_room0_2026.md`
- `docs/notes/04-05_automated_prior_position_validator_v1_2026.md`

---

## Summary

사용자 피드백을 반영해 room_0 prior position sweep corpus를 다시 만들었다.

이번 v2에서 반영한 핵심 수정:
1. view 수를 `4`장에서 `8`장으로 늘림
2. view 선택을 metric 상위 편향이 아니라 **test view 전역에서 균등 샘플링**으로 변경
3. 비교 이미지의 오른쪽 패널을 **원본 이미지 edge + GT edge + prior edge** 구조로 변경
4. `PASS / FAIL / AMBIGUOUS` decision bucket 폴더를 별도로 만들고 각 variant의 contact sheet png를 복사

즉, 이번 v2 output은 사용자가 label 경계를 직접 판독하기 위한 리뷰용 corpus다.
기존 v1 sweep output은 reference로 남기되, 수동 판독은 v2 기준으로 보는 것이 맞다.

---

## 왜 v1을 다시 만들었는가

사용자 지적 사항:
- 4 views는 너무 적고 특정 방향에 치우쳐 있었다
- raw RGB 위 prior edge만 올리면 사람이 판별하기 불편했다
- decision bucket이 없어서 PASS/FAIL/AMBIGUOUS 사례를 빠르게 비교하기 어려웠다

원인:
- v1 sweep script가 contact sheet view를 centroid error 큰 view 위주로 뽑아 direction diversity를 잃었음
- overlay가 raw RGB 위 contour라 원본 edge 대비 위치 판단이 불편했음
- variant별 산출물은 있었지만 decision bucket browse 구조가 없었음

영향:
- calibration corpus 자체는 있었지만 사람이 PASS/FAIL/AMBIGUOUS 경계를 빠르게 판독하기 어려웠음

---

## v2 구현 반영 내용

수정 파일:
- `scripts/collect_prior_position_sweep.py`
- `tests/test_collect_prior_position_sweep.py`

구현 변경:
1. `max_contact_views` 기본값을 `8`로 상향
2. valid view 중 centroid worst-first가 아니라 정렬된 test view 전역에서 evenly spaced selection 사용
3. 각 view comparison png를 다음 구조로 생성
   - left: original RGB
   - right: image edges + GT(green) + prior(red)
4. top-level decision bucket 생성
   - `.../by_decision/PASS/`
   - `.../by_decision/FAIL/`
   - `.../by_decision/AMBIGUOUS/`
5. 각 variant contact sheet를 해당 bucket에 복사
   - 예: `by_decision/PASS/obj_11_v026_...png`

테스트:
- `uv run pytest -q tests/test_collect_prior_position_sweep.py tests/test_prior_position_validator.py tests/test_build_initial_snapshot_viewer.py tests/test_replica_surface.py`
- 결과: `16 passed`

---

## v2 output root

새 review root:
- `outputs/gaussian_direct/reports/prior_position_sweep_room0_full_v2_2026`

집계 파일:
- `outputs/gaussian_direct/reports/prior_position_sweep_room0_full_v2_2026/aggregate_summary.json`
- `outputs/gaussian_direct/reports/prior_position_sweep_room0_full_v2_2026/aggregate_summary.csv`

decision bucket:
- `outputs/gaussian_direct/reports/prior_position_sweep_room0_full_v2_2026/by_decision/PASS/`
- `outputs/gaussian_direct/reports/prior_position_sweep_room0_full_v2_2026/by_decision/FAIL/`
- `outputs/gaussian_direct/reports/prior_position_sweep_room0_full_v2_2026/by_decision/AMBIGUOUS/`

object별 summary:
- `.../object_77/summary.json`
- `.../object_74/summary.json`
- `.../object_73/summary.json`
- `.../object_11/summary.json`

각 variant 내부:
- `aligned_prior.ply`
- `summary.json`
- `contact_sheet.png`
- `comparisons/*.png`

---

## 수집량

수집량은 유지:
- object당 55 variants
- 총 220 variants

label count도 동일:
- `obj_77`: PASS 0 / FAIL 18 / AMBIGUOUS 37
- `obj_74`: PASS 24 / FAIL 16 / AMBIGUOUS 15
- `obj_73`: PASS 12 / FAIL 34 / AMBIGUOUS 9
- `obj_11`: PASS 7 / FAIL 37 / AMBIGUOUS 11

즉 달라진 것은 판정 분포가 아니라 **리뷰 가능성**이다.

---

## 바로 보기 좋은 경로

### PASS 사례 폴더
- `outputs/gaussian_direct/reports/prior_position_sweep_room0_full_v2_2026/by_decision/PASS/`

### FAIL 사례 폴더
- `outputs/gaussian_direct/reports/prior_position_sweep_room0_full_v2_2026/by_decision/FAIL/`

### AMBIGUOUS 사례 폴더
- `outputs/gaussian_direct/reports/prior_position_sweep_room0_full_v2_2026/by_decision/AMBIGUOUS/`

### 예시
- table PASS 예시
  - `.../by_decision/PASS/obj_11_v026_dx+0p00_dy+0p16_dz+0p00.png`
- table FAIL 예시
  - `.../by_decision/FAIL/obj_11_v024_dx+0p00_dy+0p00_dz+0p00.png`
- table AMBIGUOUS 예시
  - `.../by_decision/AMBIGUOUS/obj_11_v025_dx+0p00_dy+0p08_dz+0p00.png`

- chair(74) PASS 예시
  - `.../by_decision/PASS/obj_74_v025_dx+0p00_dy+0p08_dz+0p00.png`
- chair(74) FAIL 예시
  - `.../by_decision/FAIL/obj_74_v022_dx+0p00_dy-0p16_dz+0p00.png`
- chair(74) AMBIGUOUS 예시
  - `.../by_decision/AMBIGUOUS/obj_74_v024_dx+0p00_dy+0p00_dz+0p00.png`

---

## 다음 단계

이제 사용자는 v2 decision bucket 폴더만 훑어도 된다.

권장 판독 순서:
1. `by_decision/PASS/`에서 정말 PASS처럼 보이는지 확인
2. `by_decision/FAIL/`에서 정말 FAIL처럼 보이는지 확인
3. `by_decision/AMBIGUOUS/`가 경계 사례처럼 보이는지 확인
4. object별로 오판정 패턴이 보이면 그 사례의 variant slug를 알려주면 됨

그 피드백을 받은 뒤에
- threshold 조정
- ambiguous band 조정
- 필요 시 metric 조합 수정
을 진행한다.
