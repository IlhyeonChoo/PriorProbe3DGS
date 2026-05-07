# Prior Insertion Geometry Fix Plan

Date: 2026-04-04

이전 문서:
- `docs/notes/03-24_phase5_surface_alignment_bug_2026.md`
- `docs/experiment_results/03-25_phase5_surface_alignment_fix_analysis_2026.md`
- `docs/experiment_plans/03-23_phase5_surface_rgb_prior_insertion_2026.md`
- `docs/experiment_plans/03-31_baseline_surface_rgb_determinism_2026.md`

이 문서에서 지금 즉시 고정하기 어려운 값(대표 object 최종 선택, geometry threshold 수치, smoke 최소 iteration, 수정 전 비교 run path 등)은 임의로 추정하지 않는다.
이런 항목은 아래 우선순위로 확정한다.

1. 위 이전 문서에 기록된 관찰과 결론
2. 대응하는 기존 artifact
   - `outputs/gaussian_direct/experiments/**/backend_run.json`
   - `prior_init/metadata.json`
   - `prior_specs.json`
3. Phase A에서 새로 수집한 측정값

실행 중 확정된 값은 같은 문서에 append하거나, 해당 smoke/result 문서의 서두에 명시하여 이후 해석과 재실행 기준이 흔들리지 않게 한다.

---

## 1. 목적

현재 gaussian-direct prior 삽입 경로에서 다음 문제가 다시 발생하거나, 아직 충분히 방지되지 않은 것으로 의심된다.

1. 내부 inspection에서 prior가 보이지 않거나 target과 다른 위치/방향/크기로 보임
2. 공간 외부에서 렌더링하면 비어 있어야 할 공간에 prior가 보임
3. 방 외부로 prior 일부가 삐져나옴
4. `alignment payload` 상으로는 정상처럼 보여도, 실제 `aligned_prior_*.ply` 또는 `iter_0 prior_points.ply` 기준으로는 잘못 배치됨

이 계획의 목표는 다음 두 가지를 분리해서 해결하는 것이다.

- A. prior가 실제로 올바른 위치/방향/크기로 삽입되는가
- B. 올바른 삽입 이후에도 성능 저하가 있다면, 그것은 geometry correctness 문제가 아니라 간섭/보호/SH mismatch 문제인가

이번 작업에서는 우선 A를 닫는다.

---

## 2. 현재까지 확인된 배경

### 2.1 이미 확인된 과거 버그

`docs/notes/03-24_phase5_surface_alignment_bug_2026.md`에서 확인된 과거 root cause:

- 정렬 기준: canonical seed frame
- 실제 삽입: scene/world frame의 원본 `splat.ply`
- 결과: 위치가 1.1m~6.0m까지 어긋난 legacy invalid result 발생

즉, 이 branch에서는 alignment representation과 insertion representation이 다를 수 있으므로, 둘의 계약을 잘못 다루면 같은 유형의 버그가 다시 발생한다.

### 2.2 현재 코드상 의심 지점

#### (1) alignment 기준 bbox와 실제 insertion asset bbox 불일치 가능성

`scripts/run_experiment.py`의 `_resolve_prior_entry_assets()`는:

- canonical seed / canonical metadata를 읽고
- `scale_meters`가 존재하면 `canonical_metadata["bbox_size"]`를 `scale_meters`로 override한다

그 다음:

- alignment 계산은 canonical seed와 이 bbox 기준으로 수행
- 실제 삽입은 `gaussian_direct`일 때 `source_prior_path`의 `splat.ply` 사용

따라서 아래 세 기준이 서로 다르면 실제 protrusion이 생길 수 있다.

- canonical seed bbox
- `scale_meters`
- 실제 source Gaussian의 bbox

#### (2) `oracle_target_box` 경로의 공간 sanity check 부족

`automatic` alignment는 다음을 검사한다.

- `outside_scene_ratio`
- `non_target_penetration_ratio`
- target overlap
- prior overlap

하지만 `oracle_target_box`는 target OBB에 맞춘 정렬 payload를 바로 생성하며, 실제 aligned prior가 room 밖으로 튀어나오는지까지는 사후 검증하지 않는다.

#### (3) 실제 삽입 결과 기준 검증 부재

`scripts/train_vanilla_3dgs_backend.py`의 `prepare_prior_asset()`는 실제 `aligned_prior_*.ply`를 생성한다.

하지만 현재는 다음을 fail-fast로 검증하지 않는다.

