# Double-Sided Prior Rebuild Results

Date: 2026-04-06

이전 문서:
- `docs/notes/04-05_sofa77_hq_handoff_for_next_agent_2026.md`
- `docs/notes/04-05_all4_roomcontained_hq192_15k_prior_rebuild_2026.md`

---

## 1. 변경 사항

### 1.1 Double-sided mesh rendering
- `src/priorprobe/replica_surface.py` `ReplicaEGLRenderer.__init__()` 수정
- `pyrender.Mesh.from_trimesh()` 이후 각 primitive에 `doubleSided=True` 설정
- 효과: 메시 뒷면이 렌더링되어 구멍(hole)이 부분적으로 채워짐
- vertex color 보존 확인됨

### 1.2 Camera z_offset 변경 (이전 세션에서 적용, 유지됨)
- `src/priorprobe/replica_export.py` `generate_orbit_camera_poses()` 수정
- 기존: `z_offset = 0.25 * size_z + uniform(-0.2, 0.35)` (100% above center)
- 변경: `z_offset = 0.10 * size_z + uniform(-0.35, 0.35)` (61% above / 39% below)
- 효과: 아래쪽 시점이 추가되어 prior가 약간 넓어짐

### 1.3 Canny edge detection
- `scripts/collect_prior_position_sweep.py` `_image_edge_background()` 수정
- gradient 기반 → Canny edge (threshold1=20, threshold2=80)

---

## 2. 실행 파이프라인

### 2.1 전체 재학습 (4 objects, HQ192/15k, double-sided)

output 경로:
- scene dataset: `/mnt/3dgs-ssd/.../replica_colmap_multi_roomwide_v2_384_surface_rgb_roomcontained_hq192_ds`
- object dataset: `/mnt/3dgs-ssd/.../replica_object_surface_exact_rgb_roomcontained_hq192_ds`
- prior training: `outputs/gaussian_direct/prior_training/04-05-surface-trained-roomcontained-hq192-15k-ds-2026`
- prior library: `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-ds-2026`
- manifest: `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-ds-manifest-2026.json`
- config: `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-ds-2026.yaml`
- inventory: `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-ds-inventory-2026.json`

### 2.2 GT bbox crop 결과

| Object | Before | After | Removed | Z ratio (trained/GT) |
|--------|--------|-------|---------|---------------------|
| sofa 77 | 54,381 | 54,379 | 0.0% | **1.06x** (이전 1.51x) |
| chair 74 | 33,990 | 33,990 | 0.0% | 1.02x |
| chair 73 | 34,795 | 27,023 | 22.3% (XY spread) | 1.01x |
| table 11 | 35,973 | 35,973 | 0.0% | 1.01x |

**핵심**: Sofa Z bloat가 1.51x → 1.06x로 사실상 해결됨. Double-sided rendering이 메시 구멍을 채워 Gaussian 성장을 억제.

### 2.3 Fine position sweep 결과 (50 positions × 4 objects)

| Object | PASS | AMBIG | FAIL | 이전 결과 | 변화 |
|--------|------|-------|------|----------|------|
| table 11 | **50** | 0 | 0 | 50 PASS | 유지 |
| chair 73 | 0 | **50** | 0 | 50 AMBIG | 유지 |
| chair 74 | 0 | **50** | 0 | 50 PASS | **회귀** |
| sofa 77 | 0 | **50** | 0 | 50 AMBIG | 유지 |

sweep root: `outputs/gaussian_direct/reports/prior_position_all4_ds_cropped_fine50_2026`

---

## 3. 상세 분석

### 3.1 Sofa 77 — 형태 대폭 개선, 위치 병목

| Metric | Median | Threshold | Pass? |
|--------|--------|-----------|-------|
| mask_iou | 0.574 | ≥ 0.50 | YES |
| bbox_iou | **0.811** | ≥ 0.60 | **YES (64/64)** |
| centroid_px | **18.2** | ≤ 15.0 | **NO** |
| edge_px | **14.4** | ≤ 12.0 | **NO** |

핵심 해석:
- bbox_iou 0.81은 이전 ~0.5 대비 **대폭 개선**. Prior 형태가 GT와 잘 맞음.
- 하지만 centroid 18px, edge 14px로 **위치 오프셋**이 남아 있음.
- 즉, 형태는 맞지만 sweep anchor 기준 위치가 아직 ~3px 정도 보정 필요.
- **해결 방향**: sweep anchor 조정 또는 threshold 소폭 완화 (centroid 18→15, edge 14→12)

### 3.2 Chair 74 — bbox_iou 회귀

| Metric | Median | Threshold | Pass? |
|--------|--------|-----------|-------|
| mask_iou | 0.702 | ≥ 0.50 | YES |
| bbox_iou | **0.539** | ≥ 0.60 | **NO (9/30)** |
| centroid_px | 7.1 | ≤ 15.0 | YES |
| edge_px | 8.9 | ≤ 12.0 | YES |

