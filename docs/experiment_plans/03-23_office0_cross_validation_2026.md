# Office_0 교차 검증: 간섭 완화 조합 실험

Date: 2026-03-23

이전 계획:
- `docs/experiment_plans/03-22_interference_diagnosis_2026.md` (간섭 진단)
- `docs/experiment_plans/03-22_interference_mitigation_combinations_2026.md` (간섭 완화 조합 — room_0)
- `docs/experiment_plans/03-22_phase3_protection_disabled_2026.md` (Phase 3: protection 해제 — room_0)

---

## 배경

### Room_0에서 확인된 사실

간섭 진단(A/B/C), 조합(A+B, A+C, A+B+C), Phase 3(lr_scale sweep, protection 해제) 실험을 room_0 v2 384-view에서 완료했다.

핵심 결론:

1. **A 25K(none)이 최선의 단일 정책** — 서브샘플링만으로 충분
2. **조합(A+B, A+C, A+B+C)은 A 단독을 개선하지 못함** — 가산적 효과 없음
3. **Protection 설정(lr_scale, prune/densify)은 final PSNR에 거의 무관** — Phase 3에서 0.031 dB 차이
4. **Prior 생존율은 보호 유무와 무관하게 ~73%** — protect_from_prune 해제해도 동일
5. **384-view에서 prior의 final PSNR 기여는 매우 제한적** — baseline 12.234 vs 최선 12.290 (+0.056 dB)

### 교차 검증의 목적

Room_0에서 발견한 패턴이 다른 scene에서도 재현되는지 확인한다:

- **A 25K가 다른 scene에서도 조합보다 좋은가?**
- **A+B(SfM 제거)가 office_0에서도 역효과인가?** (room_0에서는 커버리지 공백 발생)
- **A+C(SH 리셋)가 office_0에서도 iter_0 개선 + final 무효과인가?**
- **Prior 삽입의 absolute 기여 크기가 scene에 따라 다른가?**

### Office_0 기존 결과

| 조건 | iter_0 | iter_3000 | final PSNR | Gaussian count |
|------|---:|---:|---:|---:|
| baseline (from scratch) | 9.029 | 10.034 | 12.177 | 5,301,088 |
| prior 100K (none) | 8.896 | 10.217 | 12.234 | 5,444,376 |

Office_0 특성:
- Baseline iter_0 PSNR이 room_0(8.142)보다 높음 (9.029)
- Prior 100K 삽입 시 final PSNR 기여 +0.057 dB (room_0의 +0.036 dB보다 큼)
- Prior objects: sofa(obj_9), obj_7, obj_58, obj_61 — 4개 오브젝트

---

## 실험 조건

### 공통 조건

- **Dataset:** room-wide v2 384-view (`replica_multi_roomwide_v2_384_shared.yaml`)
- **Scene:** `office_0`
- **Iteration:** 15,000
- **Prior budget:** 25,000 (A 25K)
- **Protection:** none (lr_scale=0.05, prune/densify 보호 ON) — 기본값
- **Init mode:** merge (SfM + prior)

### 실험 목록

| # | label | config 파일 | 설명 |
|---|-------|-------------|------|
| 기준 | baseline | `*_baseline_from_scratch_vanilla_3dgs_multi_roomwide_v2_384_15000.yaml` | **이미 완료** |
| 1 | A 25K | `*_same_scene_exact_clip_roomwide_v2_384_prior_25k_15000.yaml` | 서브샘플링만 적용 |
| 2 | A+C | `*_same_scene_exact_clip_roomwide_v2_384_prior_25k_sh_zero_15000.yaml` | + SH 리셋 |
| 3 | A+B | `*_same_scene_exact_clip_roomwide_v2_384_prior_25k_replace_region_15000.yaml` | + SfM 제거 |
| 4 | A+B+C | `*_same_scene_exact_clip_roomwide_v2_384_prior_25k_replace_region_sh_zero_15000.yaml` | 전체 조합 |

> Config 파일은 room_0 실험과 동일한 것을 사용한다. `--scene office_0`으로 실행 scene만 지정.

### 각 실험의 세부 설정

**실험 1 — A 25K (서브샘플링):**
```yaml
prior_target_total_gaussians: 25000
# SH, SfM: 기본값 (변경 없음)
```