- 실제 aligned prior의 bbox / OBB가 target과 얼마나 차이 나는지
- 실제 aligned prior가 room bbox 밖으로 얼마나 나가는지
- alignment payload와 실제 aligned prior geometry가 일치하는지

즉, metadata 상 `center_error = 0`이라도 실제 insertion geometry는 틀릴 수 있다.

---

## 3. 작업 가설

이번 수정은 아래 가설 순서대로 검증한다.

### 가설 1. 스케일 기준이 잘못되었거나 일관되지 않다

증상과 가장 직접적으로 연결되는 지점이다.

우선 확인할 것:
- `scale_meters`
- `canonical_bbox_size`
- source Gaussian actual bbox
- prepared `aligned_prior_*.ply` actual bbox

### 가설 2. `oracle_target_box`가 실제 geometry protrusion을 놓치고 있다

특히 room boundary 근처 target, 큰 sofa/chair/lamp에서 문제를 일으킬 가능성이 높다.

### 가설 3. alignment payload는 맞지만 backend transform 결과가 실제 asset 기준으로는 다르다

`prepare_prior_asset()` / `transform_gaussian_vertex()` 수준에서 alignment payload와 실제 vertex-level result가 다를 가능성은 낮지만, 이번 작업에서는 명시적으로 닫는다.

---

## 4. 범위

### 4.1 직접 수정 후보

- `scripts/run_experiment.py`
- `src/priorprobe/insertion/alignment_search.py`
- `scripts/train_vanilla_3dgs_backend.py`
- 필요 시 `src/priorprobe/gaussian_affine.py`
- 필요 시 prior staging / manifest metadata 생성 경로

### 4.2 직접 검증 대상

- `prior_specs.json`
- `backend_run.json`
- `prior_init/metadata.json`
- `prior_init/aligned_prior_*.ply`
- `point_cloud/iteration_0/prior_points.ply`
- inspection viewer / initial snapshot viewer 산출물

### 4.3 이번 단계에서 하지 않을 것

- prior 성능 개선 자체를 먼저 논하지 않는다
- protection / SH reset / densification 정책을 먼저 건드리지 않는다
- pointcloud baseline 의미를 바꾸지 않는다

---

## 5. 작업 순서

## Phase A. 조사: 실제로 어디서 geometry가 어긋나는지 수치화

### A-1. 대표 object 2~3개 선정

선정 기준:
- 기존 실험에서 protrusion / ghost / 위치 어긋남이 실제 관찰된 object가 있으면 최우선 포함
- floor anchor object 1개 이상
- 크기가 큰 object 1개 이상(sofa/chair/table 우선)
- 가능하면 room boundary 근처 object 1개 포함

권장 시작점:
- `room_0`: lamp(obj_6), sofa(obj_9), chair(obj_74) 또는 sofa(obj_77)
- 필요 시 `office_0` 1개 추가

선정 확정 규칙:
- 우선 `03-24_phase5_surface_alignment_bug_2026.md`, `03-25_phase5_surface_alignment_fix_analysis_2026.md`, 관련 `backend_run.json`에서 실제 protrusion/ghost/offset 관찰이 남아 있는 object를 먼저 채택한다
- 위 문서만으로 최종 선택이 애매하면, Phase A 시작 시 기존 artifact inspection 결과를 보고 대표 object를 확정한다
- 최종 선정된 object 목록과 선정 근거는 같은 문서 append 또는 smoke 결과 문서 서두에 남긴다

### A-2. object별 4종 bbox 비교 진단 추가

각 object마다 아래를 같은 표로 비교한다.

1. source prior actual bbox
2. canonical seed bbox
3. alignment payload expected bbox
4. actual aligned prior bbox

동시에 기록할 값:
- target OBB size / center / bottom anchor
- actual aligned bbox center / size / bottom point
- center offset
- bottom offset
- room bbox 밖 비율
- target bbox 대비 protrusion 방향

### A-3. geometry 기준 결정에 필요한 비교

다음 차이를 수치로 뽑는다.
- `scale_meters` vs `canonical_bbox_size`
- `canonical_bbox_size` vs source Gaussian actual bbox
- source Gaussian actual bbox vs aligned prior actual bbox / target bbox

### A-4. 결과 판정

조사 단계 종료 조건:
- 위치 오류인지, 방향 오류인지, 스케일 오류인지, 외부 protrusion인지 object별로 분리됨
- `scale_meters` override가 root cause 후보인지 아닌지 판정 가능

### A-5. geometry 오차 threshold 확정

