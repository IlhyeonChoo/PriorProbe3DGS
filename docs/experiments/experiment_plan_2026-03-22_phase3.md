# 재정의된 Phase 3: Protection 완전 해제 실험

Date: 2026-03-22

이전 계획:
- `docs/experiments/experiment_plan_2026-03-22.md` (간섭 진단)
- `docs/experiments/experiment_plan_2026-03-22_v2.md` (간섭 완화 조합)

---

## 배경

### 진단 및 조합 실험 결과 요약

간섭 진단 실험(A/B/C)과 조합 실험(A+B, A+C, A+B+C)을 room_0 v2 384-view에서 완료했다.

상세 수치:
- `docs/experiments/replica_gaussian_direct_interference_diagnosis_room_0_2026-03-22.md`
- `docs/experiments/replica_gaussian_direct_interference_combinations_room_0_2026-03-22.md`

핵심 결과:

| label | protection | iter_0 PSNR | iter_3000 PSNR | final PSNR |
|-------|-----------|---:|---:|---:|
| baseline | - | 8.142 | 10.325 | 12.234 |
| prior 100K | none | 8.012 | 10.487 | 12.270 |
| **A 25K** | **none** | **8.100** | **10.561** | **12.290** |
| A+C | none | 8.150 | 10.566 | 12.279 |
| A+C | weak(0.02) | 8.150 | 10.437 | 12.267 |
| A+B | none | 8.137 | 10.484 | 12.233 |
| A+B+C | none | 8.081 | 10.477 | 12.290 |

### 확인된 사실

1. **A 25K(none)이 단독 최선** — 서브샘플링만으로 충분, 추가 처리(SH 리셋, SfM 제거)는 final PSNR을 개선하지 못함
2. **none > weak 일관적** — 모든 조합에서 none이 weak보다 좋음
3. **조합 효과는 가산적이 아님** — 간섭 완화 간 상호 상쇄 발생 (특히 A+B)

### 현재 "none"의 실제 설정

기존 모든 실험에서 `none`으로 표기한 조건의 실제 backend 설정:

```yaml
prior_protection_mode: none      # (기본값)
prior_lr_scale: 0.05             # prior gaussian의 lr이 정상의 5%
protect_prior_from_prune: true   # prior는 pruning에서 보호됨
protect_prior_from_densify: true # prior는 densification에서 보호됨
```

즉 현재 "none"은 **lr만 5%로 제한하고 prune/densify 보호는 켜져 있는** 상태다. 완전한 보호 해제가 아니다.

### Phase 3 재정의 이유

원래 Phase 3는 "weak protection 기반 lr_scale sweep"이었으나, weak가 폐기되면서 의미가 사라졌다. 대신 다음 질문에 답하는 것이 더 가치 있다:

- lr_scale을 0.05보다 높이면 (0.1, 1.0) 어떻게 되는가?
- prune/densify 보호를 완전히 해제하면 어떻게 되는가?
- prior gaussian에 일반 gaussian과 완전히 동일한 자유도를 주면?

---

## 실험 조건

### 공통 조건

- **Dataset:** room-wide v2 384-view (`replica_colmap_multi_roomwide_v2_384`)
- **Scene:** `room_0`
- **Iteration:** 15000
- **Prior budget:** 25,000 (A 25K 기본)
- **SH reset:** none (원본 SH 유지)
- **SfM replacement:** none

> **주의:** TTT(time_to_target_sec)는 이번 실험에서도 판단 지표로 사용하지 않는다.

### 실험 조건

| # | label | config 파일 | lr_scale | prune 보호 | densify 보호 | 의미 |
|---|-------|------------|---:|---|---|------|
| 기준 | A 25K (현재) | `*_prior_25k_15000.yaml` | 0.05 | ON | ON | 현재 최선 |
| 1 | lr_0.1 | `*_prior_25k_lr01_15000.yaml` | 0.1 | ON | ON | prior 적응 2배 |
| 2 | lr_1.0 | `*_prior_25k_lr10_15000.yaml` | 1.0 | ON | ON | prior lr = 일반 gaussian |
| 3 | full_none | `*_prior_25k_full_none_15000.yaml` | 1.0 | OFF | OFF | 완전한 보호 해제 |

### 각 실험의 의도

**실험 1 (lr_0.1):** 현재 lr_scale 0.05의 2배. prior gaussian이 새 뷰에 더 빨리 적응하지만 원본 geometry 변형도 빨라짐. 0.05 → 0.1로 올렸을 때 final PSNR이 개선되는지, prior 생존율이 변하는지 확인.

