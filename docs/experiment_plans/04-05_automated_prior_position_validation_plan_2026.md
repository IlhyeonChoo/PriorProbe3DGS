# Automated Prior Insertion Position Validation Plan

Date: 2026-04-05

관련 문서:
- `docs/experiment_plans/04-04_prior_insertion_geometry_fix_plan_2026.md`
- `docs/experiment_results/04-05_prior_insertion_status_summary_2026.md`
- `docs/notes/04-05_iter0_triplet_validation_room0_2026.md`
- `docs/notes/04-04_prior_insertion_geometry_phaseA_room0_2026.md`

---

## 1. 목적

현재 prior 삽입 후 위치 정합성 검증은 contact sheet를 사람이 육안 확인하는 수동 단계에 크게 의존한다.
이 계획의 목적은 이를 **여러 시점의 2D image evidence를 종합한 자동 판정기**로 대체하거나, 최소한 사람이 매번 직접 확인해야 하는 상황을 예외 케이스로 줄이는 것이다.

핵심 목표:

1. 삽입된 prior가 GT semantic object 위치와 여러 test view에서 일관되게 정합하는지 자동 판정한다
2. `iter_0` smoke 단계에서 `PASS / FAIL / AMBIGUOUS / INPUT_MISMATCH`를 자동 산출한다
3. 수동 검토는 기본 절차가 아니라 `AMBIGUOUS` 또는 `INPUT_MISMATCH`일 때만 수행한다

이 validator는 기존 3D geometry fail-fast를 대체하지 않는다.
대신 다음 두 층을 함께 사용한다.

1. **3D geometry validation**
   - scene proxy 기준 fail-fast
   - room containment, floating, outside ratio 검증
2. **2D multi-view position validation**
   - GT semantic mask와 prior-only render mask를 여러 view에서 비교
   - image-level evidence로 최종 smoke 판정을 자동화

즉, 이 문서의 validator는 보조 지표가 아니라 **smoke 단계의 주요 자동 판정기**다.

---

## 2. 적용 범위와 설계 원칙

### 2.1 적용 범위

validator 자체의 적용 범위는 특정 scene 하나가 아니라 다음 계열 전체다.

- gaussian-direct prior insertion runs
- Replica surface RGB family
- smoke 중심의 `iter_0` position correctness gate

현재 바로 사용 가능한 calibration corpus는 `room_0`에서 먼저 확보되어 있다.
하지만 이는 구현 범위를 `room_0`에 제한한다는 뜻이 아니라, **초기 threshold bootstrap 근거**로 사용한다는 의미다.

초기 calibration에 사용할 대표 run:

- known-bad repro:
  - `outputs/gaussian_direct/backend_runs/03-24-prior50k-geo-15k-2026/room_0`
- known-good prior smoke:
  - `outputs/gaussian_direct/backend_runs/surface_rgb_roomcontained_prior_100k_geo_smoke_1000/room_0`
- baseline smoke:
  - `outputs/gaussian_direct/backend_runs/surface_rgb_roomcontained_baseline_smoke_1000/room_0`

향후 `office_0` 및 다른 scene이 추가되더라도 validator 로직과 threshold 정책은 동일하게 유지한다.

### 2.2 설계 원칙

1. **Image evidence를 주 판정 신호로 사용한다**
   - edge, silhouette, centroid, bbox를 여러 view에서 동시에 본다
2. **특정 scene 전용 heuristics를 두지 않는다**
   - threshold는 scene별이 아니라 dataset family 공통값으로 관리한다
3. **수동 검토를 예외 경로로 내린다**
   - 기본 smoke는 자동으로 `PASS` 또는 `FAIL`까지 내려가는 것을 목표로 한다
4. **입력 불일치는 명시적으로 분리한다**
   - 애매한 정합과 metadata mismatch를 같은 실패로 섞지 않는다
5. **기본 gate는 전체 test view를 사용한다**
   - authoritative smoke 판정은 view subsampling 없이 full test set 기준으로 수행한다

---

## 3. 전체 파이프라인 개요