Phase A 조사 결과를 바탕으로 Phase B 수정 및 Phase D smoke 통과에 사용할 구체적 threshold를 확정한다.

확정 대상:
- center offset 허용 범위 (meters)
- bottom offset 허용 범위 (meters)
- room bbox 밖 비율 상한 (%)
- target bbox 대비 size 차이 허용 범위

원칙:
- Phase A에서 수집한 수치 분포를 기반으로 결정하되, 사용자와 합의 후 확정
- 확정된 threshold는 Phase D smoke 통과 기준에 그대로 반영
- 이 단계를 완료하기 전에 Phase B 수정 작업을 시작하지 않는다
- 지금 단계에서 threshold를 미리 숫자로 박기 어렵다면, `03-25_phase5_surface_alignment_fix_analysis_2026.md`와 기존 ambiguous run artifact를 1차 참조 기준으로 삼고, Phase A 측정 후 최종 수치로 고정한다
- 최종 threshold 표는 같은 문서 append 또는 `docs/notes/{MM-DD}_prior_insertion_geometry_smoke_{scene}_{YYYY}.md`에 기록하고, Phase D 시작 전에 경로를 명시한다

---

## Phase B. 수정: geometry 기준 일관화 + fail-fast 검증 추가

### B-1. 스케일 기준 일원화

우선 검토 우선순위:

1. `gaussian_direct`에서 실제 insertion asset을 대표하는 bbox를 alignment 계산에 사용하도록 맞출 수 있는가
2. `scale_meters`는 retrieval/feature metadata로만 두고, alignment scale 계산에서는 canonical bbox 또는 insertion-asset bbox를 사용해야 하는가
3. canonical seed bbox와 실제 insertion asset bbox가 다르면, manifest에 이를 명시적으로 추가해야 하는가

수정 원칙:
- alignment에 사용하는 bbox와 실제 insertion asset geometry 기준이 서로 모순되지 않아야 한다
- silent fallback보다 provenance에 명시적으로 남긴다

영향 범위 확인:
- scale_meters 기준이 변경될 경우, 기존에 scale_meters 기준으로 정렬된 과거 실험 결과와의 호환성이 깨질 수 있다
- 변경 전 기존 alignment payload가 몇 건 존재하는지, 재생성이 필요한지 확인한다
- 필요 시 migration 경로 또는 버전 구분 정책을 Phase B 수정 범위에 포함한다

### B-2. `oracle_target_box` 경로에 공간 sanity check 추가

정렬 payload를 만든 뒤 최소한 다음을 검사한다.

- actual aligned prior의 room bbox 밖 비율
- actual aligned prior bbox와 target bbox 차이
- 필요 시 non-target penetration

정책:
- dry-run / smoke 단계에서는 fail-fast 우선
- 실제 실험 실행 전 geometry 오류를 조기에 차단

### B-3. backend에서 실제 aligned prior 기준 검증 추가

`prepare_prior_asset()` 또는 `prepare_prior_assets()` 직후 실제 산출물 기준으로 다음을 계산/기록한다.

- actual aligned bbox min/max/center/size
- target bbox와의 center/bottom/size 오차
- room bbox 밖 비율(가능하면)
- geometry validation pass/fail

이 결과는 `prior_init/metadata.json`에도 남긴다.

### B-4. provenance 기록 보강

아래 항목은 선택이 아니라 필수 기록 대상으로 본다.

- alignment bbox source
  - `scale_meters`
  - `canonical_bbox_size`
  - `source_prior_actual_bbox`
  - `insertion_asset_bbox`
- actual aligned bbox summary
- geometry validation status

기록 위치:
- 반드시 `prior_init/metadata.json`
- 반드시 `outputs/gaussian_direct/experiments/**/backend_run.json`
- 가능하면 `prior_specs.json`에도 같은 핵심 요약을 남겨 smoke 전 provenance 확인 시 바로 대조 가능하게 한다

---

## Phase C. 테스트: 회귀 방지 장치 추가

### C-0. 기존 테스트 fixture 확인

Phase C 테스트 구현 전에 다음을 확인한다.

- 기존 synthetic Gaussian fixture가 존재하는지, 재사용 가능한지
- GPU 없이 실행 가능한 unit test 경로가 확보되어 있는지
- transform_gaussian_vertex() 등 핵심 함수의 기존 test coverage 수준

이 확인 결과에 따라 테스트 구현 난이도와 범위를 조정한다.

### C-1. `run_experiment.py` 테스트 보강

대상:
- `_resolve_prior_entry_assets()`
- alignment payload 생성 경로

