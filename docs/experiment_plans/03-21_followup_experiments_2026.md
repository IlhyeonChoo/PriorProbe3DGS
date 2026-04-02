# Gaussian-Direct 후속 실험 계획

Date: 2026-03-21

## 현재 상태 요약

### 확인된 사실

1. **Prior protection `weak` (lr_scale=0.02)가 현재 유일한 긍정적 결과**
   - `room_0` dense 384 views: TTT 112.03s vs baseline 118.85s (5.7% 개선)
   - prior 100000개 끝까지 보존
   - 단, final PSNR은 baseline보다 약간 낮음 (12.37 vs 12.49)

2. **Unprotected prior는 모든 조건에서 baseline과 동등하거나 느림**
   - dense view만 늘려서는 prior 파괴 문제를 해결하지 못함

3. **시점 편향 문제가 여전히 미해결**
   - 현재 카메라는 `compute_scene_focus(targets)`로 계산한 **타겟 객체 가중 중심**을 look-at으로 사용
   - 모든 학습 이미지가 특정 객체들이 화면 중심에 오도록 구성됨
   - 방 전체를 고르게 보는 시점이 없어, 배경 영역의 reconstruction quality가 낮을 수 있음
   - 이 편향이 prior 삽입 효과 측정 자체를 왜곡할 가능성 있음

---

## 실험 계획

### Phase 1: Protection Sweep 확장

**목적:** `weak` protection의 효과가 scene-specific인지, 데이터셋 조건에 따라 달라지는지 확인

#### Phase 1-B: `office_0` weak protection (dense 384 views)

- Dataset: `replica_colmap_multi_diverse_384`
- Scene: `office_0`
- Conditions:
  - baseline (이미 있음: TTT 144.41s)
  - unprotected exact (이미 있음: TTT 150.96s)
  - `weak` (lr_scale=0.02, protect_prune=true, protect_densify=true) **← 신규**
  - `freeze` (lr_scale=0.00) **← 신규**
- 확인할 것:
  - `room_0`에서 관찰된 패턴이 `office_0`에서도 재현되는가
  - `office_0`는 원래 96-view에서 prior가 효과적이었는데, dense view + protection에서는 어떤가

#### Phase 1-C: Original 96-view에서 weak protection

- Dataset: `replica_colmap_multi` (기존 96 views)
- Scenes: `room_0`, `office_0`
- Conditions:
  - baseline (이미 있음)
  - unprotected exact (이미 있음)
  - `weak` (lr_scale=0.02) **← 신규**
- 확인할 것:
  - 96-view `office_0`에서 unprotected가 이미 빨랐는데 (65.71s vs 89.55s), weak에서 추가 개선이 있는가
  - 96-view `room_0`에서 unprotected는 느렸는데 (90.96s vs 84.35s), weak이 이를 뒤집는가
  - dense view가 없어도 protection만으로 prior 효과가 나타나는 조건이 있는가

#### Phase 1 산출물

| scene | dataset | protection | 상태 |
|-------|---------|------------|------|
| room_0 | dense 384 | weak 0.02 | 완료 |
| room_0 | dense 384 | freeze | 완료 |
| room_0 | 96-view | weak 0.02 | **신규** |
| office_0 | dense 384 | weak 0.02 | **신규** |
| office_0 | dense 384 | freeze | **신규** |
| office_0 | 96-view | weak 0.02 | **신규** |

---

### Phase 2: Room-Wide View 데이터셋 구축 및 실험

**목적:** 시점 편향을 제거하고, 복원 공간 전체를 다양하게 관찰하는 조건에서 prior 효과를 재측정

#### 문제 정의

현재 exporter의 카메라 생성 로직:
```
focus_center = weighted_avg(target_centers, weights=sqrt(volume))
eye = focus_center + [r*cos(yaw), r*sin(yaw), z_offset]
look_at = focus_center  ← 항상 객체 클러스터를 바라봄
```

