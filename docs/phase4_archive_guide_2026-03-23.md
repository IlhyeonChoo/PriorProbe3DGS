# Phase 4: 실험 데이터 아카이브 및 작업 디렉토리 정리 가이드

Date: 2026-03-23

---

## 목적

Phase 1-3 실험이 완료되었다. 실험 산출물(331+ GB)을 HDD/SSD로 백업하고, 작업 디렉토리에는 소스 코드와 경량 문서만 남겨 다음 실험을 준비한다.

이 문서는 **Phase 1-3 산출물만** 아카이브/정리 대상으로 다룬다. 2026-03-23에 생성한 **Phase 5 surface RGB 준비 자산은 제외**하며, 로컬 작업 디렉토리에 그대로 남겨둔다.

---

## 현재 상태

### 작업 디렉토리 용량

| 경로 | 크기 | 내용 |
|------|-----:|------|
| `outputs/gaussian_direct/backend_runs/` | 331 GB | 65개 top-level run 디렉토리 (Phase 1-3 본 실험 62개 + 1000-iter/inspection 3개) |
| `outputs/gaussian_direct/experiments/` | 46 MB | evaluation.json, backend_run.json |
| `outputs/gaussian_direct/prior_library/` | 246 MB | Phase 1-3 prior + Phase 5 surface prior가 혼재. Surface prior는 이번 정리 대상에서 제외 |
| `outputs/gaussian_direct/reports/` | 892 KB | CSV 요약, 진단 PNG |
| `outputs/gaussian_direct/legacy_prefixed/` | 5.3 GB | 이전 prefix 포함 실험 |
| `outputs/gaussian_direct/legacy_misc/` | 6.2 MB | 이전 기타 |
| `outputs/gaussian_direct/prior_training/` | 79 MB | 현재는 Phase 5 same-scene surface prior 학습 결과만 존재. 이번 정리 대상에서 제외 |
| `configs/` | 3 MB | 실험 YAML + 데이터셋 YAML. Phase 5 surface dataset config 1개 포함 |
| `src/priorprobe/` | 752 KB | 소스 코드 |
| `scripts/` | 872 KB | 실험/리포트 스크립트 |
| `tests/` | 436 KB | 단위 테스트 |
| `docs/experiment_plans/ + docs/experiment_results/ + docs/notes/` | 240 KB | 실험 계획서 + 결과 보고서 + 운영 노트 |

### 저장소 현황

| 저장소 | 마운트 | 용량 | 사용 | 여유 | 용도 |
|--------|--------|-----:|-----:|-----:|------|
| Home NVMe | `/home/ilhyeonchu/` | 1.8 TB | 798 GB | 942 GB | 작업 디렉토리 |
| HDD | `/mnt/hddg1` | 15 TB | 193 GB | 14.8 TB | 전체 백업 대상 |
| SSD | `/mnt/3dgs-ssd` | 1.8 TB | 59 GB | 1.7 TB | 경량 인덱스 백업 |

### 기존 외부 저장소 구조

```
/mnt/hddg1/
└── 3dgs-data/
    └── priorprobe3dgs/          # 학습 데이터셋 (Replica, ShapeSplat)
        ├── replica_dataset/
        ├── shapesplat_extract/
        └── shapesplat_hf/

/mnt/3dgs-ssd/
└── 3dgs-stage/
    └── priorprobe3dgs/          # COLMAP 처리된 학습 데이터
        ├── replica_colmap/
        ├── replica_colmap_multi_roomwide_v2_*/
        └── ...
```

### 이번 정리에서 제외할 Phase 5 자산

아래 항목은 **보존 대상**이다. 이 문서의 복사/삭제 명령에서 제외한다.

- `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_v2_384_surface_rgb/`
- `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_object_surface_exact_rgb/`
- `configs/datasets/replica_multi_roomwide_v2_384_surface_rgb_shared.yaml`
- `outputs/gaussian_direct/prior_training/replica_surface_exact_trained_7000/`
- `outputs/gaussian_direct/prior_library/replica_target_surface_exact_trained_clip/`
- `outputs/gaussian_direct/prior_library/replica_target_surface_exact_trained_clip_manifest.json`
- `outputs/gaussian_direct/prior_library/replica_target_surface_exact_trained_clip_inventory.json`
- `outputs/gaussian_direct/prior_library/replica_target_surface_exact_trained_clip.yaml`
- `docs/notes/03-23_phase5_surface_prep_2026.md`

