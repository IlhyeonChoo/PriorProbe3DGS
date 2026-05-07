# Automated Prior Position Validator v1 Note

Date: 2026-04-05

관련 문서:
- `docs/experiment_plans/04-05_automated_prior_position_validation_plan_2026.md`
- `docs/experiment_results/04-05_prior_insertion_status_summary_2026.md`
- `docs/notes/04-05_iter0_triplet_validation_room0_2026.md`

---

## Summary

계획 문서 기준으로 multi-view 2D evidence 기반 자동 prior position validator v1을 구현했다.

추가 항목:
- 신규 모듈
  - `src/priorprobe/validation/__init__.py`
  - `src/priorprobe/validation/prior_position_validator.py`
- 신규 CLI
  - `scripts/validate_prior_positions.py`
- 신규 테스트
  - `tests/test_prior_position_validator.py`

validator는 다음을 수행한다.
1. `backend_run_dir` 기준 source-of-truth 해석
2. GT semantic mask 생성
3. aligned prior 전체 / object별 isolated render 생성
4. full-prior depth 기준 visible prior mask 생성
5. per-view / per-object metric 집계
6. `PASS / FAIL / AMBIGUOUS / INPUT_MISMATCH` 출력
7. JSON report와 overlay/contact sheet 저장

---

## 구현 범위

### 입력 해석

resolver는 다음 우선순위를 따른다.
1. sibling experiment dir의 `backend_run.json`
2. `backend_run_dir/cfg_args`
3. `backend_run_dir/prior_init/metadata.json`
4. `prior_specs.json`
5. `scene_root/sparse/0/{test.txt,cameras.txt,images.txt}`

추가 보완:
- legacy run의 stale `aligned_prior` absolute path는 `backend_run_dir/prior_init/<filename>` fallback으로 복구
- surface RGB dataset root에 `habitat/mesh_semantic.ply`가 없을 경우 `scene_meta.json`의 `raw_scene_root` 또는 `reference_scene_root`를 따라 semantic source scene root를 복구

### GT semantic mask

기본 경로:
- `ReplicaHabitatRenderer`

fallback:
- `ReplicaPointRenderer`

현재 실제 실행 환경에서는 `habitat_sim` 미설치로 fallback renderer가 사용되었다.

### prior-only render

- full prior render: run에 삽입된 `aligned_prior_*.ply`를 합쳐 depth-enabled gaussian renderer로 렌더
- isolated prior render: object별 `aligned_prior_XX.ply` 단독 렌더
- visible mask: `abs(isolated_depth - full_depth) <= 0.02m`

### 출력 artifact

각 실행에서 생성:
- `summary.json`
- `per_object_metrics.json`
- `per_view_metrics.json`
- `contact_sheet.png`
- `overlays/`

---

## 환경 이슈와 보완

현재 repo 기본 `uv run python` 환경에는 backend rasterizer extension `diff_gaussian_rasterization`이 없다.
반면 backend 전용 venv에는 해당 extension이 있다.

따라서 CLI는 다음 보완을 넣었다.
- 기본 호출이 `uv run python scripts/validate_prior_positions.py ...`여도
- 내부적으로 `backend_run.json`의 command / repo_path를 읽어
- 필요 시 backend venv python으로 자동 re-exec 한다

즉 사용자는 계획 문서의 단일 CLI를 그대로 호출할 수 있고,
실제 renderer 실행은 backend 호환 interpreter에서 수행된다.

---

## 테스트

실행:
- `uv run pytest -q tests/test_prior_position_validator.py tests/test_build_initial_snapshot_viewer.py tests/test_replica_surface.py`

결과:
- `14 passed`

새 테스트가 검증한 것:
- stale aligned prior path fallback
- scene_meta 기반 semantic source root fallback
- visible prior mask depth filtering
- per-view metric 계산
- baseline no-prior 상태 처리
- prior_specs mismatch 시 `INPUT_MISMATCH`

---

## 실제 validator 실행 결과

### 1. baseline smoke

명령:
- `uv run python scripts/validate_prior_positions.py --backend-run-dir outputs/gaussian_direct/backend_runs/surface_rgb_roomcontained_baseline_smoke_1000/room_0 --output-dir outputs/gaussian_direct/reports/position_validation_surface_rgb_roomcontained_baseline_smoke_1000_room0`

결과:
- decision: `PASS`
- reason: `no_priors_to_validate`

