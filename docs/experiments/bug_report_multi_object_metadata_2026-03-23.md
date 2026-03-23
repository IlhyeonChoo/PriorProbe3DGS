# Bug Report: Multi-Object Prior 삽입 시 Metadata 인덱싱 오류

Date: 2026-03-23

---

## 요약

Multi-object prior 삽입 시, 모든 prior entry의 metadata가 첫 번째 오브젝트(obj_6, lamp)의 metadata로 고정되는 버그. Gaussian vertex 데이터 자체는 4개 오브젝트에서 올바르게 준비되지만, merge loop에서 metadata 인덱싱이 잘못되어 4개 모두 동일한 metadata를 참조한다.

**영향 범위:** `_prior_25k_*`, `_prior_50k_*`, `_prior_100k_*` 등 multi-object gaussian prior를 사용하는 **모든 실험**

---

## 버그 위치

**파일:** `scripts/train_vanilla_3dgs_backend.py`
**위치:** Lines 1200-1218 (Scene.__init__ 내부 merge loop)

```python
# Line 1200
updated_selected_priors: list[dict[str, Any]] = []

# Lines 1201-1218
for init_path_value, init_format in zip(prepared_init_plys, prepared_init_formats):
    index = len(updated_selected_priors)       # ← BUG: 항상 0
    metadata_item = (
        dict(selected_priors_metadata[index])  # ← 항상 [0] = obj_6
        if index < len(selected_priors_metadata)
        else {
            "aligned_prior": str(init_path_value),
            "asset_format": init_format,
        }
    )
    if init_format == "gaussian":
        gaussian_vertex = np.array(
            PlyData.read(Path(init_path_value))["vertex"].data,
            copy=True,
        )
        gaussian_original_counts.append(int(gaussian_vertex.shape[0]))
        gaussian_raw_entries.append((gaussian_vertex, metadata_item))
        continue                               # ← updated_selected_priors에 append 안 함!
```

---

## 원인 분석

### 메커니즘

1. `updated_selected_priors`는 빈 리스트로 시작
2. Loop 매 iteration에서 `index = len(updated_selected_priors)`로 현재 인덱스를 계산
3. `init_format == "gaussian"`일 때 `continue`로 loop body를 종료
4. **`continue` 전에 `updated_selected_priors.append()`가 없음**
5. 따라서 `len(updated_selected_priors)`는 loop 내내 **0으로 유지**
6. 모든 iteration에서 `selected_priors_metadata[0]`을 참조 → **항상 첫 번째 오브젝트의 metadata**

### 왜 point cloud format에서는 문제가 없는가

Lines 1220-1237에서 `init_format != "gaussian"`인 경우를 처리한다. 이 경로에서는 `updated_selected_priors.append(updated_item)` (line 1230, 1237)이 호출되므로 인덱스가 정상적으로 증가한다. 버그는 **gaussian format에만 해당**한다.

### 후속 loop (Lines 1245-1267)에서의 전파

```python
for gaussian_index, (gaussian_vertex, metadata_item) in enumerate(gaussian_raw_entries):
    # gaussian_raw_entries에 이미 잘못된 metadata_item이 저장됨
    filtered_vertex, updated_item = apply_gaussian_insertion_policy(
        gaussian_vertex,
        metadata_item,  # ← 모두 obj_6 metadata
        ...
    )
```

`gaussian_raw_entries`에 저장된 `metadata_item`이 이미 잘못된 상태이므로, 이후 처리(`apply_gaussian_insertion_policy`)에도 전파된다.

---

## 영향

### 1. Subsample seed 동일화 (데이터 영향)

`apply_gaussian_insertion_policy()` → `prior_sample_seed()` (line 750)에서 metadata의 `target_object_id`, `prior_object_id`, `aligned_prior` 필드를 seed 계산에 사용한다:

```python
def prior_sample_seed(prepared_item: dict[str, Any], *, base_seed: int) -> int:
    return stable_seed(
        int(base_seed),
        prepared_item.get("target_object_id", ""),
        prepared_item.get("prior_object_id", ""),
        prepared_item.get("aligned_prior", ""),
    )
```