아래는 **임시 Phase 5 검증 산출물**이므로 정리 대상이다.

- `outputs/tmp_phase5_*`
- `outputs/gaussian_direct/reports/tmp_room0_surface_*.png`

---

## Git 주의사항

`backend_runs/`에 **362개 git-tracked 파일**이 존재한다. `.gitignore`에 `/outputs/**/backend_runs/` 규칙이 있지만, 이 파일들은 규칙 추가 전에 커밋되어 여전히 tracking 중이다.

**git-tracked 파일 내역:**

| 파일 유형 | 수량 | 크기 | 처리 |
|----------|-----:|-----:|------|
| `aligned_prior_*.ply` | 96 | 455 MB | `git rm --cached` 필수 |
| inspection PNG | 13 | ~20 MB | `git rm --cached` 필수 |
| `viewer.html` | 13 | ~5 MB | `git rm --cached` 필수 |
| `cfg_args` | 34 | ~100 KB | 선택 (경량, 삭제해도 무방) |
| `cameras.json` | 34 | ~수 MB | 선택 |
| `results.json`, `per_view.json`, `exposure.json` | 102 | ~수 MB | 선택 |
| `metadata.json` (prior init) | 28 | ~100 KB | 선택 |

**삭제 전 반드시 `git rm --cached`로 tracking을 해제하고, HDD 백업이 완료된 후에만 물리적 삭제를 진행한다.**

## Runbook Variables

- `DATA_STAGE_ROOT=/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs`
- `ARCHIVE_ROOT=/mnt/hddg1/priorprobe3dgs-archive`
- `SSD_INDEX_ROOT=${DATA_STAGE_ROOT}/gaussian_direct_index`

---

## Step 1: HDD 아카이브 디렉토리 생성

`3dgs-data/`는 학습 데이터셋이므로 아카이브와 분리한다. 최상위에 별도 아카이브 디렉토리를 생성한다.

```bash
ARCHIVE_ROOT=/mnt/hddg1/priorprobe3dgs-archive
ARCHIVE_PHASE_ROOT="${ARCHIVE_ROOT}/gaussian-direct/phase1-3_2026-03"

mkdir -p "${ARCHIVE_PHASE_ROOT}"/{training_runs/{era0_legacy,era1_upper_bound,era2_protection,era3_roomwide_v1,era4_roomwide_v2,era5_interference,era6_phase3,smoke_tests},evaluations,prior_library,reports,legacy_prefixed,legacy_misc,configs_snapshot/{experiments,datasets},docs_snapshot/{experiment_plans,experiment_results,notes}}
```

### 디렉토리 구조

```
/mnt/hddg1/priorprobe3dgs-archive/
├── README.md                             # 아카이브 매니페스트
│
└── gaussian-direct/                      # 브랜치별 네임스페이스
    └── phase1-3_2026-03/                 # Phase + 날짜 기반 버전
        │
        ├── training_runs/                # backend_runs 전체 (331 GB)
        │   ├── era0_legacy/              # 초기 oracle/baseline (~470 MB)
        │   ├── era1_upper_bound/         # upper bound + retrieval (~41 GB)
        │   ├── era2_protection/          # Phase 1 protection sweep (~22 GB)
        │   ├── era3_roomwide_v1/         # roomwide v1 viewcount (~100 GB)
        │   ├── era4_roomwide_v2/         # roomwide v2 viewcount (~85 GB)
        │   ├── era5_interference/        # 간섭 진단 + 조합 (~74 GB)
        │   ├── era6_phase3/              # Phase 3 lr/protection (~13 GB)
        │   └── smoke_tests/              # 1000-iter smoke (~1.5 GB)
        │
        ├── evaluations/                  # experiments/ 전체 (46 MB)
        ├── prior_library/                # PLY + manifest (128 MB)
        ├── reports/                      # CSV 요약 (892 KB)
        ├── legacy_prefixed/              # 이전 prefix 포함 실험 (5.3 GB)
        ├── legacy_misc/                  # 이전 기타 (6.2 MB)
        ├── configs_snapshot/             # 실험 시점 config 동결
        │   ├── experiments/              # 81 YAML
        │   └── datasets/                 # 14 YAML
        │
        └── docs_snapshot/                # 실험 시점 문서 동결 (Phase 5 준비 문서 제외)
            ├── experiment_plans/         # 실험 계획서
            ├── experiment_results/       # 실험 결과 보고서
            └── notes/                    # prep/bug/inventory 메모
```

