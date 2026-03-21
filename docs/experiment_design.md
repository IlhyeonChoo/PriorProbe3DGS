# Experiment Design

PriorProbe3DGS 1단계는 prior 효과를 다른 가속 요소와 분리해서 보는 것을 목표로 한다.

## Comparison Order

1. `baseline_from_scratch`
2. `oracle_prior`
3. `oracle_alignment`
4. `shapesplat_auto`
5. `domain_incremental`
6. `domain_incremental_adapted`

## Controlled Variables

- optimizer
- densification policy
- learning-rate schedule
- rendering settings

## Open TODOs

- `time-to-target quality`의 임계값을 metric별로 명시
- occlusion bucket 산정 규칙을 mask overlap 기준으로 고정
- 실제 3DGS backend와 trainer wrapper 연결

## Vanilla 3DGS Prior-Init Path

- 주력 backend는 `../3DGS/gaussian-splatting`를 사용한다.
- ShapeSplat retrieval 결과는 top-1 prior PLY로 선택한다.
- 첫 버전은 `prior_alignment.transform_path`로 oracle/manual 정렬을 명시한다.
- `scripts/run_experiment.py`는 `reconstruction_backend: vanilla_3dgs`인 경우 `scripts/train_vanilla_3dgs_backend.py`를 호출한다.
- baseline과 prior-init은 같은 optimizer/schedule로 실행하고 차이는 초기 PLY만 남긴다.

## Dataset Policy

- prior source dataset과 reconstruction target dataset은 분리해서 관리한다.
- prior source는 기본적으로 `configs/priors/shapesplat.yaml`을 사용한다.
- reconstruction target은 `configs/datasets/` 아래에서 선택하며, 현재 템플릿은 `shapesplat_objects`, `replica`, `scannet`, `nerf_synthetic`, `custom_capture`를 포함한다.
- `scripts/run_experiment.py`는 dataset config에서 `source_path`, `images`, `depths`, `eval`, `white_background`를 읽어 backend 인자를 채운다.
- scene별 실제 루트는 `--dataset-root`, 특정 장면은 `--dataset-scene-id`로 덮어쓸 수 있다.

## Branch Strategy

실험은 prior insertion representation 기준으로 2개 브랜치에서 병렬 진행된다.

| 브랜치 | Prior Representation | 설명 |
|--------|---------------------|------|
| `exp/pointcloud` | Point Cloud | geometry-only init. densification을 통해 Gaussian으로 변환 |
| `exp/gaussian-direct` | Gaussian 집합 | geometry + appearance(SH coefficient 등) 동시 재사용 |

공통 모듈(`trainer.py`, `metrics.py`)은 양쪽 브랜치에서 동일하게 유지한다. 브랜치별 상세 실험 조건은 `docs/branches.md`를 참조한다.

## Oracle Prior 3단계 조건

Oracle prior 실험은 아래 3개 조건으로 단계적으로 진행한다.

| 조건 | 설명 | 목적 |
|------|------|------|
| A | Oracle Prior + Oracle Alignment | 이론적 상한선 (ceiling) |
| B | 동일 객체 lib 보유 + 자동 retrieval/insertion | 이상적 조건 자동화 성능 |
| C | 동일 객체 lib 미보유 (유사 객체로 매칭) | 현실적 시나리오 성능 |

**Information leakage disclaimer:** 조건 A는 데이터셋 내 객체를 독립 학습하여 oracle prior를 생성하므로 학습-평가 이미지 간 환경이 겹칠 수 있다. 이 조건은 이론적 상한선 참조용이며 실험의 주요 결론에는 영향을 주지 않는다.

## Occlusion 실험 우선순위

Occlusion 실험은 **후순위**로 배치한다.

- 깨끗한 조건(no occlusion)에서 먼저 prior 삽입 효과를 확인하는 것이 우선이다.
- no-occlusion 조건에서 효과가 없으면 occlusion 실험은 수행하지 않는다.
- 효과 확인 후 occlusion 수준을 점진적으로 추가한다.
- occlusion 정량화 기준(projected mask overlap, visible area ratio)은 1순위 실험 결과 확인 후 확정한다.

## Branch-Specific Notes

- gaussian을 직접 삽입하는 실험 브랜치의 배경과 운영 계획은 `docs/gaussian_direct_branch_plan.md`에 별도로 정리한다.
