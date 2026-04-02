# outputs/gaussian_direct/ 내부 파일 참조 업데이트 계획

**Date:** 2026-04-02
**Branch:** `exp/gaussian-direct`
**선행 조건:** `scripts/rename_to_date_format.py` 의 디렉토리 리네이밍 (아직 미실행)

---

## 배경

디렉토리 리네이밍(`surface_rgb_baseline_15000` → `03-24-baseline-15k-2026`)은 스크립트가 준비되어 있지만,
**디렉토리 내부 파일들이 OLD 이름을 문자열로 참조**하고 있어 리네이밍 후 불일치가 발생한다.
이 문서는 어떤 파일의 어떤 필드가 OLD 이름을 갖고 있는지 조사한 결과와, 이를 일괄 수정하기 위한 계획을 정리한다.

---

## 1. 조사 결과: OLD 이름을 참조하는 파일 현황

### 1-1. `backend_run.json` — 205개 (legacy 제외)

experiments/ 하위 각 scene 디렉토리에 1개씩 존재.

| 필드 | 참조 형태 | 예시 값 |
|------|-----------|---------|
| `experiment_name` | 이름 문자열 | `"gaussian_direct_surface_rgb_baseline_15000"` |
| `storage_experiment_name` | 이름 문자열 | `"surface_rgb_baseline_15000"` |
| `model_path` | 절대 경로 | `".../backend_runs/surface_rgb_baseline_15000/room_0"` |
| `command[]` | 절대 경로 (배열 원소) | `".../backend_runs/surface_rgb_baseline_15000/room_0"` |

`command[]`는 학습 실행 시 사용된 인자 기록이므로 경로가 여러 원소에 분산되어 있다.

### 1-2. `evaluation.json` — 189개

| 필드 | 참조 형태 | 예시 값 |
|------|-----------|---------|
| `experiment_name` | 이름 문자열 | `"gaussian_direct_surface_rgb_baseline_15000"` |
| `model_path` | 절대 경로 | `".../backend_runs/surface_rgb_baseline_15000/room_0"` |

### 1-3. `prior_specs.json` — 114개

prior를 삽입한 실험에만 존재.

| 필드 | 참조 형태 | 예시 값 |
|------|-----------|---------|
| `alignment_json` | 절대 경로 | `".../experiments/surface_rgb_prior_100k_geo_15000/room_0/generated_alignment_*.json"` |
| `alignment_debug.source_prior_path` | 절대 경로 | prior_library 경로 (`replica_target_surface_exact_trained_clip` 포함) |

### 1-4. `cfg_args` — 64개

backend_runs/ 하위 각 scene에 1개씩. **JSON이 아니라 Python `Namespace(...)` 형식.**

| 필드 | 참조 형태 | 예시 값 |
|------|-----------|---------|
| `model_path` | 절대 경로 | `model_path='.../backend_runs/surface_rgb_baseline_15000/room_0'` |

`source_path`는 데이터셋 경로이므로 리네이밍 대상 아님.

### 1-5. CSV 리포트 — ~27개 (legacy 제외)

reports/ 디렉토리의 CSV 파일들. `experiment_name` 칼럼에 OLD 이름이 데이터로 들어 있음.

| 칼럼 | 참조 형태 | 예시 값 |
|------|-----------|---------|
| `experiment_name` | 이름 문자열 | `"gaussian_direct_surface_rgb_baseline_15000"` |

OLD 이름이 포함된 CSV 파일 수:
- `gaussian_direct_` 패턴: **27개**
- `surface_rgb_` 패턴: **10개** (non-legacy)
- `same_scene_` 패턴: **13개**

### 1-6. Prior manifest — 1개

`prior_library/replica_target_surface_exact_trained_clip_manifest.json`

| 필드 | 참조 형태 | 예시 값 |
|------|-----------|---------|
| `metadata.tags[]` | 태그 배열 | `["same_scene_exact", "surface_rgb"]` |
| `metadata.extras.prior_source` | 이름 문자열 | OLD 이름 |

### 1-7. PLY symlink (backend_runs)

`backend_runs/*/scene/point_cloud/iteration_*/` 에서 `point_cloud.ply` → `{old_label}_iter_N.ply` symlink 존재.
PLY 파일명 자체에 실험 라벨이 인코딩되어 있으나, `result_ply_naming.py`에서 생성하는 라벨이므로
리네이밍과 직접 관련은 없다 (디렉토리 이름이 아닌 라벨 기반).

---

## 2. 영향도 요약

| 파일 유형 | 파일 수 | 참조 형태 | 수정 난이도 |
|-----------|---------|-----------|------------|
| `backend_run.json` | 205 | 이름 + 경로 | 중 (JSON 필드별 치환) |
| `evaluation.json` | 189 | 이름 + 경로 | 중 |
| `prior_specs.json` | 114 | 경로 | 중 |
| `cfg_args` | 64 | 경로 (Namespace 텍스트) | 하 (문자열 치환) |
| CSV 리포트 | ~27 | 이름 (칼럼 데이터) | 하 (칼럼값 치환) |
| Prior manifest | 1 | 태그/이름 | 하 |
| **합계** | **~600개** | | |