> `prior_training/`는 현재 Phase 5 surface prior만 담고 있으므로 이 문서의 아카이브 대상에서 제외한다.

### Era 분류표

각 era는 연구 진행 단계를 반영한다. `backend_runs/` 내 디렉토리를 아래 분류에 따라 해당 era 디렉토리로 복사한다.

#### Era 0: Pre-branch Legacy (~470 MB, 17 runs)

초기 oracle/baseline 실험. 브랜치 설정 전 수행.

```
oracle_prior_vanilla_3dgs
oracle_prior_vanilla_3dgs_clip
oracle_prior_vanilla_3dgs_multi_clip
oracle_prior_vanilla_3dgs_multi_clip_15000
oracle_prior_vanilla_3dgs_multi_clip_alignfix_v1_15000
oracle_prior_vanilla_3dgs_multi_clip_alignfix_v2_15000
oracle_prior_vanilla_3dgs_multi_clip_geom
oracle_prior_vanilla_3dgs_multi_clip_geom_15000
oracle_prior_vanilla_3dgs_multi_clip_geom_filtered
oracle_prior_vanilla_3dgs_multi_clip_geom_weighted
oracle_prior_vanilla_3dgs_multi_mean_rgb
oracle_prior_vanilla_3dgs_multi_mean_rgb_15000
oracle_prior_vanilla_3dgs_multi_mean_rgb_alignfix_v1_15000
oracle_prior_vanilla_3dgs_multi_mean_rgb_alignfix_v2_15000
baseline_from_scratch_vanilla_3dgs
baseline_from_scratch_vanilla_3dgs_multi
baseline_from_scratch_vanilla_3dgs_multi_15000
```

#### Era 1: Upper Bound + Retrieval (~41 GB, 9 runs)

Oracle exact prior upper bound 및 retrieval 방식 비교.

```
same_scene_exact_tiny_room_0
merge_tiny_room_0
replace_tiny_room_0
same_scene_exact_clip_15000
existing_clip_only_15000
merged_clip_retrieval_15000
merged_oracle_select_clip_15000
same_scene_exact_clip_diverse_384_15000
baseline_from_scratch_vanilla_3dgs_multi_diverse_384_15000
```

#### Era 2: Phase 1 Protection Sweep (~22 GB, 3 runs)

Weak/freeze protection 정책 비교 (diverse 384 view).

```
same_scene_exact_clip_diverse_384_weak_15000
same_scene_exact_clip_diverse_384_freeze_15000
same_scene_exact_clip_weak_15000
```

#### Era 3: Roomwide v1 View Count Sweep (~100 GB, 9 runs)

Roomwide v1 데이터셋 기반 96/192/384 view 비교.

```
baseline_from_scratch_vanilla_3dgs_multi_roomwide_96_15000
baseline_from_scratch_vanilla_3dgs_multi_roomwide_192_15000
baseline_from_scratch_vanilla_3dgs_multi_roomwide_384_15000
same_scene_exact_clip_roomwide_96_15000
same_scene_exact_clip_roomwide_96_weak_15000
same_scene_exact_clip_roomwide_192_15000
same_scene_exact_clip_roomwide_192_weak_15000
same_scene_exact_clip_roomwide_384_15000
same_scene_exact_clip_roomwide_384_weak_15000
```

#### Era 4: Roomwide v2 View Count Sweep (~85 GB, 9 runs)

Roomwide v2 데이터셋으로 전환 후 동일 sweep 반복.

```
baseline_from_scratch_vanilla_3dgs_multi_roomwide_v2_96_15000
baseline_from_scratch_vanilla_3dgs_multi_roomwide_v2_192_15000
baseline_from_scratch_vanilla_3dgs_multi_roomwide_v2_384_15000
same_scene_exact_clip_roomwide_v2_96_15000
same_scene_exact_clip_roomwide_v2_96_weak_15000
same_scene_exact_clip_roomwide_v2_192_15000
same_scene_exact_clip_roomwide_v2_192_weak_15000
same_scene_exact_clip_roomwide_v2_384_15000
same_scene_exact_clip_roomwide_v2_384_weak_15000
```

#### Era 5: 간섭 진단 + 조합 (~74 GB, 12 runs)