```text
Step 0: backend run dir에서 source-of-truth resolve
Step 1: GT semantic mask 생성 (per view, per object)
Step 2: prior-only render 생성 (per view, full-prior + per-object)
Step 3: prior visible mask 생성 (per view, per object)
Step 4: Per-view, per-object metric 계산
Step 5: Multi-view 집계 및 PASS / FAIL / AMBIGUOUS / INPUT_MISMATCH 판정
Step 6: JSON report + overlay artifact 저장
```

이 파이프라인은 smoke run의 `iter_0` snapshot이 생성된 뒤 실행한다.

---

## 4. 입력 계약과 Source of Truth

### 4.1 CLI 계약

주 실행 경로는 다음으로 고정한다.

```bash
uv run python scripts/validate_prior_positions.py \
    --backend-run-dir <backend_run_dir> \
    --output-dir <report_dir> \
    [--iou-threshold <float>] \
    [--bbox-iou-threshold <float>] \
    [--centroid-threshold-px <float>] \
    [--edge-threshold-px <float>] \
    [--min-views <int>]
```

주 실행 경로에서는 `--scene-root`나 `--prior-spec`를 별도로 받지 않는다.
validator는 `backend_run_dir`만 받아 내부 metadata에서 필요한 경로를 해석한다.

### 4.2 Source-of-truth 우선순위

validator는 다음 우선순위로 입력을 해석한다.

1. `backend_run.json`
2. `prior_init/metadata.json`
3. `prior_specs.json`
4. dataset config
5. scene dataset 내부의 `test.txt`, `sparse/0/cameras.txt`, `sparse/0/images.txt`, `oracle/targets.json`

이 문서에서 중요한 원칙:

- run identity는 `backend_run.json`이 canonical이다
- prior object mapping과 aligned prior artifact는 `prior_init/metadata.json`이 canonical이다
- `prior_specs.json`은 보완용으로만 사용한다

### 4.3 입력 불일치 처리

아래 중 하나라도 발생하면 validator는 정합 판정을 하지 않고 `INPUT_MISMATCH`로 종료한다.

- scene id 불일치
- dataset root 또는 dataset config 불일치
- `selected_priors[*].target_object_id`와 `prior_specs.json` 간 매핑 불일치
- aligned prior artifact 누락
- test view 목록이나 camera metadata를 해석할 수 없음
- camera convention 또는 intrinsics cross-check 실패
- renderer가 `depth` 출력을 제공하지 않음

---

## 5. 상세 설계

### 5.1 Step 0: run metadata 해석

입력:

- `backend_run_dir`

해석 결과:

- `scene_id`
- dataset family / dataset root
- test view 목록
- width / height / hfov 또는 동등한 camera intrinsics 정보
- target object id 목록
- per-object aligned prior artifact path
- geometry validation context
- `sfm_region_replacement_mode`

실행 규칙:

- test view는 dataset split의 `test.txt`와 COLMAP pose metadata를 기준으로 구성한다
- validator는 training 중 랜덤 camera가 아니라 smoke snapshot과 동일한 test view 집합을 사용한다

### 5.2 Step 1: GT semantic mask 생성

입력:

- scene dataset root
- test camera poses
- target object ids
- width / height / hfov

처리:

- `ReplicaPointRenderer`를 사용해 각 test view에서 semantic map을 생성한다
- 각 target object id에 대해 binary mask를 만든다
  - `mask_gt[obj_id][view_name] = (semantic == obj_id)`
- point-sampling pinhole 완화를 위해 기본적으로 1회 `3x3 binary closing`을 적용한다

출력:

- `dict[int, dict[str, np.ndarray]]`

설계 원칙:

- GT mask는 "해당 view에서 실제로 보이는 object silhouette"를 의미한다
- 다른 object에 가려진 영역은 GT mask에 포함되지 않는다
- 기본 `sample_count = 1_000_000`으로 고정한다
- validator는 raw mask를 그대로 쓰지 않고, sampling artifact 완화를 위한 경량 postprocess만 허용한다

GT mask quality guard:

- `visible_pixel_count == 0`이면 해당 `(object, view)`는 `ignored_occluded`
- `visible_pixel_ratio < 0.001`이면 해당 `(object, view)`는 `ignored_occluded`
- closing 후에도 mask가 과도하게 분산되면 `gt_mask_low_confidence` 사유를 per-view 기록에 남긴다 (구체 기준은 calibration 단계에서 결정한다. 후보: connected component 수, mask fragmentation ratio)
- object 전체에서 valid view 수가 `min_views` 미만이면 최종 판정은 `FAIL` 또는 `AMBIGUOUS`가 아니라 기본적으로 `FAIL`로 본다

