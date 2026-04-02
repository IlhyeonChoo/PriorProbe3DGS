# Phase 5: Surface RGB 이미지 기반 Prior 삽입 실험

Date: 2026-03-23

이전 계획:
- `docs/experiment_plans/03-21_followup_experiments_2026.md` (Phase 1-5 원본)
- `docs/experiment_plans/03-22_phase3_protection_disabled_2026.md` (Phase 3 재정의)
- `docs/experiment_plans/03-23_office0_cross_validation_2026.md` (office_0 교차검증)

---

## 배경

### Phase 1-3 요약

점 기반 sparse rendering 이미지(ReplicaPointRenderer)로 학습한 실험에서 확인된 사실:

| 결론 | 내용 |
|------|------|
| 최선 정책 | A 25K(none) — prior 25K 서브샘플링, protection 기본값 |
| 간섭 완화 | 조합(A+B, A+C, A+B+C)은 A 단독 대비 개선 없음 |
| Protection | lr_scale, prune/densify 보호 설정은 final PSNR에 무관 |
| Prior 기여 | room_0 +0.056 dB, office_0 +0.076 dB (baseline 대비) |

**단, Phase 1-3 multi-object 실험은 metadata indexing 버그의 영향을 받았다.** 버그는 수정됨(`resolve_selected_prior_metadata_items()` 추가). Phase 5는 수정된 코드로 실행된다.

### Phase 5의 목적

점 기반 sparse 이미지에는 물체 사이 빈 공간이 많아 prior 효과를 왜곡할 가능성이 있다. Surface RGB 이미지로 전환하여:

1. **이미지 품질 변화에 따른 baseline PSNR 변화 확인** — surface 이미지는 dense하므로 baseline이 달라질 수 있음
2. **Prior 삽입 효과가 이미지 품질에 의존하는지 검증** — 점 기반에서의 +0.056 dB가 surface에서도 유지되는가
3. **버그 수정 후 올바른 multi-object 삽입 결과 확보** — Phase 1-3 결과의 유효성 교차 확인

### Phase 5에서 달라지는 것

| 항목 | Phase 1-3 (점 기반) | Phase 5 (surface RGB) |
|------|--------------------|-----------------------|
| Scene 이미지 | ReplicaPointRenderer (sparse) | pyrender EGL vertex-color (dense) |
| Prior 소스 | scene에서 직접 추출 (25K each) | surface RGB로 학습 (7000 iter) |
| Prior Gaussian 수 | 균일 25K/object | object마다 다름 (15K~54K) |
| COLMAP sparse | 점 기반 이미지에서 추출 | 동일 pose, 동일 sparse 재사용 |
| 3DGS Backend | vanilla 3DGS | 동일 |
| 평가 기준 | 점 기반 이미지와 비교 | surface RGB 이미지와 비교 |

---

## 준비 상태

| 항목 | 상태 | 비고 |
|------|------|------|
| Scene 이미지 (384장 × 2 scenes) | **완료** | `replica_colmap_multi_roomwide_v2_384_surface_rgb/` |
| COLMAP sparse | **완료** | roomwide_v2_384에서 재사용 |
| Object prior 학습 (8 objects, 7000 iter) | **완료** | `prior_training/replica_surface_exact_trained_7000/` |
| Prior library (CLIP indexed) | **완료** | `prior_library/replica_target_surface_exact_trained_clip/` |
| Dataset config | **완료** | `replica_multi_roomwide_v2_384_surface_rgb_shared.yaml` |
| Metadata indexing 버그 수정 | **완료** | `resolve_selected_prior_metadata_items()` |

### Surface-trained Prior Gaussian 수

| Scene | Object | Category | Gaussians |
|-------|--------|----------|----------:|
| room_0 | obj_6 | lamp | 15,786 |
| room_0 | obj_74 | chair | 34,054 |
| room_0 | obj_77 | sofa | 53,683 |
| room_0 | obj_9 | sofa | 47,762 |
| room_0 합계 | | | **151,285** |
| office_0 | obj_58 | table | 32,030 |
| office_0 | obj_61 | chair | 43,916 |
| office_0 | obj_7 | sofa | 35,493 |
| office_0 | obj_9 | sofa | 45,382 |
| office_0 합계 | | | **156,821** |

