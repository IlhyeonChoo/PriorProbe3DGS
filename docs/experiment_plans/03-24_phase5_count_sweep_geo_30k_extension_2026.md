# Phase 5.2-5.3: Prior Count Sweep, Geometry-Only, 30K 연장

Date: 2026-03-24

이전 계획:
- `docs/experiment_plans/03-23_phase5_surface_rgb_prior_insertion_2026.md` (Phase 5 초기 설계)

---

## 배경: Phase 5 초기 결과 (15K)

Surface RGB 이미지로 전환 후 5개 실험을 완료했다.

### Baseline 대비 Delta (final, 15000 iter)

| 조건 | room_0 Δ | office_0 Δ | 판정 |
|------|----------:|----------:|------|
| Prior full (~150K) | +0.514 | -0.352 | scene-dependent |
| **Prior 100K** | **+0.502** | **+1.471** | **양쪽 양수 (best)** |
| Prior 25K | -0.579 | +1.130 | scene-dependent |
| Prior 25K full_none | -0.038 | -0.339 | 약세 |

### Baseline 절대값

| Scene | iter_0 | iter_3000 | final (15000) | SSIM | Gaussians |
|-------|-------:|----------:|--------------:|-----:|----------:|
| room_0 | 11.234 | 41.630 | 46.682 | 0.9929 | 207,338 |
| office_0 | 13.054 | 36.580 | 43.737 | 0.9892 | 225,564 |

### 미결 질문

1. **25K→100K 사이 어디서 room_0의 delta가 음→양으로 반전하는가?**
2. **기하 정보만 제공하면 (SH 리셋) prior 효과가 어떻게 변하는가?**
3. **15K 이후 추가 최적화가 prior 실험의 delta를 유지/확대/축소하는가?**

---

## 목적

이 계획은 두 단계로 구성된다:

- **Phase 5.2**: Count sweep (50K, 75K) + Geometry-only (SH zero_all) 실험 — 15K iter
- **Phase 5.3**: Phase 5 전체에서 유망한 조건을 선별하여 30K iter로 연장

---

## Phase 5.2: Count Sweep + Geometry-Only (15K)

### 공통 조건

- Dataset: `replica_multi_roomwide_v2_384_surface_rgb_shared.yaml`
- Scenes: room_0, office_0
- Iteration: 15,000
- Prior library: `replica_target_surface_exact_trained_clip`
- Retrieval: same_scene_exact (oracle)
- Protection: `none`
- 해석 주의: Phase 5.2 / 5.3은 2026-03-23의 Phase 5 초기 15K 결과와
  **동일하게 protection 없음**을 유지한다. count / SH / iteration 효과만 비교한다.

### 실험 목록

| # | 실험명 | prior 수 | SH mode | 목적 |
|---|--------|------:|---------|------|
| 5 | `surface_rgb_prior_50k_15000` | 50,000 | none | 25K↔100K 반전점 탐색 |
| 6 | `surface_rgb_prior_75k_15000` | 75,000 | none | 세밀한 count sweep |
| 7 | `surface_rgb_prior_100k_geo_15000` | 100,000 | zero_all | 기하 정보만 제공 (best count) |
| 8 | `surface_rgb_prior_50k_geo_15000` | 50,000 | zero_all | count × SH 교차 비교 |

### 실험 5: Prior 50K

```yaml
experiment_name: gaussian_direct_surface_rgb_prior_50k_15000
prior_target_total_gaussians: 50000
prior_sh_reset_mode: none
prior_protection_mode: none
```

25K(-0.579, +1.130)과 100K(+0.502, +1.471) 사이의 중간점. room_0에서 delta가 음→양으로 바뀌는 지점이 50K 이하인지 이상인지 판별.

### 실험 6: Prior 75K

```yaml
experiment_name: gaussian_direct_surface_rgb_prior_75k_15000
prior_target_total_gaussians: 75000
prior_sh_reset_mode: none
prior_protection_mode: none
```

50K 결과에 따라 반전점을 더 좁혀줄 실험. 50K가 이미 양수면 sweet spot은 25K~50K 사이. 50K가 음수면 50K~100K 사이.

### 실험 7: Prior 100K Geometry-Only

```yaml
experiment_name: gaussian_direct_surface_rgb_prior_100k_geo_15000
prior_target_total_gaussians: 100000
prior_sh_reset_mode: zero_all
prior_protection_mode: none
```

**핵심 실험.** 현재 best(100K, SH 유지)와 동일 count에서 SH만 리셋.

- 결과 ≥ 100K(SH none) → prior 가치는 기하 정보에 있음. SH가 오히려 방해. cross-scene prior 적용 가능성 높아짐
- 결과 < 100K(SH none) → SH 정보도 기여. 기하만으로는 부족

