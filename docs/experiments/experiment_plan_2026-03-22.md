# Gaussian-Direct 실험 계획 (수정)

Date: 2026-03-22

이전 계획: `docs/experiments/experiment_plan_2026-03-21.md`

---

## 계획 변경 경위

### 03-21 계획의 진행 상태

| Phase | 내용 | 상태 |
|-------|------|------|
| Phase 1 | Protection sweep 확장 (weak/freeze, 96-view/384-view) | 완료 |
| Phase 2 | Room-wide view 데이터셋 구축 및 실험 | 완료 (v1 legacy + v2) |
| Phase 3 | `prior_lr_scale` sweep | **미진행** |
| Phase 4 | 실험 정리 및 아카이브 | 미진행 |
| Phase 5 | 면 기반 surface rendering 전환 | 미진행 |

### Phase 2 수행 중 발견된 문제

Phase 2 (room-wide v2) 실험 결과를 분석하면서 두 가지 이상 현상이 확인됐다.

**1. TTT 스파이크 (체크포인트 granularity 문제)**

일부 실험에서 `time_to_target_sec`이 비정상적으로 높게 측정됐다. 원인은 체크포인트 간격이 `..., 3000, 5000, ...`으로 3000에서 target PSNR을 근소하게 미달하면 다음 판정이 iter 5000까지 밀리는 것. 실제 성능 차이가 아닌 측정 해상도 문제다.

| 실험 | scene | iter_3000 psnr | target_psnr | 차이 | TTT |
|------|-------|---:|---:|---:|---:|
| v2_192 weak | room_0 | 10.469 | 10.533 | -0.064 | 234.81s |
| v2_192 none | office_0 | 10.446 | 10.474 | -0.028 | 273.71s |
| v2_192 weak | office_0 | 10.383 | 10.474 | -0.091 | 261.00s |

> **주의:** TTT(time_to_target_sec)는 현재 단계의 간섭 진단 실험에서 판단 지표로 사용하지 않는다. 체크포인트 granularity에 의한 노이즈가 크고, 현재 실험의 핵심 질문은 "간섭이 최적화를 방해하는가"이지 "얼마나 빨리 수렴하는가"가 아니다. TTT는 삽입 정책이 확정된 이후 Phase 3에서 다시 검토한다. 실험 결과를 해석할 때 TTT 수치에 의존하지 말 것.

**2. iter_0에서 baseline > prior PSNR (gaussian 간섭)**

Oracle exact prior(동일 객체를 정확한 위치에 삽입)임에도, iter_0에서 prior 삽입 조건의 PSNR이 baseline보다 **모든 조건에서 일관되게 ~0.13dB 낮았다.**

| scene | views | baseline iter_0 PSNR | prior iter_0 PSNR | 차이 |
|-------|---:|---:|---:|---:|
| room_0 | 96 | 8.112 | 7.973 | -0.139 |
| room_0 | 192 | 8.193 | 8.064 | -0.129 |
| room_0 | 384 | 8.142 | 8.012 | -0.131 |
| office_0 | 96 | 9.172 | 9.019 | -0.153 |
| office_0 | 192 | 9.116 | 8.982 | -0.134 |
| office_0 | 384 | 9.029 | 8.896 | -0.133 |

단서: SSIM은 prior가 baseline과 동등하거나 약간 높음 → 구조적 유사도는 유지되면서 per-pixel 색상 오차만 증가.

### 원인 가설

두 가지가 동시에 작용한다고 판단:

1. **SH coefficient view 불일치** — prior의 SH가 학습 뷰에 최적화되어 있어, 평가 뷰에서 색상이 부정확함. SH 표현의 고유한 일반화 한계이며, prior 학습 자체의 문제는 아님.

2. **Prior gaussian과 SfM point의 간섭** — merge 모드에서 prior 100K를 SfM 100K 위에 추가하면, 같은 영역에 학습된 gaussian과 초기화된 gaussian이 이중 렌더링되면서 색상 간섭 발생.

### 계획 변경 결정

간섭이 근본 원인이라면 `lr_scale`을 아무리 튜닝해도 한계가 있다. 따라서 **Phase 3 (lr_scale sweep)을 보류**하고, 간섭 원인을 진단하는 실험을 먼저 진행한다. 진단 결과에 따라 Phase 3 이후의 방향을 재결정한다.

---

## 간섭 진단 실험

### 목적

Prior gaussian과 SfM gaussian의 간섭이 최적화 성능에 얼마나 영향을 주는지 분리하여 측정한다.

### 공통 조건

- **Dataset:** room-wide v2 384-view (`replica_colmap_multi_roomwide_v2_384`)
- **Scene:** `room_0` 우선 진행. 유의미한 결과 시 `office_0` 확장
- **Iteration:** 15000 (기존과 동일)
- **비교 기준:** v2 384-view baseline 및 기존 unprotected/weak 결과

기존 비교 대상 (v2 384-view room_0):

| 조건 | iter_0 PSNR | psnr@3000 | final PSNR | gaussians@0 |
|------|---:|---:|---:|---:|
| baseline | 8.142 | 10.325 | 12.234 | 100K |
| prior none | 8.012 | 10.487 | 12.270 | 200K |
| prior weak(0.02) | 8.012 | 10.487 | 12.195 | 200K |

### 실험 A: Prior Gaussian 수 조절

**가설:** Prior gaussian 수를 줄이면 간섭이 감소하여 iter_0 PSNR이 회복되고 최적화 성능이 개선된다.