4개 entry 모두 동일한 metadata를 갖기 때문에 **동일한 subsample seed**가 생성된다. 각 오브젝트의 vertex 데이터는 다르지만, 서브샘플링 패턴이 비정상적으로 동일해진다.

### 2. metadata.json 오염

`write_prior_metadata()` (line 1297-1308)가 `updated_selected_priors`로 metadata.json을 **덮어쓴다**. 이 두 번째 호출이 line 1450-1457의 첫 번째 호출(정확한 `prepared` 데이터 사용)을 덮어쓰므로, 최종 metadata.json에는 잘못된 데이터가 기록된다.

### 3. prior_protection.json 오염

`configure_prior_protection()` (line 1292-1296)에 `updated_selected_priors`가 전달되어, protection 기록에도 모든 range가 obj_6으로 기록된다.

### 4. Vertex 데이터는 정상일 가능성

PLY 파일 자체는 `prepare_prior_assets()`에서 올바르게 준비된다 (MD5 해시가 4개 모두 다름). Vertex 데이터는 정확한 PLY에서 읽힌다 — **데이터 준비까지는 정상**. 그러나 동일한 subsample seed가 적용되므로, 서브샘플링 결과의 다양성이 줄어든다.

---

## 증거

### 1. metadata.json — 4개 entry 모두 obj_6

`outputs/.../prior_init/metadata.json` (25K 실험, room_0):

```
selected_priors[0]: prior_object_id = "replica_room_0_obj_6", aligned_prior = "aligned_prior_00.ply"
selected_priors[1]: prior_object_id = "replica_room_0_obj_6", aligned_prior = "aligned_prior_00.ply"
selected_priors[2]: prior_object_id = "replica_room_0_obj_6", aligned_prior = "aligned_prior_00.ply"
selected_priors[3]: prior_object_id = "replica_room_0_obj_6", aligned_prior = "aligned_prior_00.ply"
```

기대값: obj_6, obj_9, obj_77, obj_74 (각각 다른 오브젝트)

### 2. prior_specs.json — 정상 (4개 서로 다른 오브젝트)

```
specs[0]: object_id = "replica_room_0_obj_6"  (lamp)
specs[1]: object_id = "replica_room_0_obj_9"  (sofa)
specs[2]: object_id = "replica_room_0_obj_77" (sofa)
specs[3]: object_id = "replica_room_0_obj_74" (chair)
```

→ 버그는 spec 생성 이후, merge loop에서 발생

### 3. aligned PLY 파일 — MD5 해시 모두 다름

```
aligned_prior_00.ply: 2286ddd845f3434eaf1a5ab4b2a30cc8
aligned_prior_01.ply: dcff7599f0decb1d31d725b4148e5596
aligned_prior_02.ply: b2a217f02d226a239710614068de5b82
aligned_prior_03.ply: 476ec6a2f7606b82860e5e9530cc6003
```

→ PLY 준비는 정상. 데이터는 4개 오브젝트에서 올바르게 변환됨

### 4. prior_protection.json — 모든 range가 obj_6

```json
"protected_ranges": [
    {"prior_object_id": "replica_room_0_obj_6", "target_object_id": 6, ...},
    {"prior_object_id": "replica_room_0_obj_6", "target_object_id": 6, ...},
    {"prior_object_id": "replica_room_0_obj_6", "target_object_id": 6, ...},
    {"prior_object_id": "replica_room_0_obj_6", "target_object_id": 6, ...}
]
```

### 5. 사용자 시각적 확인

iter_0 렌더링에서 lamp(obj_6) 위치에만 삽입 흔적이 보이고, sofa(obj_9), sofa(obj_77), chair(obj_74) 위치는 baseline과 동일. 25K, 50K 실험 모두 동일한 패턴.

---

## 파이프라인 정상/비정상 구간 요약

