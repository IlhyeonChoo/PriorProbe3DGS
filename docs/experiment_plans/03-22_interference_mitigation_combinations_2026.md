# Gaussian-Direct 간섭 완화 조합 실험 계획

Date: 2026-03-22

이전 계획: `docs/experiment_plans/03-22_interference_diagnosis_2026.md` (간섭 진단 실험)

---

## 배경: 진단 실험 결과 요약

### 간섭 진단 실험 (A/B/C) 결과

`docs/experiment_results/03-22_interference_diagnosis_room_0_2026.md` 참조.

공통 조건: v2 384-view, room_0, 15000 iter.

| label | protection | iter_0 PSNR | iter_3000 PSNR | final PSNR | gaussians@0 |
|-------|-----------|---:|---:|---:|---:|
| baseline | - | 8.142 | 10.325 | 12.234 | 100K |
| prior 100K | none | 8.012 | 10.487 | 12.270 | 200K |
| prior 100K | weak(0.02) | 8.012 | 10.487 | 12.195 | 200K |
| **A prior_25k** | **none** | **8.100** | **10.561** | **12.290** | 125K |
| A prior_50k | none | 8.067 | 10.561 | 12.294 | 150K |
| A prior_25k | weak(0.02) | 8.100 | 10.410 | 12.195 | 125K |
| A prior_50k | weak(0.02) | 8.067 | 10.361 | 12.110 | 150K |
| B replace_region | none | 8.171 | 10.561 | 12.254 | 183K |
| B replace_region | weak(0.02) | 8.171 | 10.420 | 12.126 | 183K |
| C sh_zero | none | 8.139 | 10.442 | 12.261 | 200K |
| C sh_zero | weak(0.02) | 8.139 | 10.548 | 12.247 | 200K |

### 확인된 사실

1. **세 가지 간섭 원인이 모두 유효하다**
   - C(SH 리셋): iter_0 PSNR 97% 회복 → SH mismatch 확인
   - B(SfM 제거): iter_0 PSNR 122% 회복 (baseline 초과) → 공간 중첩 확인
   - A(prior 수 감소): iter_0 PSNR 68% 회복(25K), 42%(50K) → 밀도 비례 간섭 확인

2. **`none` protection이 `weak`를 일관되게 이긴다**
   - none은 방해되는 prior를 자연 pruning → 유용한 것만 남음
   - weak는 방해꾼까지 강제 보존 → 간섭 지속
   - 유일한 예외: C sh_zero에서 weak(10.548) > none(10.442) at iter_3000
     - SH 리셋 시 geometry 보존이 SH 재학습을 도움

3. **A prior_25k(none)이 단독 실험 중 가장 좋은 균형**
   - iter_3000: 10.561 (최고 그룹)
   - final: 12.290 (baseline +0.056, prior 100K none과 비슷)
   - prior 생존: 25K → 18143 (73%)

### 아직 확인되지 않은 것

- A, B, C를 조합했을 때 효과가 가산적(additive)인지, 중복적(redundant)인지
- 조합 후에도 none > weak 패턴이 유지되는지 (특히 SH 리셋 조합에서)
- 25K에서 확인된 패턴이 50K에서도 동일한지

---

## 조합 실험 계획

### 목적

간섭 완화 처리 A(prior 수 감소), B(SfM 제거), C(SH 리셋)를 조합하여 최적 삽입 정책을 탐색한다.

### 공통 조건

- **Dataset:** room-wide v2 384-view (`replica_colmap_multi_roomwide_v2_384`)
- **Scene:** `room_0`
- **Iteration:** 15000
- **Prior budget:** 25,000 (25K) — 단독 실험에서 가장 좋았던 설정
- **비교 기준:** baseline, A prior_25k(none), 진단 실험 전체

> **주의:** TTT(time_to_target_sec)는 이번 실험에서도 판단 지표로 사용하지 않는다. 체크포인트 granularity 문제가 미해결이며, 현재 핵심 질문은 "어떤 조합이 간섭을 가장 효과적으로 줄이는가"이다.

### 실험 조건

#### 실험 1: A+B (25K + SfM 제거, none)

- **처리:** prior를 25K로 서브샘플링 + prior AABB 내 SfM point 제거
- **Protection:** none
- **기대:** prior 밀도 감소와 공간 분리가 동시에 적용되어 iter_0 간섭 최소화
- **확인할 것:**
  - iter_0 PSNR이 B 단독(8.171)이나 A 단독(8.100)보다 높아지는가
  - SfM 제거 + prior 감소로 총 gaussian@0이 크게 줄어드는데, 이것이 final PSNR에 미치는 영향
  - SfM 제거 범위: 25K prior의 AABB는 100K보다 작을 수 있음 → 제거되는 SfM 수 확인

#### 실험 2: A+C (25K + SH 리셋, none)

- **처리:** prior를 25K로 서브샘플링 + SH 계수 전부 0으로 리셋
- **Protection:** none
- **기대:** prior 밀도 감소 + 색상 간섭 제거 → geometry 기여만 순수 측정
- **확인할 것:**
  - SH 리셋 + 밀도 감소가 iter_0 PSNR을 baseline 수준까지 회복시키는가
  - C 단독에서 none이 iter_3000에서 약했는데(10.442), 25K로 줄이면 개선되는가
  - prior 생존율: C 단독 none은 50%만 생존 → 25K에서는 비율이 달라지는가

#### 실험 3: A+B+C (25K + SfM 제거 + SH 리셋, none)