**실험 2 (lr_1.0):** prior gaussian의 learning rate를 일반 gaussian과 동일하게 설정. 이 상태에서 prune/densify 보호만 남아있으므로, "prior gaussian은 일반 gaussian과 같은 속도로 학습하지만 삭제/분할되지 않는다"는 조건. lr_scale이 0.05일 때보다 prior가 더 빠르게 변형되어 원본 정보를 잃을 수도 있고, 반대로 빠르게 적응하여 기여할 수도 있음.

**실험 3 (full_none):** 모든 보호를 해제. prior gaussian이 일반 gaussian과 **완전히 동일하게** 취급됨. pruning도 되고 densification(clone/split)도 됨. 지금까지 한번도 테스트하지 않은 조건. 가능한 결과:
- prior gaussian이 densify되면서 오히려 더 많은 gaussian으로 확장 → 기여 증가
- prior gaussian이 빠르게 pruning되어 사라짐 → prior 삽입 효과 소멸
- 또는 일부는 살아남고 일부는 사라지는 자연선택 → 최적의 균형

### 실행 순서

```
실험 2: lr_1.0       ← lr 효과를 극단적으로 확인
    ↓
실험 1: lr_0.1       ← 중간 지점 (필요시)
    ↓
실험 3: full_none    ← 보호 완전 해제
```

실험 2를 먼저 하는 이유: lr_scale을 최대로 올렸을 때 결과가 좋으면 중간 값(0.1)은 참고용으로만 돌리면 됨. 나쁘면 0.1이 의미 있는 중간 지점이 됨.

실험 3을 마지막에 하는 이유: prune/densify 보호 해제는 가장 급진적인 변경이므로, lr 효과를 먼저 이해한 뒤 진행.

---

## 비교 기준

### 기준점

| 조건 | iter_0 PSNR | iter_3000 PSNR | final PSNR | prior@3K | prior@15K (생존율) |
|------|---:|---:|---:|---:|---:|
| baseline | 8.142 | 10.325 | 12.234 | - | - |
| A 25K (현재 none) | 8.100 | 10.561 | 12.290 | 24396 | 18143 (73%) |
| prior 100K (none) | 8.012 | 10.487 | 12.270 | 94809 | 64287 (64%) |

### 확인할 지표

1. **iter_0 / iter_3000 / final PSNR** — 수렴 곡선 전체
2. **Prior 생존율** — 특히 full_none에서 prior가 얼마나 남는지
3. **Prior densification** — full_none에서 prior gaussian이 clone/split되어 증가하는지
4. **Total gaussian count** — full_none에서 densify 허용 시 총 primitive 수 변화

---

## 판단 기준

| 결과 패턴 | 해석 | 다음 단계 |
|----------|------|----------|
| lr_1.0 > A 25K(현재) | lr 제한이 prior 적응을 방해하고 있었음 | lr_1.0을 기본 정책으로 채택, full_none 결과 확인 후 최종 결정 |
| lr_1.0 ≈ A 25K(현재) | lr_scale은 0.05 이상이면 큰 차이 없음 | 현재 설정 유지, full_none 결과로 최종 결정 |
| lr_1.0 < A 25K(현재) | lr 제한이 prior 보존에 도움 | 0.05가 적절한 lr_scale, full_none은 더 나쁠 가능성 높음 |
| full_none > 모든 조건 | 보호 자체가 불필요, prior에 최대 자유도가 최적 | full_none을 기본 정책으로 확정 |
| full_none에서 prior 전멸 | 보호 없으면 prior가 최적화 과정에서 제거됨 | prune/densify 보호는 유지하되 lr만 조정 |
| full_none에서 prior densify → 수 증가 | prior geometry가 씨앗으로 작용해 확장됨 | 매우 흥미로운 결과 → densify 허용 + prune 보호 조합 추가 테스트 |

---

## 이후 실험 (Phase 3 완료 후)

Phase 3 결과로 최종 삽입 정책(prior budget, lr_scale, prune/densify protection)을 확정한 뒤:

1. **office_0 교차 검증** — 확정된 최종 정책 1~2개만 room_0과 동일 조건에서 실행
2. **50K 확장** (필요시) — 최종 정책에서 prior budget을 25K → 50K로 올렸을 때 효과 확인
3. **Phase 4:** 실험 정리 및 아카이브
4. **Phase 5:** 면 기반 surface rendering 이미지로 전환

각 Phase의 상세 내용은 `docs/experiments/experiment_plan_2026-03-21.md`를 참조한다.
