# Branch Strategy

PriorProbe3DGS 실험은 **prior insertion representation**을 기준으로 2개 브랜치에서 병렬 진행된다.

## 브랜치 분리 기준

| 브랜치 | Prior Representation | 핵심 특성 |
|--------|---------------------|----------|
| `exp/pointcloud` | Point Cloud | geometry-only init. 삽입된 점들이 densification을 통해 Gaussian으로 변환됨 |
| `exp/gaussian-direct` | Gaussian 집합 | geometry + appearance(SH coefficient 등) 동시 재사용 |

이 분리 자체가 "prior reuse의 어느 수준(geometry only vs geometry+appearance)이 효과적인가"라는 **추가 ablation 포인트**다.

## 브랜치별 실험 조건

| 항목 | exp/pointcloud | exp/gaussian-direct |
|------|---------------|---------------------|
| Prior source | ShapeSplat .ply (canonical seed point cloud) | ShapeSplat .ply (원본 Gaussian asset) |
| Alignment input | canonical_seed_path | canonical_seed_path |
| Insertion source | point cloud (xyz) | Gaussian parameters (xyz, opacity, scale, rot, SH) |
| Backend 경로 | merge / replace (pointcloud) | replace (gaussian-direct) → merge 순 |
| Output prefix | 기존 experiment 명칭 | `gaussian_direct_` prefix |

## 공통 모듈 관리

비교군 간 공정성을 위해 아래 모듈은 양쪽 브랜치에서 **반드시 동일하게 유지**한다.

- `src/priorprobe/optimization/trainer.py`
- `src/priorprobe/evaluation/metrics.py`

공통 모듈 변경 워크플로:

1. `main`에서 공통 변경 적용
2. `exp/pointcloud`, `exp/gaussian-direct` 양쪽으로 cherry-pick 또는 rebase
3. 각 브랜치에서 충돌 없이 동작하는지 확인

브랜치 간 직접 merge는 피한다. 공통 수정은 항상 `main`을 통해 배포한다.

## Oracle Prior 준비

두 브랜치에서 비교 가능하도록 oracle prior는 **pointcloud 버전과 Gaussian 버전 모두** 준비한다. oracle prior 학습 대상 데이터셋과 객체 선정 기준은 `docs/experiment_design.md`를 참조한다.

## 브랜치별 참고 문서

- `exp/pointcloud`: `docs/experiment_design.md`, `docs/branches.md`
- `exp/gaussian-direct`: `docs/experiment_design.md`, `docs/branches.md`, `docs/gaussian_direct_branch_plan.md`
