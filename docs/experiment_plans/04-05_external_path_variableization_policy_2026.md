# External Path Variableization Policy

Date: 2026-04-05

## 목적

문서에 남아 있는 외부 절대 경로를 일괄 치환하지 않고, 어떤 경로를 변수화하고 어떤 경로를 그대로 유지할지 기준을 고정한다.

이 계획은 즉시 치환을 수행하기 위한 실행 문서가 아니다.

- 이번 단계에서는 문서 수정 범위와 변수 이름만 확정한다.
- 실제 치환은 별도 승인 후 진행한다.
- 외부 경로의 운영 의미를 흐리거나, runbook 재현성을 떨어뜨리는 치환은 하지 않는다.

## 배경

현재 repo 내부 경로는 문서 위치 기준 상대 경로로 정리했다. 남아 있는 절대 경로는 주로 아래 세 범주다.

- `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/...` 아래의 staged dataset / scene metadata / object dataset
- `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS/...` 아래의 legacy dataset root
- `/mnt/hddg1`, `/mnt/3dgs-ssd`, `/home/ilhyeonchu/` 같은 storage mount / archive root

핵심 차이는 다음과 같다.

- dataset/staging root는 여러 문서에서 반복되므로 변수화 가치가 높다.
- legacy repo root도 외부 의존성이라는 점에서 변수화 가치가 있다.
- storage mount와 archive runbook은 실제 운영 경로 자체가 문서의 의미이므로, 전부 변수화하면 즉시성이 떨어질 수 있다.

## 결정 원칙

### 1. 변수화 대상

다음 조건을 만족하면 변수화한다.

- 현재 repo 외부 경로다.
- 동일 루트가 여러 문서에서 반복된다.
- 경로의 핵심 의미가 "반복되는 root 아래의 특정 dataset family"다.
- 변수 이름이 경로의 의미를 더 명확하게 만든다.

대표 예시:

- `DATA_STAGE_ROOT=/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs`
- `LEGACY_REPO_ROOT=/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS`
- `LEGACY_DATASET_ROOT=${LEGACY_REPO_ROOT}/data/public_datasets`

### 2. 그대로 유지할 대상

다음 조건을 만족하면 literal 절대 경로를 유지한다.

- 문서의 목적이 실제 mount point, backup root, archive topology를 설명하는 것이다.
- 경로 자체가 당시 운영 환경의 사실 기록이다.
- 경로를 변수로 바꾸면 사람이 문서를 읽을 때 실제 저장 위치를 즉시 파악하기 어려워진다.

대표 예시:

- storage status table의 `/home/ilhyeonchu/`, `/mnt/hddg1`, `/mnt/3dgs-ssd`
- archive directory tree에 나타나는 실제 HDD/SSD 경로

### 3. 혼합 방식 대상

다음 조건을 만족하면 section 내부에서 literal과 변수를 함께 쓴다.

- 문서 상단이나 표에서는 실제 경로를 유지하는 편이 낫다.
- 하지만 command block이나 반복되는 명령 prefix는 변수화하는 편이 읽기 쉽다.
- Markdown 외부 링크는 변수 치환을 지원하지 않아서 literal link를 유지해야 한다.

대표 예시:

- runbook의 shell command
- 외부 `scene_meta.json` 클릭 링크

## 제안 변수 집합

아래 변수는 현재 문서군에서 반복되는 외부 경로를 설명하기에 충분하다.