---

## 3. 수정 계획

### 3-1. 원칙

- `rename_to_date_format.py`가 생성하는 `old→new` 매핑을 그대로 재사용
- **실행 순서: 내부 참조 먼저 수정 → 디렉토리 리네이밍** (리네이밍 후에는 파일 위치가 바뀌므로)
- `legacy_bugged_*` 내부 파일은 건드리지 않음
- dry-run 모드를 기본으로 하여 변경 내용을 먼저 확인

### 3-2. 매핑 종류

`rename_to_date_format.py`의 `transform_dir_name()`, `transform_prior_name()` 함수를 import하여 생성.

| 매핑 이름 | 예시 (old → new) | 용도 |
|-----------|-------------------|------|
| **dir_map** | `surface_rgb_baseline_15000` → `03-24-baseline-15k-2026` | `storage_experiment_name`, `model_path` 경로 내 치환 |
| **full_map** | `gaussian_direct_surface_rgb_baseline_15000` → `03-24-baseline-15k-2026` | `experiment_name` 필드 치환 |
| **prior_map** | `replica_target_surface_exact_trained_clip` → `03-24-target-surface-trained-2026` | prior_specs 경로, manifest 치환 |

`full_map`은 `dir_map`의 각 키에 `gaussian_direct_` prefix를 붙여 생성하면 된다.

### 3-3. 파일별 수정 방법

#### A. `backend_run.json`

```python
data["experiment_name"] = full_map.get(data["experiment_name"], data["experiment_name"])
data["storage_experiment_name"] = dir_map.get(data["storage_experiment_name"], data["storage_experiment_name"])
data["model_path"] = replace_path_segments(data["model_path"], dir_map)
data["command"] = [replace_path_segments(arg, dir_map) for arg in data["command"]]
```

#### B. `evaluation.json`

```python
data["experiment_name"] = full_map.get(data["experiment_name"], data["experiment_name"])
data["model_path"] = replace_path_segments(data["model_path"], dir_map)
```

#### C. `prior_specs.json`

```python
# 경로 내 experiments/ 하위 dir name 치환
data["alignment_json"] = replace_path_segments(data["alignment_json"], dir_map)
# prior_library/ 하위 dir name 치환
deep_replace_path_segments(data, "alignment_debug", prior_map)
```

#### D. `cfg_args`

텍스트 파일이므로 문자열 치환:
```python
text = path.read_text()
for old, new in dir_map.items():
    text = text.replace(old, new)
path.write_text(text)
```

#### E. CSV 리포트

```python
import csv
# experiment_name 칼럼의 값을 full_map으로 치환
```

#### F. Prior manifest

```python
# tags 배열 내 old 태그 → new 태그
# extras 내 old 이름 → new 이름
```

### 3-4. `replace_path_segments()` 헬퍼

경로 문자열에서 `old_dir_name`을 `new_dir_name`으로 치환하되, 경로 구분자(`/`) 경계에서만 매칭:

```python
def replace_path_segments(path_str: str, mapping: dict[str, str]) -> str:
    for old, new in mapping.items():
        path_str = path_str.replace(f"/{old}/", f"/{new}/")
        if path_str.endswith(f"/{old}"):
            path_str = path_str[:-len(old)] + new
    return path_str
```

---

## 4. 구현할 스크립트

### `scripts/update_internal_refs.py`

```
용도: outputs/gaussian_direct/ 내부 파일의 OLD 이름 참조를 일괄 업데이트
입력: rename_to_date_format.py의 매핑 함수 (import)
플래그: --dry-run (기본) / --execute
처리 순서:
  1. dir_map, full_map, prior_map 생성
  2. experiments/ 순회 → backend_run.json, evaluation.json, prior_specs.json 업데이트
  3. backend_runs/ 순회 → cfg_args 업데이트
  4. reports/ 순회 → CSV 업데이트
  5. prior_library/ → manifest 업데이트
출력: 변경 파일 수 및 변경 내역 출력
```

---

## 5. 실행 순서

```bash
# Step 1: 내부 참조 dry-run
uv run python scripts/update_internal_refs.py

# Step 2: 내부 참조 실행
uv run python scripts/update_internal_refs.py --execute

# Step 3: 디렉토리 리네이밍 실행
uv run python scripts/rename_to_date_format.py --execute

# Step 4: 검증
# - 샘플 backend_run.json의 experiment_name, model_path 확인
# - 샘플 CSV의 experiment_name 칼럼 확인
# - 테스트 실행: uv run pytest tests/
```

---

## 6. 수정하지 않는 것

| 항목 | 이유 |
|------|------|
| `legacy_bugged_*` 내부 파일 | 사용자 결정: 레거시는 그대로 유지 |
| `source_path` (데이터셋 경로) | 데이터셋 위치는 리네이밍 대상 아님 |
| PLY 파일명 | `result_ply_naming.py`의 라벨 기반이라 디렉토리 이름과 무관 |
| `docs/experiments/` 보고서 | 기존 보고서는 히스토리 기록이므로 수정 불필요 |
| `configs/experiments/*.yaml` | 별도 계획에서 처리 (config 리네이밍) |