추가 테스트:
- `scale_meters`와 `canonical_bbox_size`가 다를 때 어떤 기준을 써야 하는지 정책을 고정
- gaussian_direct에서 insertion asset bbox 기준이 alignment bbox와 다르면 감지되는지 검증

주의:
- 기존 `test_resolve_prior_entry_assets_prefers_scale_meters_over_canonical_bbox`는 이번 정책 변경 시 수정 대상이다.

### C-2. `alignment_search.py` 테스트 보강

추가 테스트:
- room bbox 밖으로 나가는 후보가 reject/drop 되는지
- boundary 근처 target에서 actual candidate bbox가 threshold를 넘으면 fail하는지
- automatic과 oracle_target_box가 동일 geometry sanity policy를 갖는지 확인

### C-3. backend transform 테스트 보강

대상:
- `prepare_prior_asset()`
- `transform_gaussian_vertex()`

추가 테스트:
- alignment payload가 주어진 synthetic Gaussian에서 actual aligned bbox가 기대값과 일치하는지
- payload 기준으로는 정상이나 actual aligned prior가 target을 벗어나는 synthetic case를 감지하는지

---

## Phase D. smoke 검증: geometry correctness만 먼저 확인

### 목적

성능 비교를 하기 전에 geometry correctness를 먼저 닫는다.

### smoke 대상

Comparison target:
- 수정 전 기준: `03-24_phase5_surface_alignment_bug_2026.md`, `03-25_phase5_surface_alignment_fix_analysis_2026.md`, 그리고 해당 문서들이 참조한 기존 `backend_run.json` 중 가장 최근의 ambiguous gaussian-direct run을 기준 run으로 고정한다
- 수정 후 기준: 위 기준 run과 같은 scene / dataset family / 대표 object / protection 조건을 유지한 geometry validation 통과 build
- 기준 run path가 문서만으로 바로 특정되지 않으면, Phase A 시작 시 기존 artifact를 대조해 1건으로 고정하고 smoke 문서 서두에 명시한다

Scene:
- `room_0` 우선
- 단, 기존 결과에서 `office_0`가 더 명확한 protrusion 재현 사례이면 그 run을 보조 검증 대상으로 추가한다

Dataset family:
- `replica_multi_roomwide_v2_384_surface_rgb_shared`

Iteration:
- 1차 geometry acceptance는 `iter_0` 산출물 기준으로 수행한다
- 추가 렌더 확인이 필요할 때만 최소 후속 iteration을 사용하며, 그 값은 `03-31_baseline_surface_rgb_determinism_2026.md`와 기존 alignment 관련 smoke/result를 참조해 가장 작은 재현 가능한 값으로 고정한다
- 최종 선택된 smoke iteration은 실행 전에 smoke 문서 서두에 명시한다

Prior insertion condition:
- `gaussian_direct`
- 기본 후보는 Phase A-1의 대표 object 1~2개로 고정한다
- 다만 기존 결과가 multi-object 조건에서만 문제를 안정적으로 재현했다면, 이전 실험 결과를 근거로 동일 multi-object 조건을 사용한다
- 어떤 조건을 채택했는지는 기준 run path와 함께 smoke 문서 서두에 기록한다

Protection:
- geometry correctness 확인이 목적이므로 protection은 최신 승인된 surface RGB gaussian-direct canonical config를 그대로 유지한다
- 값이 문서에서 바로 확정되지 않으면 `03-23_phase5_surface_rgb_prior_insertion_2026.md`와 대응 `backend_run.json`의 값을 기준으로 실행 직전 확정하고 기록한다

Output dir:
- 새 smoke 전용 output 디렉토리 사용
- 기존 결과 디렉토리 재사용 금지
- 네이밍 규칙은 `outputs/gaussian_direct/experiments/{date}_prior_geometry_smoke_{scene}_{condition}`로 고정한다

Report path:
- 중간 smoke 기록은 `docs/notes/{MM-DD}_prior_insertion_geometry_smoke_{scene}_{YYYY}.md`
- geometry correctness 통과 후 최종 요약은 `docs/experiment_results/{MM-DD}_prior_insertion_geometry_fix_{YYYY}.md`
- 어떤 문서를 먼저 쓰더라도 기준 run path, 수정 후 run path, 대표 object, threshold 표를 문서 서두에 명시한다

### smoke에서 반드시 확인할 것

