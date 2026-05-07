# Sofa77 HQ Handoff for Next Agent

Date: 2026-04-05

관련 문서:
- `docs/notes/04-05_all4_roomcontained_hq192_15k_prior_rebuild_2026.md`
- `docs/notes/04-05_sofa77_hq_prior_rebuild_2026.md`
- `docs/notes/04-05_prior_position_fine_sweep_room0_100each_2026.md`
- `docs/notes/04-05_prior_position_sweep_room0_v2_2026.md`

---

## 1. 사용자 의도와 최근 수정 사항

사용자는 "고품질 prior"를 다음 의미로 명확히 정의했다.
- prior를 그냥 다시 만드는 것이 아니라
- object prior training dataset의 train image 수를 크게 늘리고
- training iteration도 늘려서
- prior 자체 품질을 올리라는 뜻이다.

이 해석에 따라 기존 roomcontained prior(96 views / train 80 / test 16 / 7000 iter) 대신,
4개 object 전체에 대해 HQ prior를 새로 만들었다.

새 HQ 설정:
- total views: `192`
- train views: `176`
- test views: `16`
- train iterations: `15000`

---

## 2. 이미 완료된 작업

### 2.1 4개 object HQ prior 재생성 완료

새 dataset / training / library 경로:
- scene dataset root
  - `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_v2_384_surface_rgb_roomcontained_hq192`
- scene dataset config
  - `configs/datasets/replica_multi_roomwide_v2_384_surface_rgb_roomcontained_hq192_shared.yaml`
- object dataset root
  - `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_object_surface_exact_rgb_roomcontained_hq192`
- prior training root
  - `outputs/gaussian_direct/prior_training/04-05-surface-trained-roomcontained-hq192-15k-2026`
- prior library root
  - `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-2026`
- manifest
  - `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-manifest-2026.json`
- config
  - `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-2026.yaml`
- inventory
  - `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-inventory-2026.json`

object별 trained point cloud:
- sofa 77
  - `outputs/gaussian_direct/prior_training/04-05-surface-trained-roomcontained-hq192-15k-2026/room_0/77/point_cloud/iteration_15000/point_cloud.ply`
- chair 74
  - `outputs/gaussian_direct/prior_training/04-05-surface-trained-roomcontained-hq192-15k-2026/room_0/74/point_cloud/iteration_15000/point_cloud.ply`
- chair 73
  - `outputs/gaussian_direct/prior_training/04-05-surface-trained-roomcontained-hq192-15k-2026/room_0/73/point_cloud/iteration_15000/point_cloud.ply`
- table 11
  - `outputs/gaussian_direct/prior_training/04-05-surface-trained-roomcontained-hq192-15k-2026/room_0/11/point_cloud/iteration_15000/point_cloud.ply`

builder code change:
- `scripts/prepare_replica_phase5_surface_assets.py`
- `--target-object-id` 옵션 추가
- 특정 object만 선택 재생성 가능

### 2.2 validator / sweep tooling 상태

관련 스크립트:
- `scripts/validate_prior_positions.py`
- `scripts/collect_prior_position_sweep.py`
- `scripts/collect_prior_position_fine_sweep.py`

핵심 상태:
- coarse sweep v2는 16 views, 4x4, edge-only 구조로 생성됨
- fine sweep은 user-selected PASS anchor 주변을 미세 sampling 가능
- `scripts/collect_prior_position_fine_sweep.py`에는 `--override-source-prior-json` 옵션을 추가하여,
  기존 base run metadata를 유지한 채 새 source prior asset을 alignment transform으로 대체해 평가 가능하게 함

관련 테스트:
- `tests/test_collect_prior_position_sweep.py`
- `tests/test_collect_prior_position_fine_sweep.py`
- `tests/test_collect_prior_position_fine_sweep_override.py`
- `tests/test_prior_position_validator.py`

최근 확인된 테스트 상태:
- `12 passed`

---

## 3. sofa(obj_77) 관련 최근 실험 결과

### 3.1 기존 fine sweep 결과

기존 source prior 기준에서는 사용자가 sofa anchor를 PASS로 보더라도,
validator는 거의 또는 전부 `AMBIGUOUS`로 남는 경향이 있었다.

### 3.2 새 HQ sofa prior로 50개 위치 비교 완료

실행 목적:
- 새 HQ192/15k sofa prior를 사용했을 때,
- `obj_77`만 50개 미세 위치에서 어떤 분포가 나오는지 확인