### 5.3 Step 2: prior-only render 생성

이 단계는 기존 문서의 `convex hull` 또는 단순 point projection을 대체한다.
기본 prior mask 생성 방식은 **prior-only render**로 고정한다.

Renderer capability 전제:

- 이 validator는 현재 repo가 사용하는 depth-enabled 3DGS renderer 포크를 전제로 한다
- validator는 `save_initial_snapshot()`가 저장한 PNG를 재사용하지 않는다
- validator는 별도 render helper에서 `render`와 `depth`를 직접 받아 사용한다
- 현재 renderer는 `gaussian_renderer.render(...)`에서 `render`, `radii`, `depth`를 반환하므로 이를 canonical source로 사용한다
- `depth`가 없는 환경에서는 v1에서 조용히 다른 방식으로 fallback하지 않고 `INPUT_MISMATCH` 또는 명시적 runtime error로 종료한다

왜 `convex hull`를 쓰지 않는가:

- 오목한 형상을 전부 볼록하게 메워 edge 위치가 왜곡된다
- 뒤쪽 Gaussian이나 빈 공간까지 mask에 포함된다
- 여러 view의 pixel-level evidence를 주 판정 신호로 쓰기에 너무 거칠다

#### 5.3.1 전체 prior render

입력:

- run에 실제로 삽입된 aligned prior 전체
- test camera set

처리:

- `prior_init/metadata.json`의 `selected_priors[*].aligned_prior`를 canonical source로 사용한다
- 빈 `GaussianModel(max_sh_degree=3)`에서 시작한다
- 첫 번째 aligned prior PLY는 `GaussianModel.load_ply()`로 직접 로드한다
- 나머지 aligned prior PLY는 vertex array를 읽어 `append_gaussian_vertex_to_model()`로 이어붙인다
- `initialize_loaded_prior()`를 호출해 exposure mapping, `max_radii2D`, `spatial_lr_scale`를 렌더 가능한 상태로 맞춘다 (기존 함수: `scripts/train_vanilla_3dgs_backend.py:initialize_loaded_prior()`. 이 함수는 `train_cam_infos`와 `cameras_extent`를 인자로 요구하므로, validator는 test camera metadata에서 이 두 값을 구성해야 한다)
- background는 black으로 고정한다
- camera set은 smoke snapshot과 동일한 test view를 사용한다
- gaussian renderer를 사용해 full-prior RGB와 depth를 render한다

출력:

- `full_prior_rgb[view_name]`
- `full_prior_depth[view_name]`

#### 5.3.2 object별 isolated prior render

입력:

- target object별 aligned prior
- 동일한 test camera set

처리:

- object 하나당 빈 `GaussianModel(max_sh_degree=3)`를 새로 만든다
- 해당 object의 `aligned_prior_XX.ply` 하나만 `load_ply()`로 로드한다
- full scene의 `protected_index_start/end`를 역으로 잘라 isolated scene을 만들지 않는다
- 같은 camera / 같은 renderer setting으로 object별 isolated render를 만든다

출력:

- `isolated_prior_rgb[obj_id][view_name]`
- `isolated_prior_depth[obj_id][view_name]`

### 5.4 Step 3: prior visible mask 생성

object별 prior mask는 다음 규칙으로 만든다.

1. `isolated_prior_depth > 0`인 픽셀을 isolated candidate로 잡는다
2. 같은 픽셀에서 `abs(isolated_prior_depth - full_prior_depth) <= depth_visibility_epsilon_m`을 만족할 때만 visible prior로 인정한다
3. 최종 object mask:
   - `mask_prior[obj_id][view_name] = isolated_visible_mask`

기본값:

- `depth_visibility_epsilon_m = 0.02`

의미:

- object를 따로 렌더링하되, 실제 full-prior render에서 앞에 보이는 부분만 남긴다
- 이렇게 하면 multi-object run에서도 prior 간 가림을 반영할 수 있다

추가 규칙:

- binary mask는 `depth > 0`를 기준으로 만든다
- RGB intensity threshold는 기본 마스크 생성 기준으로 사용하지 않는다
- antialiasing은 mask 경계 일관성을 위해 기본적으로 끈다
- full-prior와 isolated render는 반드시 같은 camera set, 같은 background, 같은 antialiasing 설정을 사용한다

### 5.5 Step 4: Per-view, Per-object metric 계산

각 `(object, view)` 쌍에 대해 아래 metric을 계산한다.

| Metric | 정의 | 역할 |
|--------|------|------|
| Mask IoU | `intersection(gt_mask, prior_mask) / union(gt_mask, prior_mask)` | 전체 silhouette 정합도 |
| BBox IoU | `IoU(bbox(gt_mask), bbox(prior_mask))` | 위치 범위 정합도 |
| Centroid Distance (px) | `||centroid(gt_mask) - centroid(prior_mask)||_2` | 중심 이동량 |
| Edge Distance (px) | symmetric contour chamfer distance | edge 위치 정합도 |
| Coverage Ratio | `sum(gt_mask ∧ prior_mask) / sum(gt_mask)` | GT 가시 영역 커버 보조 지표 |

`Edge Distance`는 다음 방식으로 계산한다.

- GT mask contour와 prior mask contour를 각각 추출한다
- 두 contour point set 사이의 symmetric chamfer distance를 pixel 단위로 계산한다

### 5.6 valid / ignored / invalid view 분류

각 view는 다음 셋 중 하나로 분류한다.

- `valid`
  - GT object visible area가 충분하고 prior mask도 정상 생성됨
- `ignored_occluded`
  - GT visible pixel 수가 너무 작거나 prior visible pixel 수가 너무 작음
- `invalid_input`
  - render/mask 생성 실패, metadata mismatch, camera mismatch 등

기본값:

- `min_visible_pixel_ratio = 0.001`

### 5.7 Step 5: Multi-view 집계와 최종 판정

object-level 집계:

- `valid` views만 사용한다
- object별 최종 metric은 median을 기본 집계값으로 쓴다
- severe outlier view 개수도 함께 기록한다 (구체 기준은 calibration 단계에서 결정한다. 후보: 단일 view에서 mask IoU < 0.1 또는 centroid distance > 50px)

run-level 최종 상태:

- `PASS`
  - 모든 target object가 threshold 충족
  - 모든 target object가 `min_views` 이상 valid view 확보
  - severe outlier view 비율이 허용 범위 내
- `FAIL`
  - 하나 이상의 object가 threshold를 명확히 위반
  - 또는 valid view 수가 최소 기준 미달
- `AMBIGUOUS`
  - threshold 근처의 borderline
  - object별 metric이 상충
  - valid view는 충분하지만 view 간 일관성이 낮음 (구체 기준은 calibration 단계에서 결정한다. 후보: valid view metric의 IQR 또는 std 기반 분산 threshold)
- `INPUT_MISMATCH`
  - source-of-truth 충돌 또는 camera / metadata resolve 실패

기본값:

- `mask_iou_threshold = 0.50`
- `bbox_iou_threshold = 0.60`
- `centroid_threshold_px = 15.0`
- `edge_threshold_px = 12.0`
- `min_views = 3`

운영 원칙:

- 기본 smoke는 `PASS` 또는 `FAIL`까지 자동 판정되는 것을 목표로 한다
- 수동 검토는 `AMBIGUOUS` 또는 `INPUT_MISMATCH`에만 요구한다

---

## 6. Threshold 정책

### 6.1 Global family threshold

threshold는 scene별이 아니라 **dataset family 단위 공통값**으로 관리한다.

적용 단위:

- `replica_multi_roomwide_v2_384_surface_rgb_*` 계열 전체

명시적 비채택:

- per-scene threshold
- per-category threshold

이유:

- 운영 복잡도를 줄인다
- scene마다 다른 기준을 두면 smoke gate 의미가 약해진다

### 6.2 Calibration 절차

초기 calibration은 기존 결과를 사용한다.

bootstrap corpus:

1. known-bad repro
   - `03-24-prior50k-geo-15k-2026/room_0`
2. known-good prior smoke
   - `surface_rgb_roomcontained_prior_100k_geo_smoke_1000/room_0`