| Variable | Proposed Value | Intended Use |
| --- | --- | --- |
| `DATA_STAGE_ROOT` | `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs` | processed Replica staging, roomwide datasets, surface RGB datasets, SSD-side lightweight index |
| `LEGACY_REPO_ROOT` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS` | old non-gaussian worktree that still contains legacy datasets |
| `LEGACY_DATASET_ROOT` | `${LEGACY_REPO_ROOT}/data/public_datasets` | legacy dataset subtree used in early smoke runs |
| `ARCHIVE_ROOT` | `/mnt/hddg1/priorprobe3dgs-archive` | top-level HDD archive root for archived experiment outputs |
| `SSD_INDEX_ROOT` | `${DATA_STAGE_ROOT}/gaussian_direct_index` | SSD-side lightweight index for reports/manifests/config snapshots |
| `SURFACE_SCENE_DATASET_ROOT` | `${DATA_STAGE_ROOT}/replica_colmap_multi_roomwide_v2_384_surface_rgb` | Phase 5 surface scene dataset family |
| `SURFACE_OBJECT_DATASET_ROOT` | `${DATA_STAGE_ROOT}/replica_object_surface_exact_rgb` | Phase 5 surface object dataset family |
| `REPLICA_MULTI_ROOT` | `${DATA_STAGE_ROOT}/replica_colmap_multi` | 96-view multi-object staged dataset |
| `REPLICA_COLMAP_STAGE_ROOT` | `${DATA_STAGE_ROOT}/replica_colmap` | staged 97-image Replica COLMAP dataset |
| `REPLICA_MULTI_DIVERSE_384_ROOT` | `${DATA_STAGE_ROOT}/replica_colmap_multi_diverse_384` | dense diverse-azimuth 384-view dataset |

## Markdown 제한

실제 치환 시 다음 제한을 반드시 지켜야 한다.

- 일반 Markdown은 변수 interpolation을 지원하지 않는다.
- code block과 inline code에서는 `${VAR}` 표기가 자연스럽다.
- Markdown link target에서는 `${VAR}`가 클릭 가능한 실제 파일 경로로 해석되지 않는다.
- 따라서 외부 파일을 직접 여는 링크는 literal absolute link를 유지하거나, 링크를 제거하고 코드 문자열로 바꾸는 선택이 필요하다.

이 제한 때문에 "변수화"는 모든 외부 경로를 같은 방식으로 치환하는 작업이 아니다.

## 문서별 분류 계획

| Document | Current External Path Meaning | Recommended Action | Notes |
| --- | --- | --- | --- |
| `docs/experiment_results/03-20_dense_view_probe_2026.md` | staged multi-object dataset root | 변수화 | `REPLICA_MULTI_ROOT` 사용 |
| `docs/experiment_results/03-20_prior_protection_room_0_2026.md` | dense 384-view staged dataset root | 변수화 | `REPLICA_MULTI_DIVERSE_384_ROOT` 사용 |
| `docs/experiment_results/03-20_upper_bound_dense_diverse_384_2026.md` | dense 384-view staged dataset root | 변수화 | `REPLICA_MULTI_DIVERSE_384_ROOT` 사용 |
| `docs/experiment_results/03-27_baseline_surface_rgb_variance10_2026.md` | scene-level surface RGB source paths | 변수화 | `SURFACE_SCENE_DATASET_ROOT` 기준으로 scene suffix를 붙인다 |
| `docs/experiment_results/03-27_baseline_surface_rgb_variance_2026.md` | scene-level surface RGB source paths | 변수화 | `SURFACE_SCENE_DATASET_ROOT` 기준으로 scene suffix를 붙인다 |
| `docs/notes/03-20_image_count_inventory_2026.md` | staged dataset roots + legacy repo dataset root | 변수화 | `REPLICA_MULTI_ROOT`, `REPLICA_COLMAP_STAGE_ROOT`, `LEGACY_DATASET_ROOT` 사용 |
| `docs/notes/03-21_roomwide_camera_distribution_check_2026.md` | external `scene_meta.json` files opened via Markdown link | 혼합 | 설명 텍스트는 변수화 가능. 링크 target은 literal 유지 권장 |
| `docs/notes/03-23_phase5_surface_prep_2026.md` | surface scene/object dataset roots | 변수화 | `SURFACE_SCENE_DATASET_ROOT`, `SURFACE_OBJECT_DATASET_ROOT` 사용 |
| `docs/notes/03-24_phase5_surface_prep_fixed_room0_smoke_2026.md` | surface scene/object dataset roots | 변수화 | `SURFACE_SCENE_DATASET_ROOT`, `SURFACE_OBJECT_DATASET_ROOT` 사용 |
| `docs/notes/03-24_phase5_surface_prep_rerun_2026.md` | surface scene/object dataset roots | 변수화 | `SURFACE_SCENE_DATASET_ROOT`, `SURFACE_OBJECT_DATASET_ROOT` 사용 |
| `docs/phase4_archive_guide_2026-03-23.md` | storage mount status, backup topology, archive commands | 혼합 | 표/트리/literal topology는 유지, 반복 command prefix는 `ARCHIVE_ROOT`, `SSD_INDEX_ROOT` 등으로 변수화 |
| `docs/gaussian_direct_branch_plan.md` | generic `/mnt/...` placeholder, not a concrete absolute path | 유지 | 이미 placeholder 의미라 별도 변수화 필요 없음 |

## 문서별 적용 방식

### A. 결과 보고서

대상:

- `docs/experiment_results/03-20_dense_view_probe_2026.md`
- `docs/experiment_results/03-20_prior_protection_room_0_2026.md`
- `docs/experiment_results/03-20_upper_bound_dense_diverse_384_2026.md`
- `docs/experiment_results/03-27_baseline_surface_rgb_variance10_2026.md`
- `docs/experiment_results/03-27_baseline_surface_rgb_variance_2026.md`

원칙:

- 문서 상단 `Dataset`, `Dense dataset root`, `source_path` 같은 반복 경로를 변수 표현으로 치환한다.
- 필요하면 문서 초반에 `External Roots` 섹션을 추가한다.
- scene suffix는 유지한다.

예시:

```text
- External root: `SURFACE_SCENE_DATASET_ROOT=${DATA_STAGE_ROOT}/replica_colmap_multi_roomwide_v2_384_surface_rgb`
- `room_0` source_path: `${SURFACE_SCENE_DATASET_ROOT}/room_0`
```

### B. 운영 노트

대상:

- `docs/notes/03-20_image_count_inventory_2026.md`
- `docs/notes/03-21_roomwide_camera_distribution_check_2026.md`
- `docs/notes/03-23_phase5_surface_prep_2026.md`
- `docs/notes/03-24_phase5_surface_prep_fixed_room0_smoke_2026.md`
- `docs/notes/03-24_phase5_surface_prep_rerun_2026.md`

원칙:

- inventory / prep 노트의 source root는 변수화한다.
- object-level path는 `${SURFACE_OBJECT_DATASET_ROOT}/room_0/6` 형태로 치환한다.
- legacy repo dataset는 `${LEGACY_DATASET_ROOT}/replica_colmap` 형태로 치환한다.
- 외부 Markdown 링크는 클릭성을 우선하면 literal 유지, 변수화를 우선하면 코드 문자열로 변경한다.

보수적 권장안:

- `03-21_roomwide_camera_distribution_check_2026.md`의 `scene_meta.json` 링크는 literal 유지
- 같은 섹션에 변수 설명 줄만 추가

### C. 아카이브 runbook

대상:

- `docs/phase4_archive_guide_2026-03-23.md`

원칙:

- storage overview table은 literal 유지
- external storage tree 예시는 literal 유지
- exclusion list의 실제 dataset 위치는 literal 유지
- shell command block에서 반복되는 root만 변수화

권장 변수 도입 위치:

- Step 1 직전 또는 runbook 상단
- `ARCHIVE_ROOT=/mnt/hddg1/priorprobe3dgs-archive`
- `SSD_INDEX_ROOT=${DATA_STAGE_ROOT}/gaussian_direct_index`

권장 예시:

```bash
ARCHIVE_ROOT=/mnt/hddg1/priorprobe3dgs-archive
mkdir -p "${ARCHIVE_ROOT}/gaussian-direct/phase1-3_2026-03/..."
```

이 문서는 "실제 어느 디스크에 무엇이 있다"를 설명하는 성격이 강하므로 전면 변수화는 하지 않는다.

## 실행 순서 제안

실제 치환을 하게 되면 아래 순서로 진행한다.

1. 결과 보고서와 prep 노트부터 변수화한다.
2. `03-21_roomwide_camera_distribution_check_2026.md`는 링크 클릭성 유지 여부를 먼저 결정한다.
3. `phase4_archive_guide`는 마지막에 다룬다.
4. 치환 후 `git grep`으로 literal 외부 경로 잔존 여부를 재확인한다.
5. `phase4_archive_guide`에서는 literal 유지 대상이 의도적으로 남아 있어야 한다.

## 승인 전 확인 질문

실제 실행 전에는 아래 두 정책을 먼저 확정해야 한다.

1. 외부 Markdown 링크는 클릭성을 위해 literal 절대 링크를 남길지, 변수 표현으로 바꿔 클릭성을 포기할지
2. `phase4_archive_guide`의 exclusion list를 literal로 남길지, variable alias를 병기할지

이 두 가지가 정해져야 최종 치환 결과의 일관성이 맞는다.

## 이번 계획의 완료 조건

- 외부 절대 경로가 문서별로 `변수화`, `유지`, `혼합` 중 하나로 분류돼 있다.
- 변수 이름 집합이 확정돼 있다.
- archive guide의 literal 유지 범위가 명시돼 있다.
- 아직 실제 치환은 수행하지 않았다.