A(서브샘플링)/B(SfM 제거)/C(SH 리셋) 단독 및 조합 실험.

```
same_scene_exact_clip_roomwide_v2_384_sh_zero_15000
same_scene_exact_clip_roomwide_v2_384_sh_zero_weak_15000
same_scene_exact_clip_roomwide_v2_384_replace_region_15000
same_scene_exact_clip_roomwide_v2_384_replace_region_weak_15000
same_scene_exact_clip_roomwide_v2_384_prior_50k_15000
same_scene_exact_clip_roomwide_v2_384_prior_50k_weak_15000
same_scene_exact_clip_roomwide_v2_384_prior_25k_15000
same_scene_exact_clip_roomwide_v2_384_prior_25k_weak_15000
same_scene_exact_clip_roomwide_v2_384_prior_25k_sh_zero_15000
same_scene_exact_clip_roomwide_v2_384_prior_25k_sh_zero_weak_15000
same_scene_exact_clip_roomwide_v2_384_prior_25k_replace_region_15000
same_scene_exact_clip_roomwide_v2_384_prior_25k_replace_region_sh_zero_15000
```

#### Era 6: Phase 3 lr/Protection Sweep (~13 GB, 3 runs)

lr_scale 및 prune/densify 보호 완전 해제 실험.

```
same_scene_exact_clip_roomwide_v2_384_prior_25k_lr01_15000
same_scene_exact_clip_roomwide_v2_384_prior_25k_lr10_15000
same_scene_exact_clip_roomwide_v2_384_prior_25k_full_none_15000
```

#### Smoke Tests (~1.5 GB)

1000-iter 빠른 검증용 실험. `backend_runs/` 내 `*_1000` 또는 `*_smoke_*` suffix 디렉토리.

---

## Step 2: HDD로 데이터 복사

모든 복사에 `rsync -av --progress` 사용. 중단 시 동일 명령으로 재개 가능.

### 2-1: Training runs (era별)

예시 (era0):

```bash
cd "$(git rev-parse --show-toplevel)"
ARCHIVE_ROOT=/mnt/hddg1/priorprobe3dgs-archive
ARCHIVE_PHASE_ROOT="${ARCHIVE_ROOT}/gaussian-direct/phase1-3_2026-03"

for dir in oracle_prior_vanilla_3dgs oracle_prior_vanilla_3dgs_clip \
  oracle_prior_vanilla_3dgs_multi_clip oracle_prior_vanilla_3dgs_multi_clip_15000 \
  oracle_prior_vanilla_3dgs_multi_clip_alignfix_v1_15000 \
  oracle_prior_vanilla_3dgs_multi_clip_alignfix_v2_15000 \
  oracle_prior_vanilla_3dgs_multi_clip_geom \
  oracle_prior_vanilla_3dgs_multi_clip_geom_15000 \
  oracle_prior_vanilla_3dgs_multi_clip_geom_filtered \
  oracle_prior_vanilla_3dgs_multi_clip_geom_weighted \
  oracle_prior_vanilla_3dgs_multi_mean_rgb \
  oracle_prior_vanilla_3dgs_multi_mean_rgb_15000 \
  oracle_prior_vanilla_3dgs_multi_mean_rgb_alignfix_v1_15000 \
  oracle_prior_vanilla_3dgs_multi_mean_rgb_alignfix_v2_15000 \
  baseline_from_scratch_vanilla_3dgs \
  baseline_from_scratch_vanilla_3dgs_multi \
  baseline_from_scratch_vanilla_3dgs_multi_15000; do
  rsync -av --progress "outputs/gaussian_direct/backend_runs/$dir/" \
    "${ARCHIVE_PHASE_ROOT}/training_runs/era0_legacy/$dir/"
done
```

나머지 era도 동일 패턴으로 해당 디렉토리 목록과 era 경로를 변경하여 실행한다.

### 2-2: 나머지 데이터

