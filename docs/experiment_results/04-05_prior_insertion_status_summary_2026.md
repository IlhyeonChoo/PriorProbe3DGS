# Prior Insertion Status Summary

Date: 2026-04-05

관련 문서:
- `docs/experiment_plans/04-04_prior_insertion_geometry_fix_plan_2026.md`
- `docs/notes/04-04_prior_insertion_geometry_phaseA_room0_2026.md`
- `docs/notes/04-05_oracle_target_room_containment_root_cause_2026.md`
- `docs/notes/04-05_iter0_triplet_validation_room0_2026.md`

---

## 1. 문서 목적

이 문서는 현재까지 prior insertion 관련 작업 상태를 한 번에 정리하기 위한 중간 결과 보고서다.

정리 대상:
1. 어떤 문제가 관찰되었는가
2. 어떤 방식으로 원인을 좁혔는가
3. 어떤 수정과 재생성을 적용했는가
4. 현재 무엇이 해결되었고, 무엇이 아직 남아 있는가

---

## 2. 현재까지 확인된 문제

초기 문제는 크게 두 층위로 나뉜다.

### 2.1 geometry 배치 오류

사용자 관찰과 repro artifact 기준으로 다음 문제가 확인되었다.

- lamp(obj_6)가 room geometry와 분리된 허공에 배치됨
- sofa(obj_9)가 room 밖으로 일부 protrusion 됨
- 내부 inspection / screenshot 기준으로 prior가 baseline 대비 미묘하게 다른 위치에 보이는 view가 존재함

대표 repro:
- `outputs/gaussian_direct/backend_runs/03-24-prior50k-geo-15k-2026/room_0/point_cloud/iteration_0/스크린샷 2026-04-05 131005.png`

이 repro를 strict scene-relative geometry validation으로 다시 보면:
- lamp(obj_6)
  - `outside_scene_proxy_ratio = 1.0`
  - `scene_proxy_mean_nn_distance_m ≈ 2.43`
- sofa(obj_9)
  - `outside_scene_proxy_ratio ≈ 0.185`

즉, 단순한 시각화 착시가 아니라 실제 geometry bug였다.

### 2.2 target-relative correctness와 scene-relative correctness의 분리 필요

이전에는 아래만 보면 정상처럼 보일 수 있었다.
- `target_center`
- `center_error`
- `bottom_error`
- alignment payload의 expected AABB

하지만 이번 문제는 그보다 바깥쪽인
- room / base scene geometry 기준의 위치 정합성
을 보지 않으면 놓친다는 점이 확인되었다.

---

## 3. 원인 분석 결과

현재까지 가장 강하게 지지되는 root cause는 다음이다.

### 3.1 직접 원인: 잘못된 oracle target selection

`room_0`의 기존 `oracle/targets.json`는 volume 기준 top-4 object를 사용했다.

기존 target set:
- `6` lamp
- `9` sofa
- `77` sofa
- `74` chair

문제는 이 target set이 room-contained reconstruction 조건에 맞지 않았다는 점이다.

room bbox 기준 outside ratio:
- `obj_6` lamp: `1.0`
- `obj_9` sofa: `~0.319`
- `obj_77` sofa: `~0.002`
- `obj_74` chair: `~0.0`

즉 lamp와 sofa(obj_9)는 애초에 room reconstruction target로 쓰기 부적절했다.

### 3.2 코드 레벨 원인

문제 위치:
- `src/priorprobe/replica_export.py`
- `select_top_targets()`

기존 동작:
- category filter
- volume sort
- top-K 선택

빠져 있던 것:
- room containment 검증
- target center가 room bbox 안에 있는지
- target AABB가 room bbox를 얼마나 벗어나는지

### 3.3 전파 경로

surface RGB dataset은 reference roomwide dataset의 oracle targets를 그대로 복사한다.
따라서 reference target metadata가 잘못되면 surface RGB dataset도 동일한 문제를 상속한다.

---