artifact:
- `outputs/gaussian_direct/reports/position_validation_surface_rgb_roomcontained_baseline_smoke_1000_room0/summary.json`

### 2. known-bad repro

명령:
- `uv run python scripts/validate_prior_positions.py --backend-run-dir outputs/gaussian_direct/backend_runs/03-24-prior50k-geo-15k-2026/room_0 --output-dir outputs/gaussian_direct/reports/position_validation_03-24-prior50k-geo-15k-2026_room0`

결과:
- decision: `FAIL`
- object-level:
  - `obj_6`: `FAIL`
  - `obj_9`: `FAIL`
  - `obj_77`: `AMBIGUOUS`
  - `obj_74`: `AMBIGUOUS`

핵심 수치:
- `obj_6`
  - median mask IoU = `0.0`
  - median centroid distance = `83.38 px`
  - median edge distance = `64.93 px`
  - severe outlier ratio = `1.0`
- `obj_9`
  - median centroid distance = `25.93 px`

artifact:
- `outputs/gaussian_direct/reports/position_validation_03-24-prior50k-geo-15k-2026_room0/summary.json`
- `outputs/gaussian_direct/reports/position_validation_03-24-prior50k-geo-15k-2026_room0/contact_sheet.png`

### 3. roomcontained prior smoke

명령:
- `uv run python scripts/validate_prior_positions.py --backend-run-dir outputs/gaussian_direct/backend_runs/surface_rgb_roomcontained_prior_100k_geo_smoke_1000/room_0 --output-dir outputs/gaussian_direct/reports/position_validation_surface_rgb_roomcontained_prior_100k_geo_smoke_1000_room0`

결과:
- decision: `FAIL`
- object-level:
  - `obj_77`: `AMBIGUOUS`
  - `obj_74`: `AMBIGUOUS`
  - `obj_73`: `AMBIGUOUS`
  - `obj_11`: `FAIL`

대표 수치:
- `obj_77`
  - median mask IoU = `0.562`
  - median bbox IoU = `0.661`
  - median centroid distance = `13.04 px`
  - median edge distance = `18.23 px`
- `obj_11`
  - median mask IoU = `0.457`
  - median bbox IoU = `0.556`
  - median centroid distance = `28.44 px`
  - median edge distance = `16.86 px`

artifact:
- `outputs/gaussian_direct/reports/position_validation_surface_rgb_roomcontained_prior_100k_geo_smoke_1000_room0/summary.json`
- `outputs/gaussian_direct/reports/position_validation_surface_rgb_roomcontained_prior_100k_geo_smoke_1000_room0/contact_sheet.png`

---

## 현재 해석

### 확인된 것

1. validator는 실제로 동작한다
   - source-of-truth resolve
   - semantic mask 생성
   - depth-enabled prior-only render
   - per-object 판정
   - overlay/contact sheet 출력

2. catastrophic bad repro는 자동으로 `FAIL`로 걸러진다
   - 특히 floating lamp(`obj_6`)는 강하게 분리된다

3. baseline no-prior 상태는 명시적으로 처리된다

### 아직 남은 문제

1. roomcontained prior smoke가 현재 bootstrap threshold로는 `PASS`가 아니다
   - 즉 v1은 bad run 분리에는 유용하지만
   - known-good smoke를 아직 안정적으로 `PASS`로 올리지는 못했다

2. GT semantic backend가 현재 `semantic_point_renderer` fallback이다
   - `habitat_sim` 부재로 semantic mask가 point-sampled silhouette에 의존한다
   - 이 때문에 chair/table 같은 object에서 centroid / edge metric이 흔들릴 가능성이 있다

3. 따라서 threshold calibration은 아직 잠정 상태다
   - 현재 default는 계획 문서의 bootstrap default 그대로 유지했다
   - 별도 calibration note로 threshold를 고정하기 전까지는
     - `FAIL` 중에서도 catastrophic failure와 borderline failure를 분리해 읽어야 한다

---

## 다음 권장 액션

1. overlay/contact sheet에서 `obj_11 table`과 `obj_73/74 chair`의 실제 위치 오차가 semantic fallback artifact인지 확인
2. 가능하면 `habitat_sim` 기반 semantic mask 환경에서 같은 run을 다시 검증
3. 그 결과를 바탕으로 threshold calibration note를 작성하고 family-wide threshold를 고정
4. 그 다음에 iter_0 smoke gate 통합 여부를 최종 결정