3. baseline smoke
   - `surface_rgb_roomcontained_baseline_smoke_1000/room_0`

절차:

1. 세 run에서 전체 test view 집합과 동일 target mapping 기준으로 metric 분포를 수집
2. known-bad와 known-good를 가장 잘 분리하는 threshold를 family 공통값으로 고정
3. 고정된 threshold를 별도 note와 validator 기본값에 반영

threshold calibration 결과는 다음 문서에 기록한다.

- `docs/notes/{MM-DD}_prior_position_validation_thresholds_{family}_{YYYY}.md`

현재 문서의 기본값은 **bootstrap default**이며, calibration note가 나오면 그 값을 우선한다.

View 정책:

- gate와 calibration의 기본 기준은 full test set이다
- 현재 `room_0` roomcontained smoke의 test split은 64 views이므로, 4-object run 기준 예상 render 수는 full-prior 64회 + isolated 256회 = 총 320회다
- 이 비용은 smoke gate 용도로 수용 가능한 수준으로 본다
- `max_views` 또는 `view_stride` 같은 옵션은 디버그 전용 override로만 허용하며, 기본 smoke 판정과 threshold calibration에는 사용하지 않는다

---

## 7. Smoke Gate 통합

### 7.1 통합 위치

validator는 training loop 내부 hard hook이 아니라 **iter_0 smoke gate**로 통합한다.

순서:

1. prior insertion 및 기존 3D geometry validation
2. `save_initial_snapshot`로 `iter_0` test renders 생성
3. `validate_prior_positions.py` 실행
4. `PASS / FAIL / AMBIGUOUS / INPUT_MISMATCH` 기록

### 7.2 운영 정책

- `PASS`
  - smoke 통과
- `FAIL`
  - smoke 실패
- `AMBIGUOUS`
  - smoke는 자동 통과시키지 않는다
  - overlay와 per-object report를 근거로 제한적 수동 검토 수행
- `INPUT_MISMATCH`
  - smoke 실패
  - metadata / camera / artifact 정합성부터 수정

### 7.3 수동 검토를 허용하는 예외 조건

다음 경우에만 사람이 직접 확인한다.

1. `AMBIGUOUS`
2. `INPUT_MISMATCH`
3. calibration note를 새로 갱신하는 threshold 재설정 단계

즉, 정상 운영에서 `PASS` 또는 `FAIL` run을 사람이 매번 다시 확인하는 절차는 두지 않는다.

---

## 8. 구현 구조

### 8.1 신규 모듈

```text
src/priorprobe/validation/
    __init__.py
    prior_position_validator.py
```

### 8.2 핵심 함수

```python
def resolve_position_validation_inputs(
    backend_run_dir: Path,
) -> PositionValidationInputs:
    """Resolve canonical inputs from backend_run.json, prior_init/metadata.json, and prior_specs.json."""


def generate_gt_semantic_masks(
    inputs: PositionValidationInputs,
    *,
    sample_count: int = 1_000_000,
    apply_binary_closing: bool = True,
) -> dict[int, dict[str, np.ndarray]]:
    """Render GT semantic masks for each target object and test view."""


def render_full_prior_views(
    inputs: PositionValidationInputs,
) -> dict[str, PriorRenderFrame]:
    """Render all aligned priors together for all test views using the depth-enabled renderer."""


def render_isolated_prior_views(
    inputs: PositionValidationInputs,
) -> dict[int, dict[str, PriorRenderFrame]]:
    """Render each aligned prior object independently for all test views."""


def build_visible_prior_masks(
    full_renders: dict[str, PriorRenderFrame],
    isolated_renders: dict[int, dict[str, PriorRenderFrame]],
    *,
    depth_visibility_epsilon_m: float = 0.02,
) -> dict[int, dict[str, np.ndarray]]:
    """Keep only per-object pixels that are visible in the full prior render."""


def compute_position_metrics(
    gt_masks: dict[int, dict[str, np.ndarray]],
    prior_masks: dict[int, dict[str, np.ndarray]],
    *,
    min_visible_pixel_ratio: float = 0.001,
) -> dict[int, ObjectPositionMetrics]:
    """Compute per-view and per-object position metrics together with GT mask quality fields."""


def validate_prior_positions(
    backend_run_dir: Path,
    *,
    mask_iou_threshold: float = 0.50,
    bbox_iou_threshold: float = 0.60,
    centroid_threshold_px: float = 15.0,
    edge_threshold_px: float = 12.0,
    min_views: int = 3,
) -> PositionValidationResult:
    """Run the full multi-view validator and emit PASS / FAIL / AMBIGUOUS / INPUT_MISMATCH."""
```

