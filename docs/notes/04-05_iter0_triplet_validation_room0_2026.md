# room_0 Iter0 Triplet Validation Note

Date: 2026-04-05

관련 문서:
- `docs/experiment_plans/04-04_prior_insertion_geometry_fix_plan_2026.md`
- `docs/notes/04-05_oracle_target_room_containment_root_cause_2026.md`

---

## Summary

room-contained room_0 dataset / prior set 기준으로 다음 두 smoke run의 `iter_0` test renders를 비교했다.

- Baseline:
  - `surface_rgb_roomcontained_baseline_smoke_1000`
- Prior:
  - `surface_rgb_roomcontained_prior_100k_geo_smoke_1000`

비교 축:
1. `test` GT
2. baseline iter_0 render
3. prior iter_0 render

현재 단계에서 자동 생성한 산출물은 **수동 시각 검토용 증거 패키지**로 본다.

---

## Artifact paths

### Contact sheet
- `outputs/gaussian_direct/reports/iter0_triplet_roomcontained_room0/room_0_iter0_triplet_8views.png`

### Per-view strips
- `outputs/gaussian_direct/reports/iter0_triplet_roomcontained_room0/per_view/`

### Metrics summary
- `outputs/gaussian_direct/reports/iter0_triplet_roomcontained_room0/metrics.csv`
- `outputs/gaussian_direct/reports/iter0_triplet_roomcontained_room0/metrics.json`
- `outputs/gaussian_direct/reports/iter0_triplet_roomcontained_room0/diffs/`
- `outputs/gaussian_direct/reports/iter0_triplet_roomcontained_room0/summary.json`

### Source render dirs
- GT:
  - `outputs/gaussian_direct/backend_runs/surface_rgb_roomcontained_baseline_smoke_1000/room_0/test/ours_0/gt`
- Baseline iter_0 renders:
  - `outputs/gaussian_direct/backend_runs/surface_rgb_roomcontained_baseline_smoke_1000/room_0/test/ours_0/renders`
- Prior iter_0 renders:
  - `outputs/gaussian_direct/backend_runs/surface_rgb_roomcontained_prior_100k_geo_smoke_1000/room_0/test/ours_0/renders`

---

## Selected views

이번 contact sheet에는 아래 8개 test view를 사용했다.

- `00000.png`
- `00009.png`
- `00018.png`
- `00027.png`
- `00036.png`
- `00045.png`
- `00054.png`
- `00063.png`

선정 방식:
- 공통으로 존재하는 test iter_0 png 중에서 정렬 순서 기준 균등 샘플링

---

## Quantitative helper metrics

아래 값은 위치 정합성의 직접 증거는 아니고, **시각 검토 우선순위를 정하는 보조 지표**다.

가장 baseline/prior 차이가 큰 view (MAE prior-vs-baseline 기준):

1. `00054.png`
   - `mae_prior_baseline = 5.0878`
   - `delta_mae_prior_minus_baseline = -0.5233`
2. `00027.png`
   - `mae_prior_baseline = 5.0851`
   - `delta_mae_prior_minus_baseline = -0.8189`
3. `00000.png`
   - `mae_prior_baseline = 4.7985`
   - `delta_mae_prior_minus_baseline = -1.1424`

해석 주의:
- 이 숫자는 prior/baseline 간 픽셀 차이를 보는 것이지, object 위치가 꼭 맞다는 뜻은 아니다.
- 위치 어긋남, 물체 shape drift, 떠 보임, baseline 대비 shift는 반드시 contact sheet와 per-view strip에서 수동 확인해야 한다.

---

## Current interpretation

- room-contained target set으로 교체한 뒤 geometry fail-fast smoke는 통과했다.
- 또한 iter_0 triplet 비교 artifact를 생성했으므로, 이제 baseline / prior / GT를 같은 pose에서 직접 육안 비교할 수 있다.
- 다만 자동 metric만으로는 table / sofa / lamp의 미세한 위치 어긋남을 확정할 수 없으므로, 이 note만으로 "위치 완전 일치"를 선언하지 않는다.

---

## Next recommended action

1. contact sheet와 per-view strip에서 table / sofa / lamp 위치를 수동 검토
2. 만약 prior 쪽만 미묘하게 밀리거나 떠 보이는 view가 있으면, 해당 view를 기준으로 object overlay 또는 bbox overlay 검증 추가
3. room_0 수동 검토가 통과하면 office_0에도 동일 iter_0 triplet validation을 적용