### 실험 8: Prior 50K Geometry-Only

```yaml
experiment_name: gaussian_direct_surface_rgb_prior_50k_geo_15000
prior_target_total_gaussians: 50000
prior_sh_reset_mode: zero_all
prior_protection_mode: none
```

Count × SH 교차 비교를 위한 실험. 50K(SH none) vs 50K(SH zero) 비교로 SH 리셋의 효과가 count에 따라 달라지는지 확인.

### Phase 5.2 실행 순서

```
실험 5 (50K)  →  실험 6 (75K)  →  실험 7 (100K geo)  →  실험 8 (50K geo)
```

GPU와 metrics 후처리 시간을 고려해 **전체를 순차 실행**한다.
5, 6을 먼저 완료해 반전 구간을 확인하고, 이어서 7, 8을 실행한다.

---

## Phase 5.3: 30K 연장

### 목적

15K에서 수렴이 아직 진행 중인지, prior의 이득이 장기적으로 유지되는지 확인한다.

Phase 5 초기 결과에서 room_0의 수렴 곡선을 보면:
- Baseline: iter_10000 → 46.413, iter_15000 → 46.682 (Δ = +0.269)
- Prior 100K: iter_10000 → 46.534, iter_15000 → 47.184 (Δ = +0.650)

**100K prior가 10K→15K 구간에서 baseline보다 더 빠르게 수렴 중.** 30K까지 가면 delta가 더 벌어질 가능성이 있다.

반대로 25K는:
- Prior 25K: iter_10000 → 45.642, iter_15000 → 46.103 (Δ = +0.461)

Baseline보다 느린 수렴은 아니지만, 출발점이 낮아서 따라잡기 어려움.

### 30K Baseline (필수)

```yaml
experiment_name: gaussian_direct_surface_rgb_baseline_30000
iterations: 30000
```

30K prior 실험의 비교 기준. **이 실험은 Phase 5.2 결과와 무관하게 반드시 실행한다.**

### 30K 연장 선별 기준

Phase 5.2 완료 후, 아래 기준으로 30K 연장 대상을 선별한다:

**필수 연장:**
- Baseline 30K
- Prior 100K 30K (현재 best, 양쪽 scene 양수)

**조건부 연장 (15K delta 기준):**

| 조건 | 연장 기준 | 현재 상태 |
|------|-----------|-----------|
| Prior 100K (SH none) | 양쪽 scene > 0 | **연장 확정** |
| Prior 50K | 최소 1 scene > 0 | 결과 대기 |
| Prior 75K | 최소 1 scene > 0 | 결과 대기 |
| Prior 100K geo (zero_all) | 최소 1 scene > 0 | 결과 대기 |
| Prior 50K geo (zero_all) | 최소 1 scene > 0 | 결과 대기 |
| Prior full (~150K) | room_0 > 0 이미 확인 | **연장 후보** |
| Prior 25K | office_0 > 0 이미 확인 | **연장 후보** |

**연장 제외:**
- Prior 25K full_none (양쪽 약세/음수)

양수 조건이 여러 개 나오더라도 **cap 없이 모두 30K로 연장**한다.

### 30K 연장 실험 형식

```yaml
experiment_name: gaussian_direct_surface_rgb_prior_100k_30000
iterations: 30000
# 나머지 설정은 15K 실험과 동일
```

30K 실험은 **처음부터 재학습**한다 (15K checkpoint에서 이어하지 않음). 이유:
- 15K와 30K의 checkpoint 스케줄이 다를 수 있음
- 재현 가능한 독립 실험 유지
- densification은 15K에서 이미 종료되므로 15K→30K 구간은 순수 최적화

### 30K에서 확인할 지표

1. **Delta 유지 여부**: 15K에서의 baseline 대비 delta가 30K에서도 유지되는가
2. **수렴 포화 시점**: PSNR 증가가 언제 멈추는가 (prior vs baseline 비교)
3. **Prior 조건 간 순위 변동**: 15K의 순위(100K > full > 25K > full_none)가 30K에서도 동일한가
4. **Geometry-only vs SH 유지**: 30K 추가 최적화가 SH 리셋의 불이익을 줄이는가 (zero_all이 학습할 시간이 더 생기므로)

---

## 보고서 / 산출물 경로

### Phase 5.2 (15K sweep)

- Markdown:
  `docs/experiment_results/03-24_phase5_count_sh_sweep_15k_2026.md`
- Summary CSV:
  `outputs/gaussian_direct/reports/replica_gaussian_direct_phase5_count_sh_sweep_15k_summary.csv`