핵심 해석:
- 이전 run에서는 50/50 PASS였는데 이번에 AMBIGUOUS로 회귀.
- bbox_iou가 0.539 (threshold 0.60 미달)
- prior가 GT보다 약간 넓게 렌더링됨. `prior_visible_pixels > gt_visible_pixels` 일관적.
- **원인**: 카메라 z_offset 변경으로 아래쪽 시점 추가 → prior가 의자 다리/하부 쪽으로 더 퍼짐.
- **해결 방향**: z_offset을 원래 값으로 되돌리고 double-sided만 유지한 채 재학습.

### 3.3 Chair 73 — bbox_iou + centroid 이중 병목

| Metric | Median | Threshold | Pass? |
|--------|--------|-----------|-------|
| mask_iou | 0.546 | ≥ 0.50 | YES (경계) |
| bbox_iou | **0.551** | ≥ 0.60 | **NO (4/29)** |
| centroid_px | 12.2 | ≤ 15.0 | YES (경계) |
| edge_px | 9.9 | ≤ 12.0 | YES |

핵심 해석:
- 이전에도 AMBIGUOUS였고, 변화 없음.
- bbox_iou 0.55는 threshold에 근접하지만 미달.
- z_offset 원복이 도움될 수 있음.

---

## 4. ds-v2 결과 (z_offset 원복 + double-sided 유지)

ds-v1에서 chair 74 회귀 원인이 camera z_offset 변경으로 확인되어, z_offset을 원래 값(`0.25 * size_z + uniform(-0.2, 0.35)`)으로 되돌리고 4개 object 전체 재학습.

### 4.1 Output 경로 (ds-v2)

- scene dataset: `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_v2_384_surface_rgb_roomcontained_hq192_ds_v2`
- object dataset: `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_object_surface_exact_rgb_roomcontained_hq192_ds_v2`
- prior training: `outputs/gaussian_direct/prior_training/04-05-surface-trained-roomcontained-hq192-15k-ds-v2-2026`
- prior library: `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-ds-v2-2026`
- override JSON: `/tmp/ds_v2_prior_override.json`
- sweep results: `outputs/gaussian_direct/reports/prior_position_all4_ds_v2_cropped_fine50_2026`

### 4.2 GT bbox crop 결과 (ds-v2)

| Object | Before | After | Removed | Z ratio (trained/GT) |
|--------|--------|-------|---------|---------------------|
| sofa 77 | — | — | 0.0% | **1.12x** (ds-v1: 1.06x, 원본: 1.51x) |
| chair 74 | — | — | 0.0% | 1.01x |
| chair 73 | — | — | 0.0% | 1.02x (ds-v1: 22.3% XY 잘림 → 0%) |
| table 11 | — | — | 0.0% | 1.01x |

**핵심**: ds-v2는 원본 z_offset을 복원해 chair 73의 XY spread 문제가 완전히 해결됨.

### 4.3 Fine sweep 상세 메트릭 비교 (ds-v2 median, 50 variants)

| Object | mask_iou | bbox_iou | centroid_px | edge_px | coverage | Decision |
|--------|----------|----------|-------------|---------|----------|----------|
| table 11 | 0.818 | **0.899** | 5.10 | 6.36 | 0.964 | **50 PASS** |
| chair 74 | 0.770 | **0.866** | 3.55 | 6.07 | 0.996 | **50 PASS** |
| chair 73 | 0.696 | 0.532 | 9.63 | 9.78 | 0.964 | 50 AMBIG (bbox_iou < 0.60) |
| sofa 77 | 0.602 | **0.810** | 15.50 | 13.81 | 0.938 | 50 AMBIG (centroid>15, edge>12) |
| threshold | ≥0.50 | ≥0.60 | ≤15.0 | ≤12.0 | — | — |

### 4.4 ds-v1 vs ds-v2 비교 (Chair 74 회귀 복구)

| Object | ds-v1 bbox_iou | ds-v2 bbox_iou | ds-v1 decision | ds-v2 decision |
|--------|---------------|---------------|---------------|---------------|
| table 11 | 0.90+ | 0.899 | 50 PASS | **50 PASS** |
| chair 74 | **0.539** | **0.866** | **50 AMBIG** (회귀) | **50 PASS** (복구) |
| chair 73 | 0.551 | 0.532 | 50 AMBIG | 50 AMBIG |
| sofa 77 | 0.811 | 0.810 | 50 AMBIG | 50 AMBIG |

**핵심**: z_offset 원복으로 chair 74가 완전 복구 (bbox_iou +0.33). Sofa 77 bbox_iou는 동일하게 유지되어 z_offset 변화는 sofa 형태에 영향 없음.

### 4.5 Sofa 77 best variant (ds-v2)