```bash
ARCHIVE_ROOT=/mnt/hddg1/priorprobe3dgs-archive
ARCHIVE_PHASE_ROOT="${ARCHIVE_ROOT}/gaussian-direct/phase1-3_2026-03"
ARCHIVE="$ARCHIVE_PHASE_ROOT"
SRC=outputs/gaussian_direct

# Evaluations (46 MB)
rsync -av --progress "$SRC/experiments/" "$ARCHIVE/evaluations/"

# Prior library (Phase 1-3만, Phase 5 surface prior 제외)
for item in \
  replica_target_exact_clip \
  replica_target_exact_clip_inventory.json \
  replica_target_exact_clip_manifest.json \
  replica_target_exact_clip.yaml \
  replica_target_exact_plus_shapesplat_clip_manifest.json \
  replica_target_exact_plus_shapesplat_clip.yaml \
  shapesplat_manifest.json \
  shapesplat_modelnet_bundle_clip_geom_manifest.json \
  shapesplat_modelnet_bundle_clip_manifest.json \
  shapesplat_modelnet_bundle_mean_rgb_manifest.json \
  shapesplat_modelnet_chair_clip_manifest.json \
  shapesplat_modelnet_chair_manifest.json; do
  rsync -av --progress "$SRC/prior_library/$item" "$ARCHIVE/prior_library/"
done

# Reports (892 KB)
rsync -av --progress "$SRC/reports/" "$ARCHIVE/reports/"

# Legacy prefixed (5.3 GB)
rsync -av --progress "$SRC/legacy_prefixed/" "$ARCHIVE/legacy_prefixed/"

# Legacy misc (6.2 MB)
rsync -av --progress "$SRC/legacy_misc/" "$ARCHIVE/legacy_misc/"

# Configs snapshot (3 MB)
rsync -av --progress configs/experiments/ "$ARCHIVE/configs_snapshot/experiments/"
rsync -av --progress --exclude 'replica_multi_roomwide_v2_384_surface_rgb_shared.yaml' \
  configs/datasets/ "$ARCHIVE/configs_snapshot/datasets/"

# Docs snapshot (Phase 5 준비 문서 제외)
rsync -av --progress docs/experiment_plans/ "$ARCHIVE/docs_snapshot/experiment_plans/"
rsync -av --progress docs/experiment_results/ "$ARCHIVE/docs_snapshot/experiment_results/"
rsync -av --progress --exclude '03-23_phase5_surface_prep*.md' \
  docs/notes/ "$ARCHIVE/docs_snapshot/notes/"
```

### 예상 소요 시간

HDD 쓰기 속도 ~150 MB/s 기준, training_runs 331 GB → 약 37분. 전체 약 40분.

---

## Step 3: 복사 검증

**반드시 검증 후에만 Step 5(삭제)로 진행한다.**

```bash
ARCHIVE_ROOT=/mnt/hddg1/priorprobe3dgs-archive
ARCHIVE_PHASE_ROOT="${ARCHIVE_ROOT}/gaussian-direct/phase1-3_2026-03"
ARCHIVE="$ARCHIVE_PHASE_ROOT"

# 거친 파일 수/용량 비교
find outputs/gaussian_direct/backend_runs/ -type f | wc -l
find "$ARCHIVE/training_runs/" -type f | wc -l
du -sh outputs/gaussian_direct/backend_runs/
du -sh "$ARCHIVE/training_runs/"

# 대표 run 1개를 checksum dry-run으로 검증
rsync -avnc --delete \
  outputs/gaussian_direct/backend_runs/same_scene_exact_clip_roomwide_v2_384_prior_25k_15000/ \
  "$ARCHIVE/training_runs/era5_interference/same_scene_exact_clip_roomwide_v2_384_prior_25k_15000/"

# 직접 복사한 평가/리포트도 dry-run으로 검증
rsync -avnc --delete outputs/gaussian_direct/experiments/ "$ARCHIVE/evaluations/"
rsync -avnc --delete outputs/gaussian_direct/reports/ "$ARCHIVE/reports/"
```

`rsync -avnc --delete` 결과가 비어 있으면 통과로 본다.

---

## Step 4: SSD 인덱스 생성

경량 데이터만 SSD에 복사. 빠른 조회용.

### 4-1: 디렉토리 생성

```bash
DATA_STAGE_ROOT=/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs
SSD_INDEX_ROOT="${DATA_STAGE_ROOT}/gaussian_direct_index"

mkdir -p "${SSD_INDEX_ROOT}"/{evaluations,reports,prior_manifests,configs/{experiments,datasets}}
```

### 4-2: 구조

```
/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/gaussian_direct_index/
├── README.md                        # 인덱스 설명 + HDD 참조
├── evaluations/                     # evaluation.json + backend_run.json만 (~30 MB)
├── reports/                         # CSV 요약 (~200 KB)
├── prior_manifests/                 # manifest JSON만, PLY 없음 (~9 MB)
└── configs/                         # YAML 스냅샷 (~3 MB)
    ├── experiments/
    └── datasets/
```