실행 결과 root:
- `outputs/gaussian_direct/reports/prior_position_sofa77_hq15k_fine50_2026`

핵심 파일:
- `outputs/gaussian_direct/reports/prior_position_sofa77_hq15k_fine50_2026/aggregate_summary.json`
- `outputs/gaussian_direct/reports/prior_position_sofa77_hq15k_fine50_2026/object_77/summary.json`
- `outputs/gaussian_direct/reports/prior_position_sofa77_hq15k_fine50_2026/by_decision/AMBIGUOUS/`

결과:
- PASS: `0`
- FAIL: `0`
- AMBIGUOUS: `50`

중요 해석:
- 새 HQ sofa prior를 써도 현재 validator 기준은 sofa에 대해 여전히 PASS를 못 내리고 있다.
- 즉 문제는 prior 품질 부족만이 아니라,
  - sofa silhouette / edge metric 자체가 보수적이거나
  - edge background 추출이 사용자 시각과 다르거나
  - validator threshold/decision rule이 sofa에 맞지 않을 가능성이 남아 있다.

---

## 4. edge 관련 현재 한계

현재 edge background 생성 경로:
- `scripts/collect_prior_position_sweep.py`
- 함수: `_image_edge_background()`

현재 방식:
- grayscale 변환
- x/y 차분 기반 gradient magnitude
- quantile 정규화

사용자 피드백:
- sofa는 실제 이미지에서 중간이 깨져 보이고
- edge가 사람이 보는 경계와 많이 다르게 잡힌다

즉 다음 agent는
- 현재 gradient edge가 사람 시각 기준 edge와 얼마나 어긋나는지
- silhouette-friendly edge extraction 또는 다른 review visualization으로 바꿔야 하는지
우선 검토할 필요가 있다.

---

## 5. 다음 agent가 바로 이어서 할 만한 작업

우선순위 1
- `prior_position_sofa77_hq15k_fine50_2026/by_decision/AMBIGUOUS/`를 샘플링해 사람이 보기에 PASS로 볼 수 있는지 확인
- 현재 50개가 전부 AMBIGUOUS인 원인이
  - 실제 위치 문제인지
  - edge visualization 문제인지
  - threshold 문제인지
분리

우선순위 2
- edge background 생성 개선
  - 현재 `_image_edge_background()` 대체 검토
  - 사용자 시각 기준 edge에 더 가까운 방식으로 변경
  - 필요하면 RGB 없이 silhouette + sparse edge만 남기는 방향 검토

우선순위 3
- 새 HQ192/15k full prior library를 실제 room_0 insertion smoke에 연결
  - old prior vs new HQ prior 직접 비교
  - iter0 비교 artifact 재생성

우선순위 4
- sofa 전용 threshold 또는 decision band를 별도로 둘지 검토
  - 다만 family-wide rule을 깨는지 주의

---

## 6. 자주 참조할 경로

새 HQ prior library manifest:
- `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-manifest-2026.json`

새 HQ sofa source asset:
- `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-2026/assets/sofa/replica_room_0_obj_77/splat.ply`

새 HQ sofa training model:
- `outputs/gaussian_direct/prior_training/04-05-surface-trained-roomcontained-hq192-15k-2026/room_0/77`

sofa 50-case review root:
- `outputs/gaussian_direct/reports/prior_position_sofa77_hq15k_fine50_2026`

all-4 HQ rebuild summary note:
- `docs/notes/04-05_all4_roomcontained_hq192_15k_prior_rebuild_2026.md`

---

what changed
- 4개 object 전체 HQ192/15k prior rebuild 완료, 그리고 새 HQ sofa prior를 사용한 obj_77 전용 50-case fine sweep까지 완료했다.

what was checked
- 새 object datasets / prior training / prior library artifact 생성 완료
- sofa HQ prior 전용 fine sweep 50 cases 생성 완료
- 관련 테스트 12개 통과

what remains risky
- 새 HQ sofa prior를 써도 validator는 50/50 AMBIGUOUS다. prior 품질만의 문제가 아닐 수 있으며 edge visualization 또는 decision rule 문제가 남아 있다.

next concrete action
- 다음 agent는 `prior_position_sofa77_hq15k_fine50_2026/by_decision/AMBIGUOUS/`를 우선 검토하고, edge extraction 개선 또는 sofa decision rule 조정을 진행하면 된다.