```
[정상] run_experiment.py: prior retrieval → 4개 서로 다른 오브젝트 선택
         ↓
[정상] run_experiment.py: prior_specs.json 생성 → 4개 올바른 entry
         ↓
[정상] train_backend.py: load_prior_specs() → specs 로드
         ↓
[정상] train_backend.py: prepare_prior_assets() → 4개 서로 다른 PLY 생성
         ↓
[정상] train_backend.py: 첫 번째 write_prior_metadata() → 올바른 prepared 데이터 기록
         ↓
[★ BUG] train_backend.py: Scene.__init__ merge loop → index가 0으로 고정
         ↓
[비정상] gaussian_raw_entries: 4개 모두 obj_6 metadata
         ↓
[비정상] apply_gaussian_insertion_policy(): 동일 seed로 서브샘플링
         ↓
[비정상] 두 번째 write_prior_metadata(): 잘못된 metadata로 덮어쓰기
         ↓
[비정상] metadata.json, prior_protection.json: 모두 obj_6으로 기록
```

---

## 수정 방향

### 핵심 수정

Line 1202의 `index` 계산이 gaussian format entry도 카운트하도록 변경해야 한다.

**방법 A: enumerate 사용**

```python
for loop_index, (init_path_value, init_format) in enumerate(
    zip(prepared_init_plys, prepared_init_formats)
):
    metadata_item = (
        dict(selected_priors_metadata[loop_index])
        if loop_index < len(selected_priors_metadata)
        else {
            "aligned_prior": str(init_path_value),
            "asset_format": init_format,
        }
    )
    ...
```

**방법 B: 별도 카운터**

```python
metadata_index = 0
for init_path_value, init_format in zip(prepared_init_plys, prepared_init_formats):
    metadata_item = (
        dict(selected_priors_metadata[metadata_index])
        if metadata_index < len(selected_priors_metadata)
        else ...
    )
    metadata_index += 1
    ...
```

### 추가 수정

두 번째 `write_prior_metadata()` (line 1297-1308)이 첫 번째 호출을 덮어쓰는 문제도 정리 필요. 첫 번째 호출(line 1450-1457)은 정확한 데이터를 쓰지만, merge loop 이후의 두 번째 호출이 이를 덮어쓴다.

---

## 수정 후 필요한 작업

1. **모든 multi-object prior 실험 재실행** — 기존 결과는 실질적으로 1-object 삽입에 가까운 조건
2. **재실행 후 기존 결론 재검증** — "A 25K가 최선", "조합이 가산적이지 않음" 등의 결론이 유효한지 확인
3. **Phase 3 결과 재검토** — full_none, lr10, lr01 모두 동일 버그의 영향을 받음
4. **Office_0 교차 검증은 버그 수정 후 실행**

---

## 영향을 받는 실험 목록 (room_0)

| 실험 | 영향 |
|------|------|
| `*_prior_25k_15000` (A 25K) | O |
| `*_prior_25k_sh_zero_15000` (A+C) | O |
| `*_prior_25k_replace_region_15000` (A+B) | O |
| `*_prior_25k_replace_region_sh_zero_15000` (A+B+C) | O |
| `*_prior_25k_lr01_15000` (Phase 3) | O |
| `*_prior_25k_lr10_15000` (Phase 3) | O |
| `*_prior_25k_full_none_15000` (Phase 3) | O |
| `*_prior_50k_15000` | O |
| `*_prior_100k_15000` (100K, none) | O |
| `*_baseline_*` (baseline) | X (prior 미사용) |

---

## 열린 질문

**Q: Vertex 데이터 자체는 4개 오브젝트가 모두 삽입되는가?**

PLY 파일은 4개가 별도로 준비되며 MD5도 다르다. `PlyData.read()`는 각각의 PLY를 올바르게 읽는다. 따라서 **vertex 데이터 자체는 4개 오브젝트가 모두 append될 가능성이 높다**. 그러나 metadata가 잘못되어:
- subsample seed가 동일 → 서브샘플링 결과가 의도와 다름
- 시각적으로 lamp만 보이는 것이 "다른 3개 오브젝트의 vertex가 잘못된 위치에 있다"는 뜻인지, "올바른 위치에 있지만 시각적으로 구분이 어려운 것"인지 추가 확인이 필요하다.

가장 확실한 검증: 버그 수정 후 동일 조건 재실행 → iter_0 렌더링 비교.