**실험 2 — A+C (서브샘플링 + SH 리셋):**
```yaml
prior_target_total_gaussians: 25000
prior_sh_reset_mode: zero_all
```

**실험 3 — A+B (서브샘플링 + SfM 영역 제거):**
```yaml
prior_target_total_gaussians: 25000
sfm_region_replacement_mode: aligned_prior_aabb_union
```

**실험 4 — A+B+C (서브샘플링 + SfM 영역 제거 + SH 리셋):**
```yaml
prior_target_total_gaussians: 25000
prior_sh_reset_mode: zero_all
sfm_region_replacement_mode: aligned_prior_aabb_union
```

---

## 실행 순서

```
실험 1: A 25K      ← 기준점 확보 (가장 중요)
    ↓
실험 2: A+C        ← SH 리셋 효과 확인
    ↓
실험 3: A+B        ← SfM 제거 효과 확인
    ↓
실험 4: A+B+C      ← 전체 조합
```

실험 1을 먼저 하는 이유: A 25K 결과가 나와야 나머지 조합의 비교 기준이 확보됨. 실험 1 결과가 baseline과 차이 없거나 악화되면 나머지 실험의 필요성을 재검토할 수 있음.

---

## Room_0 참조 데이터

| label | iter_0 | iter_3000 | final PSNR | prior@15K (생존율) |
|-------|---:|---:|---:|---:|
| baseline | 8.142 | 10.325 | 12.234 | - |
| A 25K | 8.100 | 10.561 | **12.290** | 18,143 (73%) |
| A+C | 8.150 | 10.566 | 12.279 | 13,404 (54%) |
| A+B | 8.137 | 10.484 | 12.233 | 18,065 (72%) |
| A+B+C | 8.081 | 10.477 | 12.290 | 14,247 (57%) |

---

## 예상 시나리오 및 판단 기준

### 시나리오 1: Room_0 패턴 재현

> A 25K ≥ A+C ≥ A+B+C > A+B ≈ baseline

**해석:** 간섭 완화 조합의 불필요성이 scene-independent하게 확인됨.
**다음 단계:** A 25K(none)을 최종 삽입 정책으로 확정. Phase 4(실험 정리) 진입.

### 시나리오 2: Office_0에서 A+C 또는 A+B가 A 25K보다 좋음

> 특정 조합이 A 25K를 유의미하게 개선 (>0.05 dB)

**해석:** Scene geometry나 오브젝트 구성에 따라 최적 정책이 달라짐.
**다음 단계:** Scene 특성(오브젝트 밀도, SfM 포인트 분포)과 최적 정책의 상관관계 분석 필요.

### 시나리오 3: Office_0에서 prior 기여가 room_0보다 크게 나옴

> A 25K final PSNR이 baseline + 0.1 dB 이상 개선

**해석:** Office_0의 오브젝트 구성이 prior 활용에 더 유리함. 384-view에서도 prior 효과가 scene에 따라 다름.
**다음 단계:** Prior가 특히 효과적인 scene 특성을 분석. 50K prior budget 실험 추가 검토.

### 시나리오 4: Office_0에서 prior 삽입이 baseline보다 악화

> A 25K final PSNR < baseline

**해석:** Oracle exact prior라도 scene에 따라 역효과 가능.
**다음 단계:** Office_0의 오브젝트 배치/밀도가 간섭을 야기하는 원인 분석.

---

## 확인할 지표

1. **iter_0 / iter_3000 / final PSNR** — room_0과 동일한 수렴 패턴인지 확인
2. **Prior 생존율** — prior_protection.json에서 iter_3000, iter_15000의 protected_point_count
3. **SfM 제거 수** (A+B, A+B+C) — backend_run.json의 sfm_removed_count. Office_0의 SfM 분포가 room_0과 다를 수 있음
4. **SSIM / LPIPS** — PSNR과 교차 확인
5. **Room_0과의 delta 비교** — 각 조건의 baseline 대비 개선폭이 scene 간 일관적인지

---

## 참고

- Baseline은 이미 완료되었으므로 새로 실행할 필요 없음
- 신규 config 생성 불필요 — 기존 config 그대로 사용, `--scene office_0` 지정
- Phase 3 (protection 해제) 결과에서 protection 설정이 무관함을 확인했으므로, 모든 실험은 기본 none(lr_scale=0.05, prune/densify ON)으로 통일