Phase 1-3의 oracle exact prior는 object당 균일 25K (총 100K)였다. Surface-trained prior는 object마다 다르며 총 ~150K이므로, Phase 5에서는 object별 총량에 비례해 서브샘플링한다.

- `100K` 실험: 각 object에서 대략 자신의 총 Gaussian 수의 `2/3`를 삽입
- `25K` 실험: 각 object에서 대략 자신의 총 Gaussian 수의 `1/6`을 삽입

실제 구현은 scene별 총 Gaussian 수 대비 목표 총량(`100000`, `25000`)을 기준으로 비례 배분하고, 반올림 오차는 deterministic quota 보정으로 맞춘다.

---

## Phase 1-3 참조 데이터 (점 기반, 버그 영향 하)

> 아래 수치는 metadata indexing 버그의 영향을 받은 결과이므로, 직접 비교보다는 **대략적 참조**로 사용한다.

### Room_0

| 조건 | iter_0 | iter_3000 | final (15000) | SSIM |
|------|-------:|----------:|--------------:|-----:|
| baseline (from-scratch) | 8.142 | 10.325 | 12.234 | 0.614 |
| A 25K (none) | 8.100 | 10.561 | 12.290 | 0.616 |

### Office_0

| 조건 | iter_0 | iter_3000 | final (15000) | SSIM |
|------|-------:|----------:|--------------:|-----:|
| baseline (from-scratch) | 9.029 | 10.034 | 12.177 | 0.609 |
| A 25K (none) | 8.997 | 10.122 | 12.253 | 0.614 |

---

## 실험 설계

### 공통 조건

- **Dataset:** `replica_multi_roomwide_v2_384_surface_rgb_shared.yaml`
- **Scenes:** room_0, office_0
- **Iteration:** 15,000
- **Backend:** vanilla 3DGS (동일)
- **Prior library:** `replica_target_surface_exact_trained_clip`
- **Retrieval:** same_scene_exact (oracle)

### 실험 목록

| # | 실험 | 설명 | 목적 |
|---|------|------|------|
| 0 | **Baseline** | surface RGB에서 from-scratch 3DGS | 새 기준선 확보 |
| 1 | **Prior 전체 삽입** | surface-trained prior 전체 삽입 (서브샘플링 없음) | prior 효과 상한 |
| 2 | **Prior 100K** | 100K 서브샘플링, protection 기본값 | Phase 1-3 full 조건과 총량 맞춘 비교 |
| 3 | **A 25K** | 25K 서브샘플링, protection 기본값 | Phase 1-3 최선 정책 재현 |
| 4 | **A 25K (full_none)** | 25K, 보호 완전 해제 (lr_scale=1.0, prune/densify OFF) | Phase 3 결론 재확인 |

### 실험 0: Baseline (from-scratch)

Phase 1-3의 baseline config를 dataset만 변경하여 사용.

```yaml
experiment_name: gaussian_direct_surface_rgb_baseline_15000
dataset_config: replica_multi_roomwide_v2_384_surface_rgb_shared.yaml
backend:
  type: vanilla_3dgs
  iterations: 15000
initialization: from_scratch
```

**이 실험이 가장 중요하다.** Surface RGB baseline PSNR이 점 기반(room_0: 12.234, office_0: 12.177)과 얼마나 다른지가 이후 모든 비교의 기준이 된다.

### 실험 1: Prior 전체 삽입 (서브샘플링 없음)

```yaml
experiment_name: gaussian_direct_surface_rgb_prior_full_15000
prior_library: replica_target_surface_exact_trained_clip.yaml
prior_target_total_gaussians: 0    # 전체 사용 (~150K)
```

Phase 1-3에서는 100K 전체 삽입 실험이 있었다. Surface prior는 ~150K이므로 규모가 비슷하다.

### 실험 2: Prior 100K (기본 protection)

```yaml
experiment_name: gaussian_direct_surface_rgb_prior_100k_15000
prior_library: replica_target_surface_exact_trained_clip.yaml
prior_target_total_gaussians: 100000
# protection: 기본값 (lr_scale=0.05, prune/densify ON)
```

