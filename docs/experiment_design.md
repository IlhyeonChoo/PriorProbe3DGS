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

## Branch-Specific Notes

- gaussian을 직접 삽입하는 실험 브랜치의 배경과 운영 계획은 `docs/gaussian_direct_branch_plan.md`에 별도로 정리한다.