- Checkpoints CSV:
  `outputs/gaussian_direct/reports/replica_gaussian_direct_phase5_count_sh_sweep_15k_checkpoints.csv`
- Object survival CSV:
  `outputs/gaussian_direct/reports/replica_gaussian_direct_phase5_count_sh_sweep_15k_object_survival.csv`

### Phase 5.3 (30K extension)

- Markdown:
  `docs/experiment_results/03-24_phase5_30k_extension_2026.md`
- Summary CSV:
  `outputs/gaussian_direct/reports/replica_gaussian_direct_phase5_30k_extension_summary.csv`
- Checkpoints CSV:
  `outputs/gaussian_direct/reports/replica_gaussian_direct_phase5_30k_extension_checkpoints.csv`
- Object survival CSV:
  `outputs/gaussian_direct/reports/replica_gaussian_direct_phase5_30k_extension_object_survival.csv`

---

## 예상 시나리오

### 시나리오 A: 30K에서 delta 확대

> Prior 100K의 30K delta > 15K delta

Prior가 제공한 기하 구조가 장기 최적화에서도 지속적으로 이점. 수렴 상한이 baseline보다 높다는 의미.

→ Prior 삽입의 가치가 더 강하게 확인됨.

### 시나리오 B: 30K에서 delta 유지

> 30K delta ≈ 15K delta (±0.1 dB)

Prior와 baseline 모두 비슷한 속도로 수렴 중. Prior의 이점은 초기 수렴 가속에 집중.

→ 15K 결과가 안정적 결론임을 확인.

### 시나리오 C: 30K에서 delta 축소/소멸

> 30K delta < 15K delta, 특히 0 dB에 수렴

Baseline이 15K 이후에도 빠르게 개선되어 prior 이점을 흡수. Prior는 "일시적 가속"에 불과.

→ Prior의 장기적 가치 제한적. 수렴 속도 이점에 초점을 맞춰야 함.

### 시나리오 D: Geometry-only가 SH 유지를 능가

> 100K geo(zero_all) delta > 100K(SH none) delta

SH 정보가 간섭을 유발하고 있었음. 기하 scaffold만으로 충분하며 외관은 최적화가 알아서 학습.

→ Cross-scene prior 적용의 강력한 근거. 형태만 비슷하면 작동 가능.

---

## 전체 실행 순서

```
[Phase 5.2 — 15K, 4개 실험]
  ┌─ 실험 5: Prior 50K ─────────────┐
  ├─ 실험 6: Prior 75K ─────────────┤ count sweep
  ├─ 실험 7: Prior 100K geo-only ───┤ geometry-only
  └─ 실험 8: Prior 50K geo-only ────┘
       ↓
  결과 분석 + 30K 대상 선별
       ↓
[Phase 5.3 — 30K, 선별 실험]
  ┌─ Baseline 30K (필수) ───────────┐
  ├─ Prior 100K 30K (확정) ─────────┤
  ├─ Phase 5.2 양수 조건들 30K ─────┤ 조건부
  └─ 기존 15K 양수 조건들 30K ──────┘ 조건부
       ↓
  최종 분석: count × SH × iteration 3차원 비교
```

---

## 생성할 Config 파일

### Phase 5.2 (15K)

| 파일명 | 비고 |
|--------|------|
| `gaussian_direct_surface_rgb_prior_50k_15000.yaml` | count sweep |
| `gaussian_direct_surface_rgb_prior_75k_15000.yaml` | count sweep |
| `gaussian_direct_surface_rgb_prior_100k_geo_15000.yaml` | SH zero_all |
| `gaussian_direct_surface_rgb_prior_50k_geo_15000.yaml` | SH zero_all |

### Phase 5.3 (30K) — Phase 5.2 결과 후 생성

| 파일명 | 비고 |
|--------|------|
| `gaussian_direct_surface_rgb_baseline_30000.yaml` | 필수 |
| `gaussian_direct_surface_rgb_prior_100k_30000.yaml` | 확정 |
| 이하 Phase 5.2 결과에 따라 결정 | 조건부 |

---

## Smoke Test

Phase 5 초기 smoke test에서 파이프라인 동작을 확인했으므로, `prior_sh_reset_mode: zero_all`만 추가 검증:

```yaml
gaussian_direct_surface_rgb_prior_100k_geo_smoke_1000.yaml
```

확인 사항:
- SH 리셋 후 iter_0 렌더링에서 prior 위치가 무채색(gray)으로 나타나는지
- 500~1000 iter에서 색상이 학습되기 시작하는지
- metadata.json에 4개 object가 정상 기록되는지