이 실험은 `prior full`과 `A 25K` 사이의 중간점이면서, 총량 기준으로는 Phase 1-3의 `100K exact prior`와 가장 직접적으로 비교된다.

### 실험 3: A 25K (기본 protection)

```yaml
experiment_name: gaussian_direct_surface_rgb_prior_25k_15000
prior_library: replica_target_surface_exact_trained_clip.yaml
prior_target_total_gaussians: 25000
# protection: 기본값 (lr_scale=0.05, prune/densify ON)
```

Phase 1-3의 최선 정책과 **동일한 설정**을 surface RGB에 적용. 핵심 비교 실험.

### 실험 4: A 25K (full_none)

```yaml
experiment_name: gaussian_direct_surface_rgb_prior_25k_full_none_15000
prior_library: replica_target_surface_exact_trained_clip.yaml
prior_target_total_gaussians: 25000
prior_lr_scale: 1.0
protect_prior_from_prune: false
protect_prior_from_densify: false
```

Phase 3에서 protection이 무관함을 확인했으나, 그 결과는 버그 영향 하. 수정된 코드로 재검증.

---

## 실행 순서

```
실험 0: Baseline         ← surface RGB 기준선 (최우선)
    ↓
실험 1: Prior 전체 삽입   ← prior 효과 상한 확인
    ↓
실험 2: Prior 100K       ← 총량 맞춘 공정 비교
    ↓
실험 3: A 25K            ← Phase 1-3 최선 정책 재현
    ↓
실험 4: A 25K full_none  ← protection 무관성 재확인
```

실험 0 결과가 나오면 즉시 점 기반 baseline과 비교하여 surface RGB 전환의 영향 크기를 판단한다.

---

## 예상 시나리오 및 판단 기준

### 시나리오 1: Surface baseline >> 점 기반 baseline

> Surface baseline PSNR이 점 기반보다 2+ dB 높음

**해석:** 점 기반 sparse 이미지의 빈 공간이 reconstruction 품질을 크게 제한하고 있었음. Surface RGB가 훨씬 현실적인 실험 조건.

**Prior 영향 예측:** Prior 기여가 상대적으로 줄어들 가능성 (baseline이 이미 충분히 좋으면 prior 추가 효과 감소).

### 시나리오 2: Surface baseline ≈ 점 기반 baseline

> PSNR 차이 < 0.5 dB

**해석:** 렌더링 방식이 최종 reconstruction 품질에 큰 영향을 주지 않음. 3DGS가 sparse input에도 robust함.

**Prior 영향 예측:** Prior 기여도 유사할 가능성 높음.

### 시나리오 3: Prior 기여가 surface에서 더 큼

> Prior 삽입 효과 (baseline 대비 delta)가 점 기반 +0.056 dB보다 큼

**해석:** Dense 이미지에서 prior가 더 정확하게 활용됨. 점 기반 빈 공간이 prior 효과를 왜곡하고 있었음.

**다음 단계:** Surface RGB를 표준 실험 조건으로 확정.

### 시나리오 4: Prior 기여가 surface에서 사라짐

> Prior 삽입이 baseline과 동등하거나 악화

**해석:** 점 기반 빈 공간이 prior에 유리하게 작용했을 가능성. Dense 이미지에서는 SfM + densification만으로 충분.

**다음 단계:** Prior의 가치를 재평가. View 수 감소 실험(96/192)으로 data-scarce 조건에서의 prior 효과 재확인.

---

## 확인할 지표

1. **iter_0 / iter_3000 / final PSNR** — 수렴 곡선 비교
2. **SSIM / LPIPS** — PSNR과 교차 확인 (surface 이미지는 perceptual metric에서 다르게 나올 수 있음)
3. **Gaussian count** — surface prior 삽입 후 primitive 수 변화
4. **Object별 삽입 수 / 생존 수 / 생존율** — object별 `inserted_count`, `survived_count`, `survived_count / inserted_count`
5. **metadata.json 검증** — 버그 수정 확인 (4개 object가 서로 다른 metadata를 갖는지)
6. **점 기반 vs surface delta** — 동일 조건의 baseline 대비 상대 개선폭 비교
7. **absolute PSNR** — 절대값도 그대로 보고서에 남기되, 결론의 주 해석은 baseline 대비 delta로 한다