이 구조에서는:
- 모든 카메라가 객체 클러스터 방향을 향함
- 벽, 바닥, 천장, 객체 반대편 공간이 학습 이미지에 거의 나타나지 않음
- prior가 기여할 수 있는 배경 영역의 gradient 정보가 부족

#### 변경 방향

- look-at 대상을 **방의 기하학적 중심**(mesh bounding box center)으로 변경
- 또는 look-at 대상을 **다양화** (객체 중심, 방 중심, 벽면 등을 균등 배분)
- radius 범위를 방 크기에 맞게 확장
- visibility filtering에서 **object visibility를 필수 조건에서 제외** (일부 이미지는 객체가 안 보여도 OK)
- 구체적 구현 방식은 Phase 1 결과를 보고 결정

#### 실험 조건

- Scene: `room_0`, `office_0`
- Views: 384 (기존과 동일한 이미지 수로 시점 다양성 효과만 분리)
- Conditions:
  - baseline (from-scratch)
  - unprotected exact prior
  - weak (lr_scale=0.02)
- 비교 기준:
  - 동일 이미지 수의 object-centric view 결과 (Phase 1 결과)와 직접 대조
  - 시점 다양성이 prior 보존율과 최종 품질에 미치는 영향 분석

---

### Phase 3: `prior_lr_scale` Sweep

**목적:** weak protection의 lr_scale 최적점을 찾아 TTT와 final quality의 균형을 잡음

- Scene: `room_0` 기준 (Phase 2의 room-wide view 데이터셋 사용)
- lr_scale 후보: `0.01`, `0.02`, `0.05`, `0.1`
- protect_prune: true (고정)
- protect_densify: true (고정)
- 확인할 것:
  - TTT vs final PSNR의 trade-off curve
  - prior 보존 수 변화 (lr_scale이 높아지면 prior가 변형되어 사실상 보존이 아닐 수 있음)
  - 최적 lr_scale이 scene이나 view 조건에 따라 달라지는지

---

### Phase 4: 실험 정리 및 아카이브

**목적:** Phase 1~3의 결과를 정리하고, 이후 실제 RGB 데이터 실험을 위한 깨끗한 출발점을 만듦

#### 문서 정리

- Phase 1~3 실험 보고서를 `docs/experiment_results/`에 정리
- `docs/gaussian_direct_branch_plan.md`의 Experimental Findings 섹션 갱신
- 비교표 통합: 모든 조건의 TTT / final PSNR / prior 보존율을 하나의 summary table로

#### 데이터 및 산출물 정리

- 보존 대상 분류:
  - **Git에 남길 것:** config YAML, evaluation.json, backend_run.json, 보고서
  - **HDD로 이동:** backend_runs 아래 checkpoint (point_cloud/), 학습 로그
  - **삭제 가능:** smoke test 산출물 (1000 iter runs)
- HDD 경로 규칙: `{HDD_ROOT}/priorprobe3dgs/archive/gaussian_direct/{experiment_name}/`
- 이동 후 `outputs/gaussian_direct/`에는 metadata만 남기고 대용량 파일은 제거

#### Git 정리

- 불필요한 untracked 파일 정리
- `.gitignore` 갱신 (필요시)
- Phase 1~3 완료 시점에서 정리 commit

---

### Phase 5: 면 기반 Surface Rendering 이미지로 전환

**목적:** 현재 점 기반 sparse 이미지를 면 기반 surface rendering 이미지로 교체하여 실험의 현실성 확보

#### 문제 현상

현재 학습에 사용되는 모든 이미지가 **점 기반 sparse rendering**으로 생성되어 있다.

```
ReplicaHabitatRenderer (habitat_sim)  → 면 기반 surface rendering  → habitat_sim 미설치로 사용 불가
ReplicaPointRenderer (fallback)       → 점 기반 sparse rendering   → 현재 사용 중
```

`ReplicaPointRenderer`는 mesh에서 100만 개 점을 샘플링한 뒤 카메라 평면에 투영하는 방식이다. 점 사이에 빈 틈이 존재하며, 실제 촬영 사진과는 크게 다르다.