- **처리:** 세 가지 간섭 완화를 모두 적용
- **Protection:** none
- **기대:** 이론적 최소 간섭 조건 → prior의 geometry 기여가 가장 깨끗하게 드러남
- **확인할 것:**
  - 세 처리의 효과가 가산적인가 (iter_0 PSNR이 각 단독보다 높은가)
  - 과도한 간섭 제거가 prior 기여 자체를 줄이지는 않는가 (final PSNR 확인)
  - 단독 최고(A 25K none, 12.290) 대비 개선이 있는가

#### 실험 4: A+C (25K + SH 리셋, weak)

- **처리:** prior를 25K로 서브샘플링 + SH 계수 전부 0으로 리셋
- **Protection:** weak(0.02)
- **근거:** C 단독에서 유일하게 weak > none이었음 (iter_3000: 10.548 vs 10.442). SH를 리셋하면 prior가 geometry만 가진 "빈 캔버스" 상태가 되는데, weak가 geometry를 보존하면서 SH 재학습만 허용하는 효과. 25K로 줄이면 weak의 단점(방해꾼 강제 보존)도 경감
- **확인할 것:**
  - C 단독에서 관찰된 weak > none 패턴이 25K에서도 재현되는가
  - A+C(none) 대비 iter_3000 / final PSNR 차이
  - SH가 리셋된 상태에서 weak의 geometry 보존이 실제로 도움이 되는가

### 실험 조건 요약

| # | label | prior_budget | sfm_replace | sh_reset | protection | 기대 총 gaussians@0 |
|---|-------|---:|---|---|---|---:|
| 1 | A+B | 25K | aligned_prior_aabb_union | none | none | ~109K (추정) |
| 2 | A+C | 25K | none | zero_all | none | 125K |
| 3 | A+B+C | 25K | aligned_prior_aabb_union | zero_all | none | ~109K (추정) |
| 4 | A+C weak | 25K | none | zero_all | weak(0.02) | 125K |

> **총 gaussians@0 추정 (실험 1, 3):** 진단 실험 B에서 100K prior 시 SfM 16420개가 제거됨 (100K → 83580). 25K prior의 AABB가 더 작을 수 있으므로 제거 SfM 수는 줄어들 가능성 있음. 실제 값은 실행 시 확인.

### 실행 순서

```
실험 2: A+C (none)     ← C 단독에서 none이 약했던 패턴이 25K로 바뀌는지 확인
실험 4: A+C (weak)     ← 동일 조건에서 protection 효과 비교
    ↓
실험 1: A+B (none)     ← 공간 분리 + 밀도 감소의 조합 효과
    ↓
실험 3: A+B+C (none)   ← 전체 조합
```

실험 2와 4를 먼저 하는 이유: A+C 조합이 "SH 리셋 + 밀도 감소"라는 가장 순수한 간섭 분리이고, none vs weak 비교가 이 조합에서 가장 흥미로운 결과를 줄 것으로 예상.

---

## 판단 기준

### 비교 기준점

| 조건 | iter_0 PSNR | iter_3000 PSNR | final PSNR | 의미 |
|------|---:|---:|---:|------|
| baseline | 8.142 | 10.325 | 12.234 | prior 없는 기준선 |
| A prior_25k(none) | 8.100 | 10.561 | 12.290 | **현재 단독 최선** |
| prior 100K(none) | 8.012 | 10.487 | 12.270 | 원본 prior 삽입 |

### 결과 해석 기준

| 결과 패턴 | 해석 | 다음 단계 |
|----------|------|----------|
| 조합이 A 25K(none) 단독보다 개선 | 간섭 완화 효과가 가산적 | 최선 조합을 삽입 정책으로 확정, 50K에서도 동일 조합 테스트 |
| 조합이 A 25K(none)과 동등 | 25K 서브샘플링이 이미 충분한 간섭 완화 | A 25K(none)을 기본 정책으로 확정 (가장 단순) |
| A+C(weak)가 A+C(none)보다 나음 | SH 리셋 시 geometry 보존이 중요 | A+C(weak) 또는 A+B+C(weak) 추가 테스트 |
| A+C(weak)가 A+C(none)보다 나쁨 | 25K에서도 none이 일관되게 우세 | weak protection 정책 폐기, none으로 확정 |
| 모든 조합에서 final PSNR < A 25K(none) | 과도한 처리가 prior 기여를 감소시킴 | A 25K(none) 단독이 최적, 불필요한 전처리 제거 |

### 50K 확장 판단

조합 실험 결과에 따라 50K 확장 여부를 결정:

- **확장하는 경우:** 조합이 A 25K 단독보다 유의미한 개선을 보일 때 → 최선 조합을 50K에서 재현 테스트
- **확장하지 않는 경우:** 조합이 25K 단독과 동등하거나 나쁠 때 → 25K로 확정하고 다음 Phase로 진행

---

## 이후 실험 (조합 실험 완료 후)

조합 실험 결과로 삽입 정책(prior budget, SfM 처리, SH 처리, protection)을 확정한 뒤:

1. **50K 확장 테스트** (필요시)
2. **office_0 교차 검증** — room_0에서 확정된 최선 조합이 다른 scene에서도 유효한지
3. **Phase 3 진행:** 확정된 삽입 정책 위에서 `prior_lr_scale` sweep
4. **Phase 4:** 실험 정리 및 아카이브
5. **Phase 5:** 면 기반 surface rendering 이미지로 전환

각 Phase의 상세 내용은 `docs/experiment_plans/03-21_followup_experiments_2026.md`를 참조한다.