### 4-3: 데이터 복사

```bash
DATA_STAGE_ROOT=/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs
SSD_INDEX_ROOT="${DATA_STAGE_ROOT}/gaussian_direct_index"
SSD_INDEX="$SSD_INDEX_ROOT"
SRC=outputs/gaussian_direct

# evaluation.json + backend_run.json만 선별 복사
cd "$SRC/experiments"
find . -name "evaluation.json" -o -name "backend_run.json" | while read f; do
  target_dir="$SSD_INDEX/evaluations/$(dirname "$f")"
  mkdir -p "$target_dir"
  cp "$f" "$target_dir/"
done
cd -

# Reports (CSV만)
cp "$SRC"/reports/*.csv "$SSD_INDEX/reports/"
cp "$SRC"/reports/*.json "$SSD_INDEX/reports/" 2>/dev/null

# Prior manifests (Phase 1-3만, Phase 5 surface prior 제외)
cp "$SRC"/prior_library/replica_target_exact_clip_inventory.json "$SSD_INDEX/prior_manifests/"
cp "$SRC"/prior_library/replica_target_exact_clip_manifest.json "$SSD_INDEX/prior_manifests/"
cp "$SRC"/prior_library/replica_target_exact_clip.yaml "$SSD_INDEX/prior_manifests/"
cp "$SRC"/prior_library/replica_target_exact_plus_shapesplat_clip_manifest.json "$SSD_INDEX/prior_manifests/"
cp "$SRC"/prior_library/replica_target_exact_plus_shapesplat_clip.yaml "$SSD_INDEX/prior_manifests/"
cp "$SRC"/prior_library/shapesplat*.json "$SSD_INDEX/prior_manifests/"

# Configs
cp configs/experiments/*.yaml "$SSD_INDEX/configs/experiments/"
find configs/datasets -maxdepth 1 -name '*.yaml' ! -name 'replica_multi_roomwide_v2_384_surface_rgb_shared.yaml' -exec cp {} "$SSD_INDEX/configs/datasets/" \;
```

---

## Step 5: README.md 작성

### HDD README.md

`/mnt/hddg1/priorprobe3dgs-archive/README.md`에 다음 내용 포함:

- 아카이브 날짜: 2026-03-23
- Git branch: `exp/gaussian-direct`
- Git commit hash: (작성 시점의 HEAD)
- 제외 범위: Phase 5 surface RGB dataset / surface-trained prior는 이번 아카이브에 포함하지 않음
- Phase 1-3 핵심 결론:
  - A 25K(none)이 최선의 삽입 정책
  - Protection 설정은 final PSNR에 무관
  - 간섭 완화 조합은 가산적이지 않음
  - Multi-object metadata indexing 버그 발견 및 수정 (재실행 필요)
- Era별 인덱스 (이름, 날짜, run 수, 크기, 핵심 발견)
- 복원 방법: 특정 era를 `outputs/gaussian_direct/backend_runs/`로 rsync

### SSD README.md

`/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/gaussian_direct_index/README.md`에 다음 내용 포함:

- 이 디렉토리는 조회용 경량 인덱스임
- 전체 아카이브 위치: `/mnt/hddg1/priorprobe3dgs-archive/gaussian-direct/phase1-3_2026-03/`
- 포함 데이터: evaluation.json, CSV reports, manifest JSON, config YAML

---

## Step 6: Git-tracked 파일 정리

HDD 백업 완료 후 실행.

```bash
cd "$(git rev-parse --show-toplevel)"

# 바이너리 파일 git tracking 해제 (물리 파일은 유지)
git ls-files -z outputs/gaussian_direct/backend_runs | \
  grep -zE '\.(ply|png|html)$' | \
  xargs -0 -r git rm --cached --

# 경량 메타데이터도 untrack할 경우 (선택)
git ls-files -z outputs/gaussian_direct/backend_runs | \
  grep -zE '(^|/)(cfg_args|[^/]+\.json)$' | \
  xargs -0 -r git rm --cached --
```

> **주의:** `git rm --cached`는 git에서 tracking만 해제하고 파일 자체는 삭제하지 않는다. 물리적 삭제는 Step 7에서 별도로 수행한다.

---

## Step 7: 작업 디렉토리 물리적 삭제