### 8.3 스크립트

```text
scripts/validate_prior_positions.py
```

역할:

- CLI entrypoint
- JSON report 저장
- overlay artifact 저장
- exit code와 summary 출력

---

## 9. 출력 형식

### 9.1 출력 artifact

필수 출력:

- `summary.json`
- `per_object_metrics.json`
- `per_view_metrics.json`
- `contact_sheet.png`
- `overlays/`

권장 출력:

- `objects/{object_id}_contact_sheet.png`
- `ambiguous_views/`

### 9.2 JSON report 필수 필드

```json
{
  "scene_id": "room_0",
  "dataset_family": "replica_multi_roomwide_v2_384_surface_rgb_roomcontained",
  "backend_run_dir": "...",
  "validator_version": "v1",
  "decision": "PASS",
  "decision_reasons": [],
  "renderer_capabilities": {
    "depth_available": true
  },
  "view_policy": {
    "full_test_set_used": true
  },
  "thresholds": {
    "mask_iou": 0.50,
    "bbox_iou": 0.60,
    "centroid_px": 15.0,
    "edge_px": 12.0,
    "min_views": 3
  },
  "input_consistency": {
    "status": "OK"
  },
  "gt_mask_quality": {
    "sample_count": 1000000,
    "binary_closing": true
  },
  "render_cost_summary": {
    "test_view_count": 64,
    "target_object_count": 4
  },
  "geometry_validation_context": {
    "sfm_region_replacement_mode": "aligned_prior_aabb_union"
  },
  "objects": {
    "77": {
      "decision": "PASS",
      "median_mask_iou": 0.72,
      "median_bbox_iou": 0.81,
      "median_centroid_distance_px": 4.3,
      "median_edge_distance_px": 5.1,
      "valid_view_count": 12
    }
  }
}
```

---

## 10. 테스트와 승인 기준

### 10.1 unit test

반드시 추가할 테스트:

- backend run dir에서 canonical input resolve
- metadata mismatch 시 `INPUT_MISMATCH` 반환
- GT semantic mask 생성
- full-prior / isolated prior render 생성
- visible prior mask 구성
- IoU / centroid / bbox / edge metric 계산

### 10.2 regression test

다음 비교가 재현되어야 한다.

1. known-bad repro run은 known-good run보다 일관되게 나쁜 metric을 보여야 한다
2. known-good run은 대부분의 target object가 `PASS`를 받아야 한다
3. baseline smoke는 prior validator의 대상 object가 없거나 별도 no-prior 상태로 처리되어야 하며, 이 경우 명시적 상태를 남겨야 한다

### 10.3 smoke acceptance 기준

다음이 모두 만족되어야 한다.

1. 정상 smoke run에서 validator가 자동으로 최종 상태를 산출한다
2. `PASS`와 `FAIL`은 반복 실행해도 안정적으로 유지된다
3. `AMBIGUOUS`는 소수 borderline 케이스에 한정된다
4. 사람이 매번 모든 run을 다시 열어보지 않아도 된다

---

## 11. 제한 사항과 향후 확장

현재 설계에서 의도적으로 남기는 제한:

- threshold는 bootstrap default로 시작하고 calibration note로 갱신한다
- validator의 주 적용 시점은 smoke gate이며, full training run gate까지는 바로 확장하지 않는다

향후 확장:

1. calibration corpus를 `office_0` 등으로 확대
2. family-wide threshold 재고정
3. full training report pipeline과 자동 연동
4. 필요 시 prior-only render의 alpha-aware silhouette 추출 추가

현재 단계에서는 위 확장을 미리 구현 목표로 넣지 않는다.
우선은 **multi-view 2D evidence를 기반으로 한 자동 smoke gate**를 안정화하는 데 집중한다.