#### 원인

- `replica_export.py`에서 `ReplicaHabitatRenderer`를 먼저 시도하고, `habitat_sim` import 실패 시 `ReplicaPointRenderer`로 fallback한다 (line 700-711)
- 현재 환경에 `habitat_sim`이 설치되어 있지 않다

#### 해결 방향

**옵션 1: `habitat_sim` 설치** (가장 직접적)
- Replica GT mesh에서 `habitat_sim`으로 surface rendering → 실제 사진과 유사한 면 기반 이미지 생성
- 동일 카메라 pose에서 렌더러만 교체하면 되므로 비교 조건 통제가 깨끗함
- 단, `habitat_sim`은 Python/CUDA 버전 호환성 문제가 까다로울 수 있음

**옵션 2: 대안 mesh renderer 사용**
- `pyrender`, `Open3D`, `trimesh` 등으로 Replica mesh를 면 기반으로 렌더링
- `habitat_sim` 없이도 surface rendering 가능
- semantic rendering이 필요한 경우 별도 처리 필요

**옵션 3: Replica 공식 pre-rendered 이미지 사용**
- Replica 데이터셋에 포함된 trajectory별 RGB 이미지가 이미 면 기반 rendering임
- 단, 카메라 pose를 커스텀으로 제어할 수 없고 COLMAP 변환이 필요

구체적 방식은 Phase 4 완료 후, `habitat_sim` 설치 가능 여부를 확인한 뒤 결정한다.

#### 데이터셋 재생성

- 기존 exporter (`export_replica_multi_oracle_scene`)의 카메라 pose 생성 로직은 그대로 유지 (Phase 2의 room-wide view 포함)
- 렌더러만 surface 방식으로 교체하여 동일 pose에서 이미지 재생성
- COLMAP sparse reconstruction도 재실행 필요 (이미지 특성이 크게 바뀌므로)

#### 실험 구성

- Phase 1~3에서 확정된 최적 protection 설정을 고정
- Room-wide view 방식의 카메라 구성 적용
- baseline vs weak protection 비교를 우선 실행
- 점 기반 이미지 결과 vs 면 기반 이미지 결과 교차 비교
- 면 기반 이미지에서 prior 효과가 달라지는지 확인 (점 기반에서 빈 틈이 prior 효과를 왜곡했을 가능성)

---

## 실행 순서 요약

```
Phase 1-B: office_0 protection sweep (dense 384)
Phase 1-C: room_0 + office_0 protection (96-view)
    ↓
Phase 2: Room-wide view 데이터셋 구축 + 실험
    ↓
Phase 3: lr_scale sweep (room-wide view 기준)
    ↓
Phase 4: 문서/데이터 정리, HDD 아카이브
    ↓
Phase 5: 면 기반 surface rendering 이미지로 전환 + 실험
```

## 판단 기준

각 Phase에서 다음 단계로 넘어가기 전에 확인할 사항:

| Phase | Go 조건 | Stop/Pivot 조건 |
|-------|---------|----------------|
| 1-B/C | weak protection이 2개 이상 scene/dataset 조건에서 baseline을 이김 | 모든 조건에서 baseline과 동등하거나 느림 → Phase 2로 바로 진행하되 protection 자체를 재검토 |
| 2 | Room-wide view가 object-centric view 대비 prior 효과를 개선 | 시점 다양성을 바꿔도 차이가 없음 → prior 자체의 문제(scale, appearance)로 원인 재탐색 |
| 3 | lr_scale에 따라 TTT-quality trade-off가 명확히 존재 | 모든 lr_scale에서 비슷한 결과 → protection 메커니즘 자체를 재설계 |
| 4 | 정리 완료, 깨끗한 코드/데이터 상태 | - |
| 5 | 면 기반 이미지에서도 prior 효과 패턴이 유지되거나 개선됨 | 면 기반에서 prior 효과가 사라짐 → 점 기반 이미지의 sparse 특성이 prior에 유리하게 작용했을 가능성 검토 |