**Step 3(검증) 완료 후에만 실행한다.**

```bash
cd "$(git rev-parse --show-toplevel)"

# backend_runs 전체 삭제 (331 GB 회수)
rm -rf outputs/gaussian_direct/backend_runs/*/

# legacy 디렉토리 삭제 (5.4 GB 회수)
rm -rf outputs/gaussian_direct/legacy_prefixed/
rm -rf outputs/gaussian_direct/legacy_misc/

# prior_library에서 Phase 1-3 자산만 삭제, Phase 5 surface prior는 유지
rm -rf outputs/gaussian_direct/prior_library/replica_target_exact_clip/
rm -f outputs/gaussian_direct/prior_library/replica_target_exact_clip_inventory.json
rm -f outputs/gaussian_direct/prior_library/replica_target_exact_clip_manifest.json
rm -f outputs/gaussian_direct/prior_library/replica_target_exact_clip.yaml
rm -f outputs/gaussian_direct/prior_library/replica_target_exact_plus_shapesplat_clip_manifest.json
rm -f outputs/gaussian_direct/prior_library/replica_target_exact_plus_shapesplat_clip.yaml
rm -f outputs/gaussian_direct/prior_library/shapesplat*.json

# reports에서 임시 진단 PNG 삭제
rm -f outputs/gaussian_direct/reports/tmp_*.png

# Phase 5 임시 검증 산출물만 삭제
rm -rf outputs/tmp_phase5_*

# conversation 로그 삭제
rm -f conversation-*.txt
```

---

## Step 8: 정리 확인

```bash
# 작업 디렉토리 용량 확인 (Phase 5 보존 자산 포함 시 ~250 MB 수준 기대)
du -sh outputs/gaussian_direct/

# git status 확인 (tracked 파일 삭제 여부)
git status

# 소스 코드 정상 여부
uv run python -c "import priorprobe; print('OK')"
```

---

## 정리 후 작업 디렉토리 최종 상태

```
PriorProbe3DGS-gaussian/              (정리 후 outputs 기준 ~250 MB 수준, .venv 제외)
├── src/priorprobe/                    # 소스 코드
├── scripts/                           # 실험/리포트 스크립트
├── tests/                             # 단위 테스트
├── configs/
│   ├── experiments/                   # 81 실험 YAML
│   └── datasets/                      # 데이터셋 YAML (Phase 5 surface config 포함)
├── docs/
│   ├── experiment_plans/              # 실험 계획서
│   ├── experiment_results/            # 실험 결과 보고서
│   ├── notes/                         # prep/bug/inventory 메모
│   └── phase4_archive_guide_2026-03-23.md  # 이 문서
├── outputs/gaussian_direct/
│   ├── backend_runs/                  # 비어있음 (새 실험용)
│   ├── experiments/                   # evaluation.json + backend_run.json만
│   ├── reports/                       # CSV 요약만
│   ├── prior_library/                 # Phase 5 surface prior library만 유지
│   └── prior_training/                # Phase 5 surface object prior 학습 결과 유지
├── CLAUDE.md, research_plan.md, README.md
└── .venv/
```

---

## 복원 방법

특정 실험의 training run이 필요할 때:

```bash
# 예: era5의 prior_25k 실험 복원
ARCHIVE_ROOT=/mnt/hddg1/priorprobe3dgs-archive
ARCHIVE_PHASE_ROOT="${ARCHIVE_ROOT}/gaussian-direct/phase1-3_2026-03"

rsync -av --progress \
  "${ARCHIVE_PHASE_ROOT}/training_runs/era5_interference/same_scene_exact_clip_roomwide_v2_384_prior_25k_15000/" \
  outputs/gaussian_direct/backend_runs/same_scene_exact_clip_roomwide_v2_384_prior_25k_15000/
```

---

## 체크리스트

```
[ ] Step 1: HDD 디렉토리 구조 생성 (mkdir)
[ ] Step 2: HDD로 rsync (era별 순차)
[ ] Step 3: 복사 검증 (파일 수 + 용량 일치 확인)
[ ] Step 4: SSD 인덱스 생성 + 경량 데이터 복사
[ ] Step 5: README.md 작성 (HDD + SSD)
[ ] Step 6: git rm --cached (바이너리 untrack)
[ ] Step 7: 물리적 삭제 (rm -rf)
[ ] Step 8: 정리 확인 (du, git status, import 테스트)
```