## 4. 적용한 수정

### 4.1 runtime fail-fast validation 추가

수정 파일:
- `scripts/train_vanilla_3dgs_backend.py`
- `src/priorprobe/optimization/vanilla_3dgs.py`

적용 내용:
- actual aligned prior를 scene proxy(base scene point cloud) 기준으로 검증
- fail-fast 조건 추가
  - `outside_scene_proxy_ratio > 0.01`
  - `scene_proxy_mean_nn_distance_m > 0.5`
- 각 prior에 대해 `geometry_validation` 기록
- `geometry_validation_policy`를 metadata / command provenance에도 반영

의미:
- 잘못된 prior placement가 이제 조용히 통과하지 않음
- repro case는 실제로 fail-fast 되는 것을 외부 dataset smoke로 확인함

### 4.2 oracle target selection에 room containment 필터 추가

수정 파일:
- `src/priorprobe/replica_export.py`

새 규칙:
- target center must be inside room bbox
- target AABB outside-room ratio <= `0.01`

테스트:
- `tests/test_replica_export.py`에 회귀 테스트 추가

전체 관련 테스트:
- `25 passed`

---

## 5. 재생성한 산출물

### 5.1 oracle target metadata 재생성

교체 대상:
- reference dataset
  - `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_v2_384/room_0/oracle/target.json`
  - `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_v2_384/room_0/oracle/targets.json`
- surface RGB dataset
  - `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_v2_384_surface_rgb/room_0/oracle/target.json`
  - `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_v2_384_surface_rgb/room_0/oracle/targets.json`

backup stamp:
- `20260405_060556`

재생성 후 room_0 target set:
- `77` sofa
- `74` chair
- `73` chair
- `11` table

### 5.2 새 target set 기준 surface/object/prior 재생성

새 dataset / prior artifact 경로:
- scene dataset root
  - `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_v2_384_surface_rgb_roomcontained`
- dataset config
  - `configs/datasets/replica_multi_roomwide_v2_384_surface_rgb_roomcontained_shared.yaml`
- object dataset root
  - `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_object_surface_exact_rgb_roomcontained`
- prior training root
  - `outputs/gaussian_direct/prior_training/04-05-surface-trained-roomcontained-7k-2026`
- prior stage root
  - `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-2026`
- prior manifest
  - `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-manifest-2026.json`
- prior config
  - `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-2026.yaml`
- prep note
  - `docs/notes/04-05_phase5_surface_prep_roomcontained_room0_2026.md`

---

## 6. 현재 smoke 결과

### 6.1 strict geometry validation repro smoke

repro 조건:
- old target set / old prior spec 기반 smoke

결과:
- 의도대로 fail-fast
- 실패 대상:
  - lamp(obj_6): `outside_scene_proxy`, `floating_from_scene_proxy`
  - sofa(obj_9): `outside_scene_proxy`

의미:
- 예전 문제는 이제 초기에 차단됨

### 6.2 room-contained smoke

새 smoke config:
- `configs/experiments/gaussian_direct_surface_rgb_roomcontained_prior_100k_geo_smoke_1000.yaml`

결과:
- `gaussian_direct_surface_rgb_roomcontained_prior_100k_geo_smoke_1000`
- geometry validation passed
- 새 target set의 4개 prior 모두 fail-fast 없이 통과

### 6.3 baseline smoke

baseline smoke config:
- `configs/experiments/gaussian_direct_surface_rgb_roomcontained_baseline_smoke_1000.yaml`

결과:
- baseline smoke도 완료
- 이제 같은 pose에서 GT / baseline / prior를 나란히 비교할 수 있는 상태가 됨

---

## 7. 추가한 iter0 시각 검증 단계

문제는 room 밖 protrusion만이 아니라,
같은 room 안에서도 baseline 대비 prior의 물체 위치가 미묘하게 어긋날 수 있다는 점이다.

그래서 iter0 기준 3자 비교 artifact를 추가 생성했다.