### Object별 quota와 생존율 기록 방식

- `100K` 실험: object별 삽입 수는 각 object 총 Gaussian 수의 대략 `2/3`
- `25K` 실험: object별 삽입 수는 각 object 총 Gaussian 수의 대략 `1/6`
- 보고서에는 object별로 아래를 모두 남긴다.
  - `original_count`
  - `inserted_count`
  - `survived_count @3000`
  - `survived_count @15000`
  - `survival_ratio @3000 = survived / inserted`
  - `survival_ratio @15000 = survived / inserted`

---

## 생성할 Config 파일

| 파일명 | 기반 |
|--------|------|
| `gaussian_direct_surface_rgb_baseline_15000.yaml` | baseline config, dataset만 변경 |
| `gaussian_direct_surface_rgb_prior_full_15000.yaml` | prior 전체 삽입, target_total=0 |
| `gaussian_direct_surface_rgb_prior_100k_15000.yaml` | prior 100K, target_total=100000 |
| `gaussian_direct_surface_rgb_prior_25k_15000.yaml` | A 25K, 기본 protection |
| `gaussian_direct_surface_rgb_prior_25k_full_none_15000.yaml` | A 25K, protection 완전 해제 |

---

## Smoke Test

본 실험 전에 1000-iter smoke test로 파이프라인 동작을 확인한다:

```yaml
gaussian_direct_surface_rgb_baseline_smoke_1000.yaml
gaussian_direct_surface_rgb_prior_100k_smoke_1000.yaml
gaussian_direct_surface_rgb_prior_25k_smoke_1000.yaml
```

확인 사항:
- Surface RGB 이미지가 올바르게 로드되는지
- Surface-trained prior가 올바르게 삽입되는지
- **metadata.json에 4개 서로 다른 object가 기록되는지** (버그 수정 검증)
- iter_0 렌더링에서 4개 object 위치에 모두 삽입 흔적이 보이는지

### Smoke Test Pass 조건

- `baseline`, `prior_100k`, `prior_25k` smoke run이 모두 정상 종료될 것
- `prior_init/metadata.json`에 서로 다른 4개 object가 기록될 것
- `prior_init/aligned_prior_*.ply`가 4개 생성될 것
- object별 `inserted_count`가 기록될 것
- `iter_0` 산출물에서 4개 object 중심 근처에 prior Gaussian이 실제 존재할 것
- object별 prior range 또는 object별 grouping 정보가 후속 보고서에서 추적 가능할 것

---

## B / C 후속 조건

Phase 5 1차 실험에는 B(`replace_region`)와 C(`sh_zero`)를 포함하지 않는다. 대신 아래 조건에서만 후속 실험으로 연다.

- **B 우선 재도입 조건**
  - `prior_full`, `prior_100k`, `prior_25k` 중 하나라도 `iter_0`에서 baseline보다 뚜렷하게 나쁘고
  - geometry는 맞는데 prior 주변에서 base Gaussian과의 중복/간섭이 시각적으로 보일 때
- **C 재도입 조건**
  - geometry는 맞지만 color/appearance mismatch가 유독 강하게 보일 때
  - 특히 `iter_0`에서 prior 위치의 색감만 어색하고 shape는 맞을 때
- **B/C 생략 조건**
  - `prior_25k` 또는 `prior_100k`가 baseline 대비 안정적인 delta를 보이면 추가 진단 없이 표준 조건으로 채택

---

## 참고: Phase 1-3와의 공정한 비교에 대하여

Phase 5 실험과 Phase 1-3 결과를 직접 비교할 때 주의할 점:

1. **이미지가 다르므로 PSNR 절대값 비교는 의미 없음** — 비교 대상은 각각의 baseline 대비 delta
2. **Prior 소스가 다름** — Phase 1-3은 scene에서 직접 추출(oracle exact), Phase 5는 surface RGB로 재학습
3. **Phase 1-3 결과는 metadata 버그 영향** — delta 비교 시에도 이 점을 감안
4. **동일한 것은 camera pose, scene geometry, object 선택** — 통제된 비교 가능

따라서 비교의 핵심은 "baseline 대비 prior 삽입의 **상대적 개선폭**이 이미지 품질에 따라 어떻게 변하는가"이다.
