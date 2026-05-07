# Prior Insertion Geometry Phase A Initial Diagnostics (room_0)

Date: 2026-04-04

관련 문서:
- `docs/experiment_plans/04-04_prior_insertion_geometry_fix_plan_2026.md`
- `docs/notes/03-24_phase5_surface_alignment_bug_2026.md`
- `docs/experiment_results/03-24_phase5_surface_alignment_fix_smoke_2026.md`
- `docs/experiment_results/03-25_phase5_surface_alignment_fix_analysis_2026.md`

---

## 1. 목적

계획서의 Phase A-1 ~ A-4 중 room_0 대표 object를 먼저 확정하고, 현재 접근 가능한 artifact에서 다음을 비교했다.

1. source prior actual bbox
2. canonical seed bbox
3. alignment payload expected bbox
4. actual aligned prior bbox

이번 메모는 **threshold 확정 전의 초기 진단 기록**이다.

---

## 2. 대표 object 선정

대표 object는 과거 버그 문서와 smoke/fix 분석 문서에서 반복적으로 등장한 room_0의 4개 object로 고정했다.

- `obj_6` lamp
- `obj_9` sofa
- `obj_77` sofa
- `obj_74` chair

선정 근거:
- `docs/notes/03-24_phase5_surface_alignment_bug_2026.md`에 pre-fix 대표 오차로 명시됨
- `docs/experiment_results/03-24_phase5_surface_alignment_fix_smoke_2026.md`에 before/after center error가 재기록됨
- floor anchor object와 큰 object(sofa/chair)를 동시에 포함함

---

## 3. 사용한 artifact

### 3.1 pre-fix 기준

문서 기준 center error:
- `obj_6`: `2.58 m`
- `obj_9`: `4.01 m`
- `obj_77`: `4.80 m`
- `obj_74`: `6.01 m`

출처:
- `docs/experiment_results/03-24_phase5_surface_alignment_fix_smoke_2026.md`
- `docs/notes/03-24_phase5_surface_alignment_bug_2026.md`

### 3.2 post-fix / accessible artifact 기준

분석에 사용한 현재 접근 가능한 artifact:
- experiment specs:
  - `outputs/gaussian_direct/experiments/03-24-prior50k-geo-15k-2026/room_0/prior_specs.json`
- actual aligned prior:
  - `outputs/gaussian_direct/backend_runs/03-24-prior50k-geo-15k-2026/room_0/prior_init/aligned_prior_00.ply`
  - `outputs/gaussian_direct/backend_runs/03-24-prior50k-geo-15k-2026/room_0/prior_init/aligned_prior_01.ply`
  - `outputs/gaussian_direct/backend_runs/03-24-prior50k-geo-15k-2026/room_0/prior_init/aligned_prior_02.ply`
  - `outputs/gaussian_direct/backend_runs/03-24-prior50k-geo-15k-2026/room_0/prior_init/aligned_prior_03.ply`
- source priors / canonical seeds:
  - `outputs/gaussian_direct/prior_library/03-24-target-surface-trained-2026/assets/...`

주의:
- 현재 환경에서는 외부 dataset scene root의 `sparse/0/points3D.ply`에 접근할 수 없어, room sparse bbox 기준 outside ratio는 이번 메모에서 직접 재계산하지 못했다.
- 따라서 이번 기록은 **actual aligned prior vs target/alignment payload consistency** 중심이다.

---

## 4. 측정 결과

## 4.1 source prior bbox vs canonical seed bbox

네 object 모두에서 source prior actual bbox와 canonical seed bbox가 사실상 동일했다.

| object | source bbox size | canonical seed bbox size | delta |
|---|---|---|---|
| obj_6 lamp | `[1.007440, 2.625498, 1.412553]` | `[1.007440, 2.625498, 1.412553]` | `[0, 0, 0]` |
| obj_9 sofa | `[2.403190, 1.683846, 1.174273]` | `[2.403190, 1.683846, 1.174273]` | `[0, 0, 0]` |
| obj_77 sofa | `[2.361198, 1.142107, 1.027338]` | `[2.361198, 1.142107, 1.027338]` | `[0, 0, 0]` |
| obj_74 chair | `[0.896645, 0.841767, 1.103820]` | `[0.896645, 0.841767, 1.103820]` | `[0, 0, 0]` |

해석:
- 현재 접근 가능한 `03-24-target-surface-trained-2026` staged prior에서는 **source prior와 canonical seed frame bbox 차이 자체는 보이지 않는다**.
- 즉, 과거 world-frame insertion 버그는 현재 접근 가능한 fixed-stage artifact에는 그대로 남아 있지 않다.

## 4.2 actual aligned prior center / bottom error

| object | aligned center vs target center (L2 m) | aligned bottom vs target bottom (L2 m) |
|---|---:|---:|
| obj_6 lamp | `0.0031` | `0.0032` |
| obj_9 sofa | `0.0448` | `0.0463` |
| obj_77 sofa | `0.0047` | `0.0074` |
| obj_74 chair | `0.0120` | `0.0114` |

해석:
- 현재 접근 가능한 post-fix artifact 기준으로는 중심/바닥 anchor 오차가 모두 매우 작다.
- 특히 `obj_6`, `obj_77`, `obj_74`는 cm 이하~1cm대 수준이며, `obj_9`만 약 4.5cm 수준이다.

## 4.3 actual aligned prior AABB vs alignment payload expected AABB

이번 비교에서는 alignment payload의 `candidate_aabb_min/max`와 실제 `aligned_prior_*.ply`의 AABB를 비교했다.

결과:
- 네 object 모두 `aabb_protrusion_total = 0.0`
- 즉, **현재 접근 가능한 post-fix artifact에서는 actual aligned prior AABB가 payload expected AABB 밖으로 튀어나온 증거가 없다**.