비교 축:
1. test GT
2. baseline iter_0 render
3. prior iter_0 render

artifact:
- contact sheet
  - `outputs/gaussian_direct/reports/iter0_triplet_roomcontained_room0/room_0_iter0_triplet_8views.png`
- per-view strips
  - `outputs/gaussian_direct/reports/iter0_triplet_roomcontained_room0/per_view/`
- metrics/diffs
  - `outputs/gaussian_direct/reports/iter0_triplet_roomcontained_room0/metrics.csv`
  - `outputs/gaussian_direct/reports/iter0_triplet_roomcontained_room0/diffs/`
- note
  - `docs/notes/04-05_iter0_triplet_validation_room0_2026.md`

의미:
- 이제 사용자는 단순 수치가 아니라 같은 pose에서 table / sofa / lamp 위치가 baseline과 prior 사이에서 미묘하게 어긋나는지 직접 확인할 수 있다.

---

## 8. 현재 해결된 것

해결된 항목:
1. room 밖 object가 oracle target으로 선택되던 문제의 root cause 식별
2. 잘못된 target selection을 runtime 전에 차단하는 strict geometry validation 도입
3. room_0에 대해 room-contained oracle target metadata 재생성
4. room_0에 대해 새 target set 기준 surface/object/prior 재생성
5. 새 target set 기준 prior smoke가 geometry validation을 통과함
6. baseline / prior / GT iter0 triplet 비교 artifact 생성

---

## 9. 아직 남아 있는 한계

### 9.1 미세한 object 위치 어긋남은 아직 사용자 시각 검토가 필요

현재 자동으로 확인 가능한 것은 주로
- room 밖으로 나갔는지
- 허공에 떴는지
- scene proxy와 너무 멀리 떨어졌는지
이다.

하지만 사용자가 지적한
- table / sofa / lamp 위치의 미묘한 shift
는 아직 contact sheet를 사람이 보고 판정해야 한다.

즉,
- geometry fail-fast는 통과했지만
- “baseline과 prior가 완전히 같은 room structure alignment를 유지하는가”는 아직 최종 확정 아님

### 9.2 office_0는 아직 같은 수준으로 재정리되지 않음

현재 room_0는 정리됐지만,
- office_0에 대해 같은 room-containment 검증
- oracle target 재생성
- downstream prior 재생성
- iter0 triplet 비교
는 아직 별도 수행 필요

### 9.3 prior 품질 자체는 아직 더 올릴 여지가 있음

사용자가 지적한 것처럼,
- prior 자체를 더 고품질로 학습하거나
- 원본 shape/appearance에 더 가깝게 삽입되도록 개선하거나
- prior 삽입 위치의 base Gaussian/SfM seed를 제거하는 정책
은 아직 본격적으로 적용하지 않았다.

현재까지는 우선 geometry correctness와 upstream target semantics를 바로잡는 단계였다.

---

## 10. 다음 단계 제안

우선순위 1
- `room_0_iter0_triplet_8views.png` 및 per-view strip을 기준으로
  - table
  - sofa
  - lamp
의 미세 위치 어긋남을 사용자가 확인

우선순위 2
- 사용자가 지적한 view/object를 기준으로
  - bbox overlay
  - object-specific overlay
  - baseline/prior alignment 차이 정량화
를 추가

우선순위 3
- 이후 다음 개선을 단계적으로 검토
  1. prior 품질 상향
  2. 원본에 더 가까운 삽입 방식
  3. prior 삽입 영역의 sparse view / initial Gaussian 제거 정책

---

## 현재 시점 한 줄 요약

가장 큰 구조적 문제였던 "방 밖 object를 oracle target으로 선택해 잘못된 prior를 삽입하는 문제"는 room_0에서 해결되었고, 이제 남은 핵심 과제는 **room 내부에서 baseline 대비 prior 위치가 미묘하게 어긋나는지 iter0 triplet 비교로 검증하는 것**이다.