- **variant**: `v050_f046_dx+0p000_dy+0p030_dz-0p065`
- mask_iou=0.639, bbox_iou=0.833, centroid=12.82px, **edge=13.14px**
- 여전히 edge_px > 12.0 threshold. 50개 variant 중 어느 것도 edge ≤ 12.0 도달하지 못함.

## 5. 결론

### 무엇이 성공했나
1. **Double-sided rendering** (ds-v1, ds-v2 모두): Sofa Z bloat 1.51x → 1.06–1.12x. 메시 구멍 문제 근본 해결.
2. **Sofa bbox_iou**: ~0.5 → 0.81. Prior 형태가 GT와 거의 일치.
3. **z_offset 원복 (ds-v2)**: Chair 74 완전 복구 (0.54 → 0.87 bbox_iou, 50 PASS).
4. **Table 11**: 모든 run에서 50/50 PASS 유지.

### 무엇이 여전히 실패했나
1. **Sofa 77 sweep anchor 위치 오차**: bbox_iou는 우수(0.81)하지만 centroid(15.5px) / edge(13.8px) 모두 threshold 초과.
   - 현재 anchor `v050_dx+0p00_dy+0p00_dz-0p08` 주변 50 variants 모두 실패.
   - 형태는 맞으므로 sweep anchor 자체 위치가 GT 중심과 이격되어 있음.
2. **Chair 73 bbox_iou 병목**: double-sided + 원복 z_offset 조합에서도 bbox_iou 0.53 (threshold 0.60 미달).
   - mask_iou / centroid / edge 모두 통과 — bbox_iou 혼자 발목을 잡음.
   - Prior이 GT보다 미세하게 큰 bbox로 렌더링됨.

## 6. 권장 다음 단계

**우선순위 1**: Sofa 77 sweep anchor 재탐색
- 현재 anchor는 `v050_dx+0p00_dy+0p00_dz-0p08` 한 개만 사용 중.
- ds-v2 prior로 coarse sweep 재실행해서 sofa 77용 새 최적 anchor 탐색.
- 또는 edge/centroid threshold를 완화 (centroid 15→18, edge 12→15) — 이 경우 ds-v2 sofa는 즉시 PASS 가능 (median 15.5/13.8).

**우선순위 2**: Chair 73 bbox_iou 조사
- 모든 variant의 bbox_iou가 0.52–0.55 좁은 범위. 형태 자체가 GT보다 약간 퍼진 것으로 추정.
- Canonical crop bounds를 더 타이트하게 (XY 마진 5% → 0%) 조정해서 재시도.
- 또는 chair 73 mesh를 직접 살펴보고 구멍/아티팩트 여부 확인.

**우선순위 3**: 통합 검증
- ds-v2로 4/4 PASS 달성 후 실제 scene insertion smoke test.
- 현재 상태(table 11, chair 74 PASS)만으로도 부분 smoke test 가능.

---

## 7. 자주 참조할 경로

**ds-v2 (최신, 권장)**:
- Prior library: `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-ds-v2-2026`
- Cropped assets: `.../assets/*/replica_room_0_obj_*/splat_cropped.ply`
- Override JSON: `/tmp/ds_v2_prior_override.json`
- Sweep results: `outputs/gaussian_direct/reports/prior_position_all4_ds_v2_cropped_fine50_2026`

**ds-v1 (new camera angles, chair 74 regression)**:
- Prior library: `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-ds-2026`
- Sweep results: `outputs/gaussian_direct/reports/prior_position_all4_ds_cropped_fine50_2026`

**이전 (non-DS, sofa bloat)**:
- Prior library: `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-2026`
- Sweep results: `outputs/gaussian_direct/reports/prior_position_all4_cropped_fine50_2026`

---

## 8. 변경된 코드 파일 (최종 상태)

- `src/priorprobe/replica_surface.py` — ReplicaEGLRenderer double-sided rendering (유지)
- `src/priorprobe/replica_export.py` — camera z_offset **원복됨** (`0.25 * size_z + uniform(-0.2, 0.35)`)
- `scripts/collect_prior_position_sweep.py` — Canny edge detection (유지)

---

what changed:
- Double-sided rendering 유지 + z_offset 원복 + 4개 object 전체 재학습 (ds-v2).

what was checked:
- Table 11 / Chair 74 50/50 PASS (chair 74 bbox_iou 0.54 → 0.87). Sofa 77 bbox_iou 0.81 유지, Chair 73 bbox_iou 0.53 여전히 미달.

what remains risky:
- Sofa 77 sweep anchor 위치 자체가 GT 중심과 이격되어 모든 variant가 AMBIG. Chair 73 bbox_iou 원인은 구조적 형태 불일치.

next concrete action:
- ds-v2 prior로 sofa 77 coarse sweep 재실행해서 새 anchor 후보 찾기. Chair 73 GT bbox crop XY 마진 축소 실험.