대표 예시:
- obj_6 lamp
  - expected AABB min/max:
    - `[-1.748926, -3.876120, -1.526374]`
    - `[ 0.837194, -2.869815, -0.120695]`
  - actual AABB min/max:
    - `[-1.746309, -3.778546, -1.522247]`
    - `[ 0.836593, -2.967644, -0.130645]`
- obj_9 sofa
  - expected AABB min/max:
    - `[ 2.358860, -1.696025, -1.520004]`
    - `[ 4.890474, -0.096022, -0.599264]`
  - actual AABB min/max:
    - `[ 2.432790, -1.556552, -1.515485]`
    - `[ 4.810926, -0.324747, -0.608322]`

주의:
- lamp처럼 회전이 큰 object는 OBB size와 AABB size가 크게 다를 수 있다.
- 따라서 `target_sizes`와 `actual_aligned_bbox_size`를 직접 비교해 "크기 불일치"로 결론 내리면 안 되고, 이번 작업에서는 **AABB 위치 일치 / center-bottom error / actual outside ratio** 중심으로 봐야 한다.

---

## 5. 현재까지의 판단

### confirmed
- pre-fix 버그는 실제로 매우 큰 center error(2.58m~6.01m)를 만들었다.
- post-fix로 접근 가능한 `03-24-prior50k-geo-15k-2026/room_0` artifact에서는 representative 4개 object가 target 근처에 정렬되어 있다.
- 현재 접근 가능한 fixed-stage prior asset에서는 source prior bbox와 canonical seed bbox가 동일하다.
- actual aligned prior AABB가 payload expected AABB를 벗어나는 증거는 이번 샘플에서 보이지 않는다.

### confirmed by iteration_0 point-cloud proxy analysis
- 사용자가 지정한 경로 `outputs/gaussian_direct/backend_runs/03-24-prior50k-geo-15k-2026/room_0/point_cloud/iteration_0/스크린샷 2026-04-05 131005.png` 와 동일 run을 기준으로, `surface_prior_50k_geo_iter_0.ply`에서 prior 50K를 제거한 100K base point cloud를 room proxy로 사용해 최근접 거리/scene bbox 근사 검사를 다시 수행했다.
- 이 재검사에서는 이전의 "target 근처에 정렬됨"만으로는 놓친 문제가 드러났다.
  - lamp (`obj_6`): base scene 최근접 거리 평균 `2.427m`, 중앙값 `2.437m`, `outside_base_bbox_ratio = 1.0`
  - sofa (`obj_9`): base scene 최근접 거리 평균 `0.100m`, p99 `0.290m`, `outside_base_bbox_ratio = 0.185`
  - sofa (`obj_77`), chair (`obj_74`)는 상대적으로 scene proxy와 잘 맞음
- 해석:
  - lamp는 target box 중심과는 맞더라도, **현재 iteration_0 room geometry와는 완전히 분리된 허공 위치**에 있다고 보는 편이 타당하다.
  - sofa(`obj_9`)는 전체가 완전히 분리된 수준은 아니지만, **일부가 room/base scene bbox 밖으로 빠져나와 있다**고 볼 수 있다.
- 즉 사용자가 말한 "램프가 허공에 있다", "소파가 방 밖으로 빠져나와 있다"는 관찰은 현재 run artifact와 모순되지 않고, 오히려 point-cloud proxy 기준으로 지지된다.

### still not yet confirmed
- room sparse bbox 또는 실제 room boundary 메쉬 기준 outside ratio
- `oracle_target_box` 경로가 현재 코드에서도 어떤 조건에서 silent failure를 일으키는지
- `scale_meters` override가 이번 repro case의 직접 원인인지

---

## 6. immediate implication

현재 접근 가능한 post-fix artifact만 보면, 이미 알려진 03-24 alignment bug는 재현되지 않는다.

따라서 다음 두 가능성으로 좁혀진다.

1. **사용자가 본 문제는 다른 run / 다른 prior library / 다른 config에서 발생했다**
2. **현재 코드에는 fail-fast 검증이 없어서, 특정 조건에서만 다시 잘못된 prior가 통과할 수 있다**

즉, 지금 단계에서 바로 "현재 clean artifact도 여전히 틀리다"고 결론 내릴 수는 없다.
대신, **재현되는 run path를 특정하거나, 현재 코드에 actual aligned prior 기준 geometry validation을 추가해 silent failure를 차단하는 방향**이 타당하다.

---

## 7. 정책 결정

사용자 결정:
- fail-fast policy = **엄격**
- 해석: scene proxy 밖 비율이 조금만 커도 바로 실패시키는 방향으로 구현

현재 구현 반영:
- backend에서 actual aligned prior를 scene proxy와 비교해 geometry validation을 수행
- `outside_scene_proxy_ratio > 0.01` 또는 mean nearest-neighbor distance가 과도하면 실패
- validation 결과는 `prior_init/metadata.json`의 `selected_priors[*].geometry_validation`에 기록

## 8. 다음 권장 액션

1. 사용자가 최근 문제를 본 run path / scene / object / viewer artifact를 특정한다
2. 그 repro case를 이 메모와 같은 방식으로 다시 측정한다
3. 동시에 Phase B로 넘어가서:
   - actual aligned prior geometry validation
   - `oracle_target_box` fail-fast
   - bbox source provenance 기록 강화
   를 추가한다

현재 기준으로 가장 먼저 고칠 만한 지점은 여전히 다음 순서다.
- `scripts/train_vanilla_3dgs_backend.py`: actual aligned prior 기준 검증 추가
- `scripts/run_experiment.py`: alignment bbox source/provenance 명시 강화
- 필요 시 `oracle_target_box` 경로의 geometry sanity check 보강