- `prior_specs.json`의 provenance 일관성
- `prior_init/aligned_prior_*.ply` 생성 여부
- `prior_init/metadata.json`의 geometry validation 필드
- `iter_0 prior_points.ply`가 target 중심 근처에 실제 존재하는지
- **multi-pose iter_0 render triplet validation**
  - 같은 pose 집합에서 아래 3가지를 나란히 비교한다
    1. `test` GT / dataset render
    2. `baseline` iter_0 render
    3. `prior` iter_0 render
  - 최소 목표는 "prior가 baseline 대비 같은 물체를 같은 위치에 더 가깝게 두는가"를 보는 것이 아니라, **baseline과 prior가 동일한 room 구조 위에서 같은 물체 위치를 유지하는지**를 먼저 검증하는 것이다
  - 특히 table / sofa / lamp처럼 위치 어긋남이 보였던 object를 우선 확인한다
  - 비교는 최소 3개 이상 pose에서 수행하고, 가능하면 room 내부 각기 다른 시야(정면 / 측면 / 대각)로 고른다
  - 검증 결과는 contact sheet 또는 side-by-side image 형태로 저장한다
- inspection / viewer에서 (수동 확인, 스크린샷 기록 필수)
  - target 내부 또는 근처에 prior가 보이는지
  - 빈 공간에 뜬 prior가 없는지
  - room 밖 protrusion이 없는지
  - baseline과 prior 사이에서 table / sofa / lamp 위치가 미묘하게라도 어긋나지 않는지
  - 검증 스크린샷은 smoke 결과 문서에 첨부하여 사후 재현 가능하게 한다

### smoke 통과 기준

- representative object 기준 center/bottom 오차가 허용 범위 내
- actual aligned prior outside ratio가 허용 범위 내(가능하면 0 또는 매우 낮은 수준)
- inspection과 메타데이터가 서로 모순되지 않음
- 방 외부 렌더에서 prior artifact가 불필요하게 보이지 않음
- multi-pose iter_0 render triplet에서 baseline / prior 사이의 table / sofa / lamp 위치가 GT 기준으로 구조적으로 일치하고, prior 쪽만 따로 밀리거나 떠 보이는 object가 없어야 함
- 위 판단에 사용한 threshold 값과 비교 대상 run path가 smoke 문서에 함께 기록되어 있음

---

## Phase E. geometry correctness 통과 후 실험 재개

geometry correctness smoke가 통과한 뒤에만 다음으로 넘어간다.

1. 동일 조건 1-scene 재실행
2. 2-scene 교차 확인
3. 이후 baseline / prior 성능 비교 재개

이 순서를 지켜야 다음을 분리할 수 있다.
- geometry가 틀려서 생긴 성능 왜곡
- geometry는 맞지만 prior 자체가 간섭을 일으키는 문제

---

## 6. 성공 기준

이번 계획의 Definition of Done:

1. geometry correctness
- representative object에서 actual aligned prior가 target 근처에 올바르게 배치됨
- room 밖 protrusion이 재현되지 않음
- 빈 공간 prior ghost가 재현되지 않음

2. provenance correctness
- `source_prior_path`
- `canonical_seed_path`
- `insertion_source_path`
- `insertion_representation`
이 실제 삽입 결과와 모순되지 않음

3. regression protection
- 관련 unit/regression tests 추가 또는 수정
- smoke path가 재현 가능하게 문서화됨
- 기준 run path, 수정 후 run path, threshold 표, 대표 object 선정 근거가 문서에 남아 있음

4. 해석 분리
- 이후 성능 실험에서 geometry correctness 문제와 optimization/interference 문제를 분리해서 논할 수 있음

---

## 7. 우선순위

§3 가설 순서(가설 1 → 2 → 3)대로 진행한다.

각 가설에서 가장 먼저 확인할 구체 항목:

1. **가설 1 (스케일 기준)**: _resolve_prior_entry_assets()의 scale_meters override가 실제 insertion asset geometry와 맞는가
2. **가설 2 (oracle sanity check)**: oracle_target_box 경로가 actual aligned prior 기준 spatial sanity check 없이 통과시키는가
3. **가설 3 (backend transform)**: source Gaussian actual bbox와 canonical seed bbox가 얼마나 다르며, alignment payload 기준 transform 결과가 실제 vertex-level 결과와 일치하는가

---

## 8. 다음 실행 단위

이 문서 승인 후 실제 작업 시작 순서:

1. Phase A 조사 구현
2. 조사 결과 공유 및 수정 포인트 확정
3. Phase B 수정
4. Phase C 테스트
5. Phase D smoke 검증
6. 사용자 확인 후 후속 실험 진행