**방법:** 기존 prior를 랜덤 서브샘플링하여 삽입 수를 조절한다.

| 조건 | prior 수 | SfM 수 | 총 gaussians@0 | protection |
|------|---:|---:|---:|---|
| prior_25k | 25,000 | 100,000 | 125,000 | none |
| prior_50k | 50,000 | 100,000 | 150,000 | none |
| prior_25k_weak | 25,000 | 100,000 | 125,000 | weak(0.02) |
| prior_50k_weak | 50,000 | 100,000 | 150,000 | weak(0.02) |

**확인할 것:**
- iter_0 PSNR이 baseline에 가까워지는가
- prior 수 감소에 따른 iter_0 / iter_3000 / final PSNR 변화 패턴
- prior 수와 간섭 정도가 선형적 관계인가

**구현:** `scripts/run_experiment.py`의 prior 로딩 단계에서 서브샘플링 파라미터 추가. 또는 prior PLY를 사전에 서브샘플링한 버전 생성.

### 실험 B: Prior 영역 SfM Point 제거

**가설:** 간섭의 주 원인이 같은 공간에서 SfM과 prior가 중첩되는 것이라면, prior가 커버하는 영역의 SfM point를 제거하면 간섭이 사라진다.

**방법:** Prior gaussian의 bounding box(또는 일정 반경) 안에 있는 SfM point를 제거한 뒤 prior를 삽입한다.

| 조건 | prior 수 | SfM 처리 | 총 gaussians@0 (추정) | protection |
|------|---:|---|---:|---|
| replace_region | 100,000 | bbox 내 SfM 제거 | ~150K–180K | none |
| replace_region_weak | 100,000 | bbox 내 SfM 제거 | ~150K–180K | weak(0.02) |

**확인할 것:**
- iter_0 PSNR이 baseline 수준으로 회복되는가
- SfM 제거로 배경 영역의 quality가 떨어지지 않는가
- 간섭 제거 후 prior 삽입이 iter별 PSNR 수렴 곡선에서 이점을 주는가

**구현:** `scripts/train_vanilla_3dgs_backend.py`의 merge 단계에서 prior bounding box 계산 → SfM point filtering 로직 추가. Prior별 bounding box는 prior PLY의 xyz min/max에 margin을 더해 계산.

### 실험 C: Prior SH 리셋

**가설:** iter_0 PSNR 하락의 주 원인이 SH mismatch라면, SH만 리셋하고 geometry를 유지하면 iter_0 PSNR이 회복된다.

**방법:** Prior gaussian의 xyz, opacity, scale, rotation은 유지하고 SH 계수만 초기 상태(0차만 유지 또는 SfM 기본값)로 리셋한 뒤 삽입한다.

| 조건 | geometry | SH | protection |
|------|----------|-----|---|
| sh_reset | prior 유지 | 0차만 유지 (DC term) | none |
| sh_reset_weak | prior 유지 | 0차만 유지 (DC term) | weak(0.02) |

**확인할 것:**
- iter_0 PSNR이 baseline 수준으로 회복되는가 → SH가 주범 확인
- 회복되지 않는다면 → 간섭(가설 2)이 주 원인
- SH 리셋 후에도 geometry 정보만으로 prior 효과(TTT 개선)가 나타나는가

**구현:** Prior PLY 로딩 후 SH 계수 배열에서 0차(DC) 이외 계수를 0으로 리셋. `src/priorprobe/gaussian_affine.py` 또는 prior 로딩 유틸에 `reset_sh_to_dc()` 함수 추가.

### 실험 실행 순서

```
실험 C (SH 리셋)     ← 구현이 가장 간단, 원인 분리 효과 높음
    ↓
실험 B (SfM 제거)    ← 간섭 가설 직접 테스트
    ↓
실험 A (Prior 수 조절) ← 간섭 정도의 연속적 변화 확인
```

C를 먼저 하는 이유: SH 리셋만으로 iter_0 PSNR이 회복되면 간섭보다 SH가 주 원인임을 빠르게 확인 가능. 회복되지 않으면 B로 넘어가 간섭 가설을 테스트.

### 판단 기준

| 결과 패턴 | 해석 | 다음 단계 |
|----------|------|----------|
| C에서 iter_0 PSNR 회복 | SH mismatch가 주 원인 | SH 리셋을 기본 삽입 정책에 포함하고 Phase 3 진행 |
| C 효과 없음 + B에서 회복 | gaussian 간섭이 주 원인 | SfM 제거를 기본 삽입 정책에 포함하고 Phase 3 진행 |
| C + B 모두 효과 없음 | 두 가설 모두 아님 | 다른 원인 탐색 (opacity 리셋, prior alignment 재검증 등) |
| A에서 prior 수 감소 시 점진적 개선 | 간섭이 밀도에 비례 | 최적 prior 밀도 탐색으로 전환 |

---

## 이후 실험 (간섭 진단 완료 후)

간섭 진단 결과를 반영하여 삽입 정책을 확정한 뒤, 이전 계획의 Phase 3 이후를 순차 진행한다.

- **Phase 3:** `prior_lr_scale` sweep — 확정된 삽입 정책 위에서 lr_scale 최적화
- **Phase 4:** 실험 정리 및 HDD 아카이브
- **Phase 5:** 면 기반 surface rendering 이미지로 전환

각 Phase의 상세 내용은 `docs/experiments/experiment_plan_2026-03-21.md`를 참조한다.
